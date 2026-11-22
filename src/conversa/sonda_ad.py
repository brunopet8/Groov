"""Segunda sonda do controle do PC: o agent-desktop (vercel-labs, Apache-2.0, versão 1.2.0) no lugar da `sonda.ps1` para ler e
agir em APPS (não no Chrome). Um processo por chamada, como `pc.Sonda`: uma falha dele nunca derruba a voz. Não decide nada:
as regras são de regras_pc/laco. Mídia, som, envio, abrir site, trazer/fechar/minimizar continuam na `Sonda` (9.5 compõe os dois).

O log guarda só o código de erro do envelope (STALE_REF...), nunca o conteúdo da janela.
"""
import asyncio
import ctypes
import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

from src.conversa.ajudante import CHAVES_DOS_MODELOS, SEM_JANELA, _matar, ambiente_sem
from src.conversa.pc import PROCESSOS_PROIBIDOS, TEXTO_MAX, TITULOS_PROIBIDOS, ErroSonda, Leitura
from src.conversa.regras_pc import Elemento, e_campo_sensivel

log = logging.getLogger("groov.sonda_ad")

EXECUTAVEL = "agent-desktop"  # o Windows acha pelo PATH (npm install -g agent-desktop@1.2.0)
RAIZ = Path(__file__).resolve().parents[2]
# Onde ele grava as leituras (refmaps) para resolver as referências; privado/ é ignorado pelo git. Nunca criada nem lida aqui.
AGENT_DESKTOP_HOME = RAIZ / "privado" / "agent-desktop"
TETO_AD_S = 8.0  # igual ao da Sonda
TETO_LEITURA_MS = 5000  # --timeout-ms da leitura; o padrão dele para auto-espera também é 5000
# NÃO VERIFICADO (a documentação 1.2.0 diz "w-" + identificador, sem dar o formato): shortcut: o id é montado só com o HWND, se
# ele exigir o token de criação da janela o ler falha com WINDOW_NOT_FOUND; trocar por um `list-windows` na Fase 10.
JANELA_ID = "w-{hwnd}"
VALOR_MAX = 2000  # caracteres: medido no Notepad (11/11) o get é exato até 2000 (1,5k e 2k iguais ao gravado); acima o editor rola e ele recusa (AMBIGUOUS_TARGET). Não há leitor independente: a UIA não vê o editor do Notepad (Document)
BOTOES_VOLTAR = ("voltar", "back", "go back")  # nome do botão de voltar, como a Sonda procura
# ControlType da UIA que o regras_pc espera, por papel do agent-desktop. NÃO VERIFICADO (papéis em inglês minúsculo);
# shortcut: papel fora da tabela vira o próprio papel capitalizado, o regras_pc só trata Edit/ComboBox/Hyperlink/Button.
TIPOS = {"button": "Button", "link": "Hyperlink", "textfield": "Edit", "textbox": "Edit", "searchbox": "Edit",
         "combobox": "ComboBox", "listitem": "ListItem", "checkbox": "CheckBox", "menuitem": "MenuItem", "tab": "TabItem"}


def processo_da_janela(hwnd: int) -> str:
    """Nome do executável (sem .exe, minúsculo) dono da janela; "" se não achar. Direto por ctypes, sem abrir processo."""
    if sys.platform != "win32":
        return ""
    u, k = ctypes.WinDLL("user32"), ctypes.WinDLL("kernel32")
    pid = ctypes.c_ulong(0)
    u.GetWindowThreadProcessId(ctypes.c_void_p(hwnd), ctypes.byref(pid))
    k.OpenProcess.restype = ctypes.c_void_p
    h = k.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return ""
    try:
        buf, n = ctypes.create_unicode_buffer(520), ctypes.c_ulong(520)
        k.QueryFullProcessImageNameW(ctypes.c_void_p(h), 0, buf, ctypes.byref(n))
        return Path(buf.value).stem.lower()
    finally:
        k.CloseHandle(ctypes.c_void_p(h))


def titulo_da_janela(hwnd: int) -> str:
    if sys.platform != "win32":
        return ""
    buf = ctypes.create_unicode_buffer(512)
    ctypes.WinDLL("user32").GetWindowTextW(ctypes.c_void_p(hwnd), buf, 512)
    return buf.value


