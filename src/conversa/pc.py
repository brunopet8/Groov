"""Backend do controle do PC: lê e age em janelas por UI Automation, sempre por uma sonda PowerShell fora do processo.

Molde de tela.py: Protocol, classe real (`Sonda`) e falso para os testes dos outros módulos (`Falso`). Nada aqui decide se um passo
pode acontecer: isso é de regras_pc/laco. O backend só confere, no ato, que o alvo continua sendo o que foi lido.

Para a Task 11 (ligar `Sessao.midia_tocando`): `vigiar()` chama `await backend.midias()` a cada poucos segundos e faz
`sessao.midia_tocando = any(m.tocando for m in midias)`; `midias()` devolve `()` se a sonda falhar (o que desliga a flag, o lado benigno).
"""
import asyncio
import base64
import ctypes
import json
import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from src.conversa import tela
from src.conversa.abrir_janela import CHROME
from src.conversa.ajudante import CHAVES_DOS_MODELOS, SEM_JANELA, _matar, ambiente_sem
from src.conversa.regras_pc import PROCESSOS_NAVEGADOR, TECLAS, Elemento, e_outro_navegador, host_de

log = logging.getLogger("groov.pc")

SONDA_PS1 = Path(__file__).with_name("sonda.ps1")
TETO_SONDA_S = 8.0
TEXTO_MAX = 8192  # caracteres de página por leitura (acompanha TEXTO_PAGINA_MAX do cerebro_pc)
TETO_OLHAR_S = 12.0  # captura + OCR do WinRT
# Esconde a barra "Playwright Extension começou a depurar" (decisão do usuário, 14/11). Só vale quando o Chrome abre com ela;
# risco aceito: qualquer extensão pode depurar o Chrome sem a barra de aviso.
FLAG_SEM_BARRA = "--silent-debugger-extension-api"
IMAGEM_LADO_MAX = 1280  # lado maior do PNG que pode ir ao Claude (o OCR usa a captura inteira)
LIMIAR_SOM = 0.02  # decisão provisória (a revisar): pico do Spotify tocando foi 0,198 e pausado 0 (prova 9)
AMOSTRAS_SOM = 6  # decisão provisória (a revisar): o pico é instantâneo, então várias leituras de ~80 ms cada
# Apelidos de app (11/11: não é mais lista de permitidos, qualquer app de nome simples abre): nome falado -> (processo, executável).
APPS_PC: dict[str, tuple[str, str]] = {
    "spotify": ("Spotify", os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WindowsApps", "Spotify.exe")),
    "bloco de notas": ("notepad", "notepad.exe"),
    "notepad": ("notepad", "notepad.exe"),
}
# Janelas em que o GROOV nunca lê nem age (processos de sistema, elevados ou de segurança); o resto do PC vale.
# (e os outros navegadores). Janela UWP vem com dono ApplicationFrameHost: a sonda e a SondaAD recusam também pelo título.
PROCESSOS_PROIBIDOS = ("consent", "logonui", "credentialuibroker", "sechealthui", "securityhealthsystray", "winlogon", "lockapp",
                       *PROCESSOS_NAVEGADOR)
TITULOS_PROIBIDOS = ("segurança do windows", "windows security")
NOME_APP_MAX = 40


def nome_de_app_valido(nome: str) -> bool:
    """Nome simples de app: letras, dígitos, espaço, ponto e hífen, começando por letra ou dígito. Sem caminho, opção nem
    metacaractere de shell: o nome só chega à sonda como texto, nunca como linha de comando."""
    return (0 < len(nome) <= NOME_APP_MAX and nome[0].isalnum() and ".." not in nome
            and all(c.isalnum() or c in " .-" for c in nome))


class ErroSonda(Exception):
    """Falha da sonda (estourou, saiu com erro, JSON inválido). A mensagem é fixa: nunca leva texto de janela."""


@dataclass(frozen=True)
class Leitura:
    hwnd: int
    endereco: str | None
    titulo: str
    texto: str
    elementos: tuple[Elemento, ...]
    cortado: bool


@dataclass(frozen=True)
class Midia:
    app: str
    tocando: bool
    titulo: str
    artista: str


@dataclass(frozen=True)
class InfoJanela:
    processo: str
    abas: int  # abas do Chrome; 0 nos outros apps
    groov: bool  # é a janela do próprio GROOV


@dataclass(frozen=True)
class Envio:
    destino: str
    texto: str
    anexos: int
    cc: str


@dataclass(frozen=True)
class LinhaOcr:
    texto: str
    caixa: tuple[int, int, int, int]  # x, y, largura, altura: px físicos relativos à janela


@dataclass(frozen=True)
class Olhar:
    """Captura só da janela alvo: retângulo na tela (px físicos), linhas do OCR local e o PNG reduzido (lado ≤ IMAGEM_LADO_MAX)."""
    retangulo: tuple[int, int, int, int]  # esquerda, topo, largura, altura
    linhas: tuple[LinhaOcr, ...]
    png: bytes
    escala: float  # lado do PNG / lado real da janela


class Backend(Protocol):
    async def janelas(self, processo: str = "") -> frozenset[int]: ...
    async def abrir_site(self, url: str) -> None: ...
    async def abrir_app(self, nome: str) -> int | None: ...
    async def ler(self, hwnd: int) -> Leitura: ...
    async def clicar(self, hwnd: int, el: Elemento, endereco: str | None) -> bool: ...
    async def buscar(self, hwnd: int, el: Elemento, texto: str, endereco: str | None) -> bool: ...
    async def digitar(self, hwnd: int, el: Elemento, texto: str, endereco: str | None, acrescentar: bool = True) -> bool: ...
    async def rolar(self, hwnd: int, direcao: str) -> bool: ...
    async def voltar(self, hwnd: int) -> bool: ...
    async def envio(self, hwnd: int) -> Envio | None: ...
    async def midias(self) -> tuple[Midia, ...]: ...
    async def pausar_midia(self, app: str) -> bool: ...
    async def controlar_midia(self, acao: str) -> bool: ...
    async def primeiro_plano(self) -> int: ...
    async def trazer(self, hwnd: int) -> bool: ...
    async def som_tocando(self) -> bool: ...
    async def info_janela(self, hwnd: int) -> InfoJanela | None: ...
    async def fechar(self, hwnd: int) -> bool: ...
    async def minimizar(self, hwnd: int) -> bool: ...
    async def fechar_aba(self, hwnd: int) -> bool: ...
    async def olhar(self, hwnd: int) -> Olhar | None: ...
    async def clicar_ponto(self, hwnd: int, x: int, y: int, retangulo: tuple[int, int, int, int]) -> bool: ...
    async def tecla(self, hwnd: int, tecla: str) -> bool: ...
    async def procurar(self, nome: str) -> tuple[int, str] | None: ...
    async def tela_cheia(self, hwnd: int) -> bool: ...
    async def focar(self, nome: str) -> int | None: ...


def comando_sonda() -> list[str]:
    ps = shutil.which("powershell") or r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
    return [ps, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(SONDA_PS1)]


def _elemento(d: dict) -> Elemento:
    anc = d.get("ancestrais") or ()
    anc = (anc,) if isinstance(anc, str) else tuple(a for a in anc if isinstance(a, str) and a)  # a sonda manda null
    return Elemento(id=int(d["id"]), nome=d["nome"], tipo=d["tipo"], papel=d.get("papel") or "",
                    texto_interno=d.get("texto_interno") or "", ancestrais=anc,
                    senha=bool(d.get("senha")), runtime_id=d.get("runtime_id") or "", host_do_link=d.get("host_do_link"))


def _ids(el: Elemento) -> dict:
    return {"runtime_id": el.runtime_id, "nome": el.nome[:200], "tipo": el.tipo}


class Sonda:
    """Uma execução do PowerShell por chamada: pedido em JSON UTF-8 pelo stdin, resposta JSON pelo stdout. Estourar o teto ou
    receber CancelledError (é como `Laco.cancelar()` interrompe) mata a árvore do processo, sem derrubar a voz."""

    def __init__(self, comando: list[str] | None = None, teto: float = TETO_SONDA_S, chrome: str = CHROME,
                 apps: dict[str, tuple[str, str]] | None = None, segredos: frozenset[str] = CHAVES_DOS_MODELOS,
                 titulo_groov: str | None = None, processos_extras: tuple[str, ...] = (),
                 proibidos: tuple[str, ...] = PROCESSOS_PROIBIDOS):
        self.comando = comando
        self.teto = teto
        self.chrome = chrome
        self.apps = APPS_PC if apps is None else apps
        self.segredos = segredos
        self.titulo_groov = titulo_groov
        self.proibidos = tuple(p.lower() for p in proibidos)
        # só o que `janelas()` lista (Chrome, apelidos, apps que o GROOV abriu): ler e agir valem em qualquer app não proibido
        self.listadas = ["chrome", *(p for p, _ in self.apps.values()), *processos_extras]
        self._pausado = ""  # app da sessão que o último "pausar" pausou

    async def _chamar(self, op: str, teto: float | None = None, **dados) -> dict:
        pedido = {"op": op, "proibidos": list(self.proibidos), "titulos_proibidos": list(TITULOS_PROIBIDOS), "listadas": list(self.listadas),
                  "titulo_groov": self.titulo_groov or tela.titulo_da_janela(tela.porta()), **dados}
        corpo = json.dumps(pedido, ensure_ascii=False).encode("utf-8")
        env = {**ambiente_sem(self.segredos), "PYTHONUTF8": "1"}
        proc = await asyncio.create_subprocess_exec(
            *(self.comando or comando_sonda()), stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=subprocess.DEVNULL, env=env, creationflags=SEM_JANELA)
        try:
            saida, _ = await asyncio.wait_for(proc.communicate(corpo), teto or self.teto)
        except asyncio.TimeoutError:
            _matar(proc)
            await proc.wait()
            raise ErroSonda(f"{op}: estourou o teto") from None
        except asyncio.CancelledError:
            _matar(proc)
            raise
        if proc.returncode != 0:
            raise ErroSonda(f"{op}: saiu com código {proc.returncode}")
        try:
            resposta = json.loads(saida.decode("utf-8-sig"))
        except ValueError:
            raise ErroSonda(f"{op}: resposta ilegível") from None
        if not isinstance(resposta, dict):
            raise ErroSonda(f"{op}: resposta ilegível")
        if resposta.get("erro"):
            raise ErroSonda(f"{op}: {resposta['erro']}")  # nome do tipo da exceção, nunca texto de janela
        return resposta

    async def _agir(self, op: str, **dados) -> bool:
        """Ação: qualquer falha é "não agiu" (o laço relê). O motivo vai ao log como palavra fixa."""
        try:
            r = await self._chamar(op, **dados)
        except ErroSonda as e:
            log.warning("sonda %s", e)
            return False
        if not r.get("ok"):
            log.info("sonda %s: não agiu (%s)", op, r.get("motivo", "?"))
        return bool(r.get("ok"))

    async def janelas(self, processo: str = "") -> frozenset[int]:
        """`processo`: um app a mais na lista desta chamada (o alvo de "fecha o X"), se for nome simples."""
        extra = [processo] if nome_de_app_valido(processo) else []
        return frozenset(int(h) for h in (await self._chamar("janelas", listadas=[*self.listadas, *extra]))["janelas"])

    async def abrir_site(self, url: str) -> None:
        if not url.startswith(("http://", "https://")):
            raise ValueError("só http e https")
        try:  # perfil normal do Chrome: sem --user-data-dir; sem --new-window: abre aba na janela ativa (fechado, abre janela)
            subprocess.Popen([self.chrome, FLAG_SEM_BARRA, url], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, env=ambiente_sem(self.segredos), creationflags=SEM_JANELA)
        except OSError:
            raise ErroSonda("abrir_site: não consegui abrir o Chrome") from None

    async def abrir_app(self, nome: str) -> int | None:
        nome = nome.strip().lower()
        app = self.apps.get(nome) or ((nome, "") if nome_de_app_valido(nome) else None)
        if app is None or app[0].lower() in self.proibidos or e_outro_navegador(nome):
            return None
        h = (await self._chamar("abrir_app", processo=app[0], exe=app[1])).get("hwnd")
        if not (isinstance(h, int) and h):  # 11/11: o PowerShell já devolveu a lista de janelas aqui (TypeError no int())
            return None
        if app[0] not in self.listadas:
            self.listadas.append(app[0])
        return h

    async def ler(self, hwnd: int) -> Leitura:
        r = await self._chamar("ler", hwnd=hwnd, max_chars=TEXTO_MAX)
        return Leitura(hwnd=int(r["hwnd"]), endereco=r.get("endereco"), titulo=r.get("titulo") or "", texto=r.get("texto") or "",
                       elementos=tuple(_elemento(d) for d in r.get("elementos") or ()), cortado=bool(r.get("cortado")))

    async def clicar(self, hwnd: int, el: Elemento, endereco: str | None) -> bool:
        return await self._agir("clicar", hwnd=hwnd, endereco=endereco, **_ids(el))

    async def buscar(self, hwnd: int, el: Elemento, texto: str, endereco: str | None) -> bool:
        return await self._agir("buscar", hwnd=hwnd, endereco=endereco, texto=texto, **_ids(el))

    async def digitar(self, hwnd: int, el: Elemento, texto: str, endereco: str | None, acrescentar: bool = True) -> bool:
        return await self._agir("digitar", hwnd=hwnd, endereco=endereco, texto=texto, acrescentar=acrescentar, **_ids(el))

    async def rolar(self, hwnd: int, direcao: str) -> bool:
        return await self._agir("rolar", hwnd=hwnd, direcao=direcao)

    async def voltar(self, hwnd: int) -> bool:
        return await self._agir("voltar", hwnd=hwnd)

    async def envio(self, hwnd: int) -> Envio | None:
        try:
            e = (await self._chamar("envio", hwnd=hwnd)).get("envio")
        except ErroSonda as erro:
            log.warning("sonda %s", erro)
            return None
        return Envio(e["destino"], e["texto"], int(e["anexos"]), e["cc"]) if e else None

    async def midias(self) -> tuple[Midia, ...]:
        try:
            r = await self._chamar("midias")
        except ErroSonda as e:
            log.warning("sonda %s", e)
            return ()
        return tuple(Midia(m["app"], bool(m["tocando"]), m.get("titulo") or "", m.get("artista") or "") for m in r.get("midias") or ())

    async def pausar_midia(self, app: str) -> bool:
        return await self._agir("pausar", app=app)

    async def controlar_midia(self, acao: str) -> bool:
        """`acao`: pausar, tocar ou proxima, na sessão que a sonda achar. Tocar prefere o app que o último "pausar" pausou
        (rodada de 09/11: "continua" despausou o vídeo do navegador em vez do Spotify)."""
        try:
            r = await self._chamar("midia_controle", acao=acao, preferir=self._pausado)
        except ErroSonda as e:
            log.warning("sonda %s", e)
            return False
        ok = bool(r.get("ok"))
        if ok and acao in ("pausar", "tocar"):  # voltou a tocar: a preferência acabou
            self._pausado = str(r.get("app") or "") if acao == "pausar" else ""
        return ok

    async def primeiro_plano(self) -> int:
        """Janela de nível superior em primeiro plano (0 se nenhuma). Direto por ctypes: não vale um PowerShell."""
        if sys.platform != "win32":
            return 0
        u = ctypes.WinDLL("user32")
        u.GetForegroundWindow.restype = ctypes.c_void_p
        u.GetAncestor.restype = ctypes.c_void_p
        u.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        fg = u.GetForegroundWindow()
        return int((u.GetAncestor(fg, 2) if fg else 0) or 0)  # 2 = GA_ROOT

    async def trazer(self, hwnd: int) -> bool:
        """Põe a janela do pedido em primeiro plano (rodada de 09/11: atrás, a UIA não mexia nela). Processo em segundo
        plano não ganha SetForegroundWindow sozinho: liga a entrada à da janela da frente (AttachThreadInput) e solta."""
        if sys.platform != "win32":
            return False
        u, k = ctypes.WinDLL("user32"), ctypes.WinDLL("kernel32")
        u.GetForegroundWindow.restype = ctypes.c_void_p
        u.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        for f in (u.IsIconic, u.BringWindowToTop, u.SetForegroundWindow):
            f.argtypes = [ctypes.c_void_p]
        u.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
        if u.IsIconic(hwnd):
            u.ShowWindow(hwnd, 9)  # SW_RESTORE
        fg = u.GetForegroundWindow()
        dela, minha = (u.GetWindowThreadProcessId(fg, None) if fg else 0), k.GetCurrentThreadId()
        ligou = bool(dela) and dela != minha and bool(u.AttachThreadInput(minha, dela, True))
        try:
            u.BringWindowToTop(hwnd)
            u.SetForegroundWindow(hwnd)
        finally:
            if ligou:
                u.AttachThreadInput(minha, dela, False)
        return await self.primeiro_plano() == hwnd

    async def info_janela(self, hwnd: int) -> InfoJanela | None:
        try:
            r = await self._chamar("janela_info", hwnd=hwnd)
        except ErroSonda as e:
            log.warning("sonda %s", e)
            return None
        return InfoJanela(str(r.get("processo") or ""), int(r.get("abas") or 0), bool(r.get("groov")))

    async def fechar(self, hwnd: int) -> bool:
        """Pede o fechamento (WM_CLOSE: o app ainda pode perguntar se salva). Quem confere se pode é regras_pc.decidir_janela."""
        if sys.platform != "win32":
            return False
        u = ctypes.WinDLL("user32")
        u.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
        return bool(u.PostMessageW(hwnd, 0x0010, 0, 0))  # WM_CLOSE

    async def minimizar(self, hwnd: int) -> bool:
        if sys.platform != "win32":
            return False
        u = ctypes.WinDLL("user32")
        u.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
        u.IsIconic.argtypes = [ctypes.c_void_p]
        u.ShowWindow(hwnd, 6)  # SW_MINIMIZE; o retorno de ShowWindow diz só se estava visível
        return bool(u.IsIconic(hwnd))

    async def fechar_aba(self, hwnd: int) -> bool:
        """A aba ativa do Chrome, pelo botão de fechar dela na árvore da UIA (sem atalho de teclado)."""
        return await self._agir("fechar_aba", hwnd=hwnd)

    async def olhar(self, hwnd: int) -> Olhar | None:
        """Captura e OCR só da janela `hwnd`; qualquer falha é None (o laço segue sem visão)."""
        try:
            r = await self._chamar("olhar", teto=TETO_OLHAR_S, hwnd=hwnd, lado_max=IMAGEM_LADO_MAX)
            linhas = tuple(LinhaOcr(str(d["texto"]), tuple(int(v) for v in d["caixa"])) for d in r.get("linhas") or ()
                           if isinstance(d, dict) and str(d.get("texto") or "").strip())
            return Olhar(tuple(int(v) for v in r["retangulo"]), linhas, base64.b64decode(r["png_b64"]), float(r["escala"]))
        except ErroSonda as e:
            log.warning("sonda %s", e)
        except (KeyError, TypeError, ValueError) as e:
            log.warning("sonda olhar: resposta torta (%s)", type(e).__name__)
        return None

    async def clicar_ponto(self, hwnd: int, x: int, y: int, retangulo: tuple[int, int, int, int]) -> bool:
        """Clique em (x, y) relativo à janela; a sonda recusa se a janela saiu da frente ou o retângulo mudou desde o olhar."""
        return await self._agir("clicar_ponto", hwnd=hwnd, x=int(x), y=int(y), retangulo=list(retangulo))

    async def tecla(self, hwnd: int, tecla: str) -> bool:
        if tecla not in TECLAS:
            return False
        return await self._agir("tecla", hwnd=hwnd, tecla=tecla)

    async def _foco(self, nome: str, selecionar: bool) -> dict | None:
        if not nome_de_app_valido(nome):
            return None
        try:
            r = await self._chamar("focar", nome=nome, selecionar=selecionar)
        except ErroSonda as e:
            log.warning("sonda %s", e)
            return None
        return r if isinstance(r.get("hwnd"), int) and r["hwnd"] else None

    async def tela_cheia(self, hwnd: int) -> bool:
        """A janela cobre o monitor inteiro (o player em tela cheia); janela maximizada não cobre a barra de tarefas."""
        if sys.platform != "win32":
            return False

        class Ret(ctypes.Structure):
            _fields_ = [("e", ctypes.c_long), ("t", ctypes.c_long), ("d", ctypes.c_long), ("b", ctypes.c_long)]

        class InfoMonitor(ctypes.Structure):
            _fields_ = [("tamanho", ctypes.c_ulong), ("monitor", Ret), ("trabalho", Ret), ("flags", ctypes.c_ulong)]
        u = ctypes.WinDLL("user32")
        u.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(Ret)]
        u.MonitorFromWindow.argtypes, u.MonitorFromWindow.restype = [ctypes.c_void_p, ctypes.c_ulong], ctypes.c_void_p
        u.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.POINTER(InfoMonitor)]
        r, info = Ret(), InfoMonitor(tamanho=ctypes.sizeof(InfoMonitor))
        if not u.GetWindowRect(hwnd, ctypes.byref(r)) or not u.GetMonitorInfoW(u.MonitorFromWindow(hwnd, 2), ctypes.byref(info)):
            return False
        m = info.monitor
        return r.e <= m.e and r.t <= m.t and r.d >= m.d and r.b >= m.b

    async def procurar(self, nome: str) -> tuple[int, str] | None:
        """(hwnd, título) da única janela ou aba do Chrome cujo título contém `nome`, sem selecionar nada."""
        r = await self._foco(nome, False)
        return (r["hwnd"], str(r.get("titulo") or "")) if r else None

    async def focar(self, nome: str) -> int | None:
        """A única janela aberta (ou aba do Chrome, que a sonda seleciona) cujo título contém `nome`; None se nenhuma ou várias."""
        r = await self._foco(nome, True)
        if r is None:
            return None
        processo = str(r.get("processo") or "")
        if processo and processo not in self.listadas:  # janelas() passa a ver o app focado (continuação do pedido)
            self.listadas.append(processo)
        return r["hwnd"]

    async def som_tocando(self) -> bool:
        """Algum processo com pico de áudio, fora o Chrome do GROOV e este processo. Se a sonda falhar, diz que há som:
        o lado seguro, porque som tocando recusa a frase forte."""
        try:
            r = await self._chamar("som", amostras=AMOSTRAS_SOM, ignorar_pids=[os.getpid()])
        except ErroSonda as e:
            log.warning("sonda %s", e)
            return True
        return any(float(p["pico"]) >= LIMIAR_SOM for p in r.get("picos") or ())


async def janela_nova(backend: Backend, antes: frozenset[int], prazo: float = 10, passo: float = 0.3, assentar: float = 1.5,
                      excluir: frozenset[int] = frozenset()) -> int | None:
    """Exatamente uma janela nova (Chrome ou app da lista) em relação a `antes`; zero ou duas: None. A janela do GROOV
    (`tela.titulo_da_janela(tela.porta())`) nunca entra: a Sonda a tira de `janelas()` pelo título e `excluir` cobre quem
    tiver o HWND dela. Ao ver a primeira, espera `assentar` e relê, porque o Chrome restaurando sessão pode abrir duas."""
    relogio = asyncio.get_running_loop().time
    fim = relogio() + prazo
    while True:
        novas = (await backend.janelas()) - antes - excluir
        if novas:
            await asyncio.sleep(assentar)
            novas = (await backend.janelas()) - antes - excluir
            return next(iter(novas)) if len(novas) == 1 else None
        if relogio() >= fim:
            return None
        await asyncio.sleep(passo)


def _mesmo_site(a: str, b: str) -> bool:
    """Mesmo host, com ou sem www., ou um subdomínio do outro (redirecionamento nos dois sentidos)."""
    a, b = a.removeprefix("www."), b.removeprefix("www.")
    return a == b or a.endswith("." + b) or b.endswith("." + a)