class SondaAD:
    def __init__(self, comando: list[str] | None = None, home: Path = AGENT_DESKTOP_HOME, teto: float = TETO_AD_S,
                 segredos: frozenset[str] = CHAVES_DOS_MODELOS, proibidos: tuple[str, ...] = PROCESSOS_PROIBIDOS,
                 processo_de: Callable[[int], str] = processo_da_janela, titulo_de: Callable[[int], str] | None = None):
        # qualquer app, menos os proibidos; o Chrome fica de fora: o regras_pc decide login e clique pelo host do link e o
        # agent-desktop não o entrega
        self.proibidos = frozenset(p.lower() for p in proibidos) | {"chrome"}
        self.processo_de = processo_de
        self.titulo_de = titulo_de or titulo_da_janela
        self.comando = comando or [EXECUTAVEL]
        self.home = home
        self.teto = teto
        self.segredos = segredos

    async def _chamar(self, *args: str, teto: float | None = None) -> dict:
        """Roda `agent-desktop <args>` e devolve o `data` do envelope. Falha (teto, saída sem JSON, ok=false) vira
        ErroSonda com mensagem fixa: só o código do erro, nunca texto de janela. Estourar o teto ou ser cancelado mata a árvore."""
        op = args[0]
        env = {**ambiente_sem(self.segredos), "AGENT_DESKTOP_HOME": str(self.home)}
        try:
            proc = await asyncio.create_subprocess_exec(
                *self.comando, *args, stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE,
                stderr=subprocess.DEVNULL, env=env, creationflags=SEM_JANELA)
        except OSError:  # executável ausente, ou o .cmd do npm que não roda sem shell
            raise ErroSonda(f"{op}: não consegui iniciar o agent-desktop") from None
        try:
            saida, _ = await asyncio.wait_for(proc.communicate(), teto or self.teto)
        except asyncio.TimeoutError:
            _matar(proc)
            await proc.wait()
            raise ErroSonda(f"{op}: estourou o teto") from None
        except asyncio.CancelledError:
            _matar(proc)
            raise
        try:  # erro estruturado sai com código 1 e o JSON no stdout: lê o JSON antes de olhar o código
            envelope = json.loads(saida.decode("utf-8-sig"))
        except ValueError:
            envelope = None
        if not isinstance(envelope, dict):
            raise ErroSonda(f"{op}: saiu com código {proc.returncode}" if proc.returncode else f"{op}: resposta ilegível")
        if not envelope.get("ok"):
            codigo = str((envelope.get("error") or {}).get("code") or "?")
            log.info("agent-desktop %s: %s", op, codigo)
            raise ErroSonda(f"{op}: {codigo}")
        return envelope.get("data") or {}

    def aceita(self, hwnd: int) -> bool:
        processo = self.processo_de(hwnd)
        if processo == "applicationframehost":  # janela UWP: Segurança do Windows e afins só se vê pelo título
            if any(t in self.titulo_de(hwnd).lower() for t in TITULOS_PROIBIDOS):
                return False
        return bool(processo) and processo not in self.proibidos

    def _conferir(self, hwnd: int, op: str) -> None:
        if not self.aceita(hwnd):
            raise ErroSonda(f"{op}: janela_nao_permitida")

    async def ler(self, hwnd: int) -> Leitura:
        """Mesma `Leitura` da Sonda, para janela de qualquer app (Chrome e processo proibido: ErroSonda janela_nao_permitida, sem chamar nada).
        `runtime_id` guarda a referência dele (`@leitura:elemento`), que só vale para esta leitura: o laço relê a cada passo.
        shortcut: leitura única (`-i --compact`), sem esqueleto + região; tela com mais controles que o teto dele sai `cortado`,
        e o laço já limita a ELEMENTOS_MAX. Trocar por --skeleton + --root se a Fase 10 mostrar app denso demais."""
        self._conferir(hwnd, "ler")
        d = await self._chamar("snapshot", "--window-id", JANELA_ID.format(hwnd=hwnd), "-i", "--compact",
                               "--timeout-ms", str(TETO_LEITURA_MS))
        elementos, textos = [], []
        _percorrer(d.get("tree"), (), elementos, textos)
        janela = d.get("window") or {}
        titulo = str(janela.get("title") or janela.get("name") or "")
        return Leitura(hwnd=hwnd, endereco=None, titulo=titulo, texto=" ".join(textos)[:TEXTO_MAX], elementos=tuple(elementos),
                       cortado=d.get("complete") is False or bool(d.get("truncated")))


    async def _agir(self, hwnd: int, *args: str) -> bool:
        """Ação: qualquer falha (referência vencida, alvo ambíguo, teto...) é "não agiu"; o laço relê, como com a Sonda. O log
        leva só o código do erro. `ok` no envelope é "agiu"; a conferência dele (disposition) vai ao log como resultado."""
        try:
            self._conferir(hwnd, args[0])
            d = await self._chamar(*args)
        except ErroSonda as e:
            log.warning("sonda_ad %s", e)
            return False
        if isinstance(d.get("disposition"), str):
            log.info("sonda_ad %s: %s", args[0], d["disposition"])  # delivered_verified, delivered_unverified...
        return True

    async def clicar(self, hwnd: int, el: Elemento, endereco: str | None) -> bool:
        return await self._agir(hwnd, "click", el.runtime_id)

    async def digitar(self, hwnd: int, el: Elemento, texto: str, endereco: str | None, acrescentar: bool = True) -> bool:
        """Valor direto (`set-value`), sem foco: o `type` dele exige tomar o foco da janela. O `--` evita texto começando em "-".
        O `set-value` troca o valor INTEIRO (Bloco de Notas perdeu o texto, 11/11): em `acrescentar` lê o atual (`get`, medido:
        data.value) e grava atual + quebra de linha + texto. Não escreve se não conseguir ler, se a leitura passa de VALOR_MAX
        ou se uma segunda leitura (`--property text`) difere da primeira: set-value de leitura cortada apagaria o resto."""
        if acrescentar:
            try:
                self._conferir(hwnd, "get")
                atual = (await self._chamar("get", el.runtime_id, "--property", "value")).get("value")
            except ErroSonda as e:
                log.warning("sonda_ad %s", e)
                return False
            if not isinstance(atual, str) or len(atual) > VALOR_MAX:
                log.warning("sonda_ad get: leitura_nao_confiavel")
                return False
            try:  # a segunda leitura é obrigatória (fail-closed): value "" sem erro também pode ser leitura que falhou em documento com texto
                conferida = (await self._chamar("get", el.runtime_id, "--property", "text")).get("value")
            except ErroSonda as e:
                log.warning("sonda_ad %s", e)
                return False
            # editor vazio: o `text` dele devolve "" ou o NOME do campo (medido 11/11: "Editor de texto"); com texto, value == text
            confere = conferida in ("", el.nome) if atual == "" else conferida == atual
            if not isinstance(conferida, str) or not confere:
                log.warning("sonda_ad get: leitura_nao_confiavel")
                return False
            if atual:
                quebra = "" if atual.endswith(("\r", "\n")) else "\r\n" if "\r\n" in atual else "\r" if "\r" in atual else "\n" if "\n" in atual else "\r\n"
                texto = atual + quebra + texto
        return await self._agir(hwnd, "set-value", el.runtime_id, "--", texto)

    # `buscar` não existe aqui: o Enter seria `press`, e sem foco a documentação diz que ele falha em janela que não está na
    # frente. A composição da 9.5 manda `buscar` para a Sonda atual.

    async def rolar(self, hwnd: int, direcao: str) -> bool:
        """NÃO VERIFICADO: a sintaxe do `scroll` (aqui `--window-id` e `--direction`) não está na documentação lida."""
        return await self._agir(hwnd, "scroll", "--window-id", JANELA_ID.format(hwnd=hwnd), "--direction", direcao)

    async def voltar(self, hwnd: int) -> bool:
        """Acha o botão de voltar numa leitura nova e clica nele, como a Sonda."""
        try:
            leitura = await self.ler(hwnd)
        except ErroSonda as e:
            log.warning("sonda_ad %s", e)
            return False
        botao = next((e for e in leitura.elementos if e.tipo == "Button" and e.nome.strip().lower() in BOTOES_VOLTAR), None)
        return await self.clicar(hwnd, botao, None) if botao else False