async def janela_da_aba(backend: Backend, antes: frozenset[int], host: str, prazo: float = 10, passo: float = 0.3,
                        excluir: frozenset[int] = frozenset(), assentar: float = 1.5) -> int | None:
    """A janela do site que acabou de abrir: uma janela nova (Chrome estava fechado, mesma regra de `janela_nova`) ou uma
    janela que já existia e cujo endereço lido bate com `host` (a aba nova abre na janela do usuário). A da frente primeiro;
    depois de `assentar`, as de trás, porque o Windows pode deixar a janela da aba nova atrás (rodada de 09/11): só se
    for uma só no site, senão a janela antiga do usuário no mesmo site passaria pela aba nova."""
    relogio = asyncio.get_running_loop().time
    inicio = relogio()
    fim = inicio + prazo

    async def no_site(h: int) -> bool:
        try:
            leitura = await backend.ler(h)
        except Exception as erro:  # a janela pode estar carregando: tenta de novo até o prazo
            log.warning("aba: ler falhou: %s", type(erro).__name__)
            return False
        lido = host_de(leitura.endereco) if leitura.endereco else None
        return leitura.hwnd == h and bool(lido) and _mesmo_site(lido, host)
    while True:
        if (nova := await janela_nova(backend, antes, 0, passo, assentar, excluir)) is not None:
            return nova
        plano = await backend.primeiro_plano()
        if plano in antes and plano not in excluir and await no_site(plano):
            return plano
        if relogio() - inicio >= assentar:
            achadas = [h for h in sorted(antes - excluir - {plano}) if await no_site(h)]
            if len(achadas) == 1:
                return achadas[0]
        if relogio() >= fim:
            return None
        await asyncio.sleep(passo)