def _secreto(no: dict) -> bool:
    """Campo de senha. O JSON real não tem chave `secure`: só `states` e `role`. shortcut: palavras prováveis ("protected",
    "password"...), NÃO vistas no JSON real (Notepad não tem campo de senha); a regra pelo nome do campo continua valendo."""
    marcas = [str(x).lower() for x in (no.get("states") or [])] + [str(no.get("role") or "").lower()]
    return any(p in m for m in marcas for p in ("password", "protected", "secure"))


def _percorrer(no, ancestrais: tuple[str, ...], elementos: list, textos: list) -> str:
    """Desce a árvore (JSON real 1.2.0: role, name, ref_id, states, available_actions, children). Nó com `ref_id` vira Elemento; os sem ref_id
    alimentam o texto da página. Devolve os nomes dos descendentes, que viram o `texto_interno` do pai."""
    if isinstance(no, list):
        return " ".join(f for n in no if (f := _percorrer(n, ancestrais, elementos, textos)))
    if not isinstance(no, dict):
        return ""
    if _secreto(no):  # campo seguro: nada dele (nome, valor, filhos) vai para texto, texto_interno nem ancestrais
        if no.get("ref_id"):  # só o Elemento marcado (o nome é o rótulo do campo), sem texto interno, para o regras_pc recusar escrever nele
            papel = str(no.get("role") or "")
            elementos.append(Elemento(id=len(elementos), nome=str(no.get("name") or ""), tipo=TIPOS.get(papel.lower(), papel.capitalize()), papel="",
                                      texto_interno="", ancestrais=ancestrais, senha=True, runtime_id=str(no["ref_id"]),
                                      host_do_link=None))
        return ""
    nome = str(no.get("name") or "")
    ancestrais_filhos = (*ancestrais, nome) if nome else ancestrais
    lugar = len(elementos)
    if no.get("ref_id"):
        elementos.append(None)  # reserva a posição: o pai vem antes dos filhos, o texto interno só depois
    elif nome:
        textos.append(nome)
    dentro = _percorrer(no.get("children"), ancestrais_filhos, elementos, textos)
    if no.get("ref_id"):
        papel = str(no.get("role") or "")
        elementos[lugar] = Elemento(id=lugar, nome=nome, tipo=TIPOS.get(papel.lower(), papel.capitalize()), papel="",
                                    texto_interno=dentro, ancestrais=ancestrais, senha=bool(_secreto(no)),
                                    runtime_id=str(no["ref_id"]), host_do_link=None)
    return " ".join(x for x in (nome, dentro) if x)