class Falso:
    """Backend de teste dos outros módulos: respostas roteirizadas, chamadas gravadas em `chamadas`."""

    def __init__(self, leituras: list[Leitura] | None = None, janelas: list[frozenset[int]] | None = None,
                 midias: list[tuple[Midia, ...]] | None = None, agir: bool = True, som: bool = False, plano: int = 0):
        self.leituras = list(leituras or [])
        self._janelas = list(janelas or [frozenset()])
        self._midias = list(midias or [()])
        self.agir, self.som, self.plano = agir, som, plano
        self.chamadas: list[tuple] = []
        self.envio_lido: Envio | None = None
        self.app_hwnd: int | None = None
        self.trazer_ok = True
        self.infos: dict[int, InfoJanela] = {}
        self.olhares: list[Olhar | None] = [None]
        self.focar_hwnd: int | None = None
        self.focar_titulo = ""
        self.cheia = False

    def _gravar(self, *c) -> None:
        self.chamadas.append(c)

    async def janelas(self, processo: str = "") -> frozenset[int]:
        self._gravar("janelas")
        return self._janelas.pop(0) if len(self._janelas) > 1 else self._janelas[0]

    async def abrir_site(self, url: str) -> None:
        self._gravar("abrir_site", url)

    async def abrir_app(self, nome: str) -> int | None:
        self._gravar("abrir_app", nome)
        return self.app_hwnd

    async def ler(self, hwnd: int) -> Leitura:
        self._gravar("ler", hwnd)
        return self.leituras.pop(0) if len(self.leituras) > 1 else self.leituras[0]

    async def clicar(self, hwnd: int, el: Elemento, endereco: str | None) -> bool:
        self._gravar("clicar", hwnd, el, endereco)
        return self.agir

    async def buscar(self, hwnd: int, el: Elemento, texto: str, endereco: str | None) -> bool:
        self._gravar("buscar", hwnd, el, texto, endereco)
        return self.agir

    async def digitar(self, hwnd: int, el: Elemento, texto: str, endereco: str | None, acrescentar: bool = True) -> bool:
        self._gravar("digitar", hwnd, el, texto, endereco, acrescentar)
        return self.agir

    async def rolar(self, hwnd: int, direcao: str) -> bool:
        self._gravar("rolar", hwnd, direcao)
        return self.agir

    async def voltar(self, hwnd: int) -> bool:
        self._gravar("voltar", hwnd)
        return self.agir

    async def envio(self, hwnd: int) -> Envio | None:
        self._gravar("envio", hwnd)
        return self.envio_lido

    async def midias(self) -> tuple[Midia, ...]:
        self._gravar("midias")
        return self._midias.pop(0) if len(self._midias) > 1 else self._midias[0]

    async def pausar_midia(self, app: str) -> bool:
        self._gravar("pausar_midia", app)
        return self.agir

    async def controlar_midia(self, acao: str) -> bool:
        self._gravar("controlar_midia", acao)
        return self.agir

    async def primeiro_plano(self) -> int:
        return self.plano

    async def trazer(self, hwnd: int) -> bool:
        self._gravar("trazer", hwnd)
        if self.trazer_ok:
            self.plano = hwnd
        return self.trazer_ok

    async def som_tocando(self) -> bool:
        return self.som

    async def info_janela(self, hwnd: int) -> InfoJanela | None:
        self._gravar("info_janela", hwnd)
        return self.infos.get(hwnd)

    async def fechar(self, hwnd: int) -> bool:
        self._gravar("fechar", hwnd)
        return self.agir

    async def minimizar(self, hwnd: int) -> bool:
        self._gravar("minimizar", hwnd)
        return self.agir

    async def fechar_aba(self, hwnd: int) -> bool:
        self._gravar("fechar_aba", hwnd)
        return self.agir

    async def olhar(self, hwnd: int) -> Olhar | None:
        self._gravar("olhar", hwnd)
        return self.olhares.pop(0) if len(self.olhares) > 1 else self.olhares[0]

    async def clicar_ponto(self, hwnd: int, x: int, y: int, retangulo: tuple[int, int, int, int]) -> bool:
        self._gravar("clicar_ponto", hwnd, x, y)
        return self.agir

    async def tecla(self, hwnd: int, tecla: str) -> bool:
        self._gravar("tecla", hwnd, tecla)
        return self.agir

    async def tela_cheia(self, hwnd: int) -> bool:
        return self.cheia

    async def procurar(self, nome: str) -> tuple[int, str] | None:
        self._gravar("procurar", nome)
        return (self.focar_hwnd, self.focar_titulo) if self.focar_hwnd else None

    async def focar(self, nome: str) -> int | None:
        self._gravar("focar", nome)
        return self.focar_hwnd