def esta_minimizada(hwnd: int) -> bool:
    return sys.platform == "win32" and bool(ctypes.WinDLL("user32").IsIconic(ctypes.c_void_p(hwnd)))


class SondaComposta:
    """O que a 9.5 entrega ao laço: leitura e ações da SondaAD nas janelas de app que ela aceita; todo o resto (mídia, som, envio,
    abrir site, trazer/fechar/minimizar, `buscar`) e as janelas que ela recusa (Chrome...) vão para a `Sonda` atual, como hoje."""

    def __init__(self, atual, ad: SondaAD, minimizada: Callable[[int], bool] = esta_minimizada):
        self.atual, self.ad, self.minimizada = atual, ad, minimizada

    def __getattr__(self, nome):  # só chega aqui o que não está definido abaixo
        return getattr(self.atual, nome)

    async def _por(self, hwnd: int):
        if not self.ad.aceita(hwnd):
            return self.atual
        if self.minimizada(hwnd) and not await self.atual.trazer(hwnd):  # minimizada, ele não age: restaura pela Sonda atual
            return self.atual
        return self.ad

    async def ler(self, hwnd: int) -> Leitura:
        return await (await self._por(hwnd)).ler(hwnd)

    async def clicar(self, hwnd: int, el: Elemento, endereco: str | None) -> bool:
        return await (await self._por(hwnd)).clicar(hwnd, el, endereco)

    async def digitar(self, hwnd: int, el: Elemento, texto: str, endereco: str | None, acrescentar: bool = True) -> bool:
        return await (await self._por(hwnd)).digitar(hwnd, el, texto, endereco, acrescentar)

    async def buscar(self, hwnd: int, el: Elemento, texto: str, endereco: str | None) -> bool:
        """A SondaAD não tem `buscar` e o `runtime_id` dela não vale na Sonda atual: relê a janela com a Sonda atual e acha o
        elemento por nome e tipo. Zero ou vários iguais: não agiu (o laço relê)."""
        if await self._por(hwnd) is self.atual:
            return await self.atual.buscar(hwnd, el, texto, endereco)
        try:
            achados = [e for e in (await self.atual.ler(hwnd)).elementos if (e.nome, e.tipo) == (el.nome, el.tipo)]
        except ErroSonda as e:
            log.warning("sonda_ad buscar: %s", e)
            return False
        # o elemento relido na Sonda atual pode ser outro: confere de novo que não é campo sensível
        return len(achados) == 1 and not e_campo_sensivel(achados[0]) and await self.atual.buscar(hwnd, achados[0], texto, endereco)

    async def rolar(self, hwnd: int, direcao: str) -> bool:
        return await (await self._por(hwnd)).rolar(hwnd, direcao)

    async def voltar(self, hwnd: int) -> bool:
        return await (await self._por(hwnd)).voltar(hwnd)


SONDA = "agent-desktop"  # "uia" (sonda.ps1, a de hoje) ou "agent-desktop" (SondaAD + a atual); a Fase 10 troca e repete as cenas


def escolher_sonda(atual, segredos: frozenset[str], sonda: str | None = None, procurar=shutil.which):
    """Backend do laço pela constante. Sem o executável no PATH, fica a `Sonda` atual e avisa (sem conteúdo) no log."""
    if (sonda or SONDA) != "agent-desktop":
        return atual
    exe = executavel(procurar)
    if not exe:
        log.warning("agent-desktop não encontrado: usando a sonda atual")
        return atual
    return SondaComposta(atual, SondaAD(segredos=segredos, comando=[exe]))


def executavel(procurar=shutil.which) -> str | None:
    """Caminho que o Python consegue abrir: o npm põe no PATH um `.cmd`, que `create_subprocess_exec` não roda sem shell."""
    achado = procurar(EXECUTAVEL)
    if achado and achado.lower().endswith(".cmd"):
        exe = Path(achado).parent / "node_modules" / "agent-desktop" / "bin" / "agent-desktop-win32-x64.exe"
        return str(exe) if exe.is_file() else None
    return achado
