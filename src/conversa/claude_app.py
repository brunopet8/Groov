"""Claude desktop dentro da janela do GROOV: abre o chat no app (link claude://) e encaixa a janela do app sobre o painel
grande "CLAUDE CODE"; ao fechar o painel, dormir ou cair a conexão, ela volta para onde estava.

Uma página não contém um app nativo: a janela do Claude fica por cima (TOPMOST) no retângulo do painel. Só Win32 por
ctypes, como tela.py. O app tem uma janela principal só (a mesma em que o usuário programa), por isso guardar e devolver a
posição. Link e pasta de sessões não são documentados (achados no app 5.11492, 14/11): uma atualização pode mudá-los.
"""
import ctypes
import ctypes.wintypes as wt
import json
import logging
import math
import os
import re
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from src.conversa import tela
from src.conversa.mensagens import Recusada

log = logging.getLogger("groov.claude_app")

SESSOES = Path(os.environ.get("LOCALAPPDATA", "")) / "Claude-Data" / "claude_pzs8sxrjxfjjc" / "claude-code-sessions"
_ID_DO_APP = re.compile(r"^local_[A-Za-z0-9-]{1,64}$")  # o mesmo formato que o app aceita no ?session=
Area = tuple[float, float, float, float]  # x, y, largura, altura: frações da janela do GROOV
MINIMO = 0.05  # fração: painel menor que isso viraria uma janela de poucos pixels


def sessao_do_app(cli_id: str, raiz: Path = SESSOES) -> str:
    """A sessão do app que continua o chat do PROJETOS (campo cliSessionId), ou "last" (a última do app). Lê só três
    campos; nada do chat vai ao log."""
    try:
        arquivos = list(raiz.rglob("local_*.json"))
    except OSError:
        return "last"
    for arquivo in arquivos:
        try:
            d = json.loads(arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(d, dict) or d.get("cliSessionId") != cli_id or d.get("isArchived"):
            continue
        sessao = d.get("sessionId")
        if isinstance(sessao, str) and _ID_DO_APP.fullmatch(sessao):  # fullmatch: "$" aceitaria uma quebra de linha no fim
            return sessao
    return "last"


def link(sessao: str) -> str:
    return f"claude://code/continue?session={sessao}"


def ler_area(d: object) -> Area:
    """O retângulo do painel vem da janela (fronteira de confiança): 4 números finitos em [0, 1], dentro da tela."""
    if not isinstance(d, dict):
        raise Recusada("área inválida")
    valores = [d.get(k) for k in ("x", "y", "w", "h")]
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in valores):
        raise Recusada("área inválida")
    x, y, w, h = (float(v) for v in valores)
    if x < 0 or y < 0 or w < MINIMO or h < MINIMO or x + w > 1.001 or y + h > 1.001:
        raise Recusada("área inválida")
    return x, y, w, h


def retangulo(groov: tela.Retangulo, area: Area) -> tela.Retangulo:
    """Área (frações) dentro da janela do GROOV → esquerda, topo, direita, base em pixels físicos."""
    e, t, d, b = groov
    x, y, w, h = area
    esquerda, topo = e + round(x * (d - e)), t + round(y * (b - t))
    return esquerda, topo, esquerda + round(w * (d - e)), topo + round(h * (b - t))


class Backend(Protocol):
    def achar_claude(self) -> int | None: ...
    def retangulo_groov(self) -> tela.Retangulo | None: ...
    def posicao(self, janela: int) -> object: ...
    def encaixar(self, janela: int, ret: tela.Retangulo) -> None: ...
    def soltar(self, janela: int, posicao: object) -> None: ...
    def ativar(self, janela: int) -> None: ...


class Encaixe:
    def __init__(self, backend: Backend, abrir_link: Callable[[str], None] = os.startfile, raiz: Path = SESSOES,
                 esperar: Callable[[], None] = lambda: time.sleep(0.25), tentativas: int = 40):
        self._backend = backend
        self._abrir_link = abrir_link
        self._raiz = raiz
        self._esperar = esperar
        self._tentativas = tentativas  # x 0,25 s: o app frio leva alguns segundos para mostrar a janela
        self._trava = threading.Lock()  # o servidor chama de threads diferentes
        self._aberto = False
        self._area: Area | None = None
        self._salvo: tuple[int, object] | None = None  # janela e posição de antes do 1º encaixe

    def abrir(self, cli_id: str) -> bool:
        """Abre o chat no app e espera a janela dele; encaixa já se o painel mediu. False: o app não apareceu."""
        self._abrir_link(link(sessao_do_app(cli_id, self._raiz)))
        with self._trava:
            self._aberto = True
        for _ in range(self._tentativas):
            if self._backend.achar_claude() is not None:
                with self._trava:
                    # o painel pode ter fechado durante a espera: aí o app fica onde abriu, sem TOPMOST
                    if self._aberto and self._area is not None and not self._encaixar():
                        log.warning("o app abriu, mas a janela do GROOV não foi achada para o encaixe")
                return True  # o app abriu; o encaixe sem a janela do GROOV não é "não abriu"
            self._esperar()
        log.warning("o app do Claude não apareceu")
        return False

    def area(self, area: Area) -> None:
        with self._trava:
            self._area = area
            if self._aberto:
                self._encaixar()

    def soltar(self) -> None:
        """Nunca levanta: o Claude fechado à mão não derruba a conversa."""
        with self._trava:
            salvo, self._salvo, self._aberto = self._salvo, None, False
            if salvo is None:
                return
            try:
                if self._backend.achar_claude() != salvo[0]:  # o usuário fechou o app: o HWND pode ser de outra janela
                    return
                self._backend.soltar(*salvo)
            except Exception:
                log.exception("não consegui devolver a janela do Claude")

    def _encaixar(self) -> bool:
        janela = self._backend.achar_claude()
        groov = self._backend.retangulo_groov()
        if janela is None or groov is None or self._area is None:
            return False
        primeiro = self._salvo is None or self._salvo[0] != janela
        if primeiro:
            self._salvo = (janela, self._backend.posicao(janela))
        self._backend.encaixar(janela, retangulo(groov, self._area))
        if primeiro:
            self._backend.ativar(janela)  # foco só ao abrir: a cada redimensionar roubaria o teclado
        return True


class _Placement(ctypes.Structure):
    _fields_ = [("length", wt.UINT), ("flags", wt.UINT), ("showCmd", wt.UINT), ("ptMinPosition", wt.POINT),
                ("ptMaxPosition", wt.POINT), ("rcNormalPosition", wt.RECT)]


class Win32(tela.Win32):
    SW_RESTORE = 9
    SWP_NOSIZE, SWP_NOMOVE = 0x0001, 0x0002
    SWP_ASYNCWINDOWPOS = 0x4000  # app travado não trava o servidor (a trava do Encaixe fica presa só o tempo de postar)

    def __init__(self, titulo_groov: str):
        super().__init__()  # pixels físicos (DPI) e os argtypes de tela.Win32
        self._titulo_groov = titulo_groov
        u, h = self._u, ctypes.c_void_p
        for nome in ("IsWindowVisible", "IsIconic", "IsZoomed", "IsWindow", "SetForegroundWindow"):
            getattr(u, nome).argtypes = [h]
        u.GetWindow.argtypes, u.GetWindow.restype = [h, ctypes.c_uint], h
        u.GetWindowThreadProcessId.argtypes = [h, ctypes.POINTER(wt.DWORD)]
        u.GetWindowRect.argtypes = [h, ctypes.POINTER(wt.RECT)]
        u.GetWindowPlacement.argtypes = [h, ctypes.POINTER(_Placement)]
        u.SetWindowPlacement.argtypes = [h, ctypes.POINTER(_Placement)]
        self._k = k = ctypes.WinDLL("kernel32", use_last_error=True)
        k.OpenProcess.restype = h
        k.QueryFullProcessImageNameW.argtypes = [h, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)]
        k.CloseHandle.argtypes = [h]

    def _programa(self, janela: int) -> str:
        pid = wt.DWORD()
        self._u.GetWindowThreadProcessId(janela, ctypes.byref(pid))
        processo = self._k.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not processo:
            return ""
        try:
            nome, n = ctypes.create_unicode_buffer(520), wt.DWORD(520)
            return os.path.basename(nome.value).lower() if self._k.QueryFullProcessImageNameW(processo, 0, nome, ctypes.byref(n)) else ""
        finally:
            self._k.CloseHandle(processo)

    def achar_claude(self) -> int | None:
        achados: list[int] = []

        @ctypes.WINFUNCTYPE(wt.BOOL, ctypes.c_void_p, wt.LPARAM)
        def olhar(h, _):
            if not self._u.IsWindowVisible(h) or self._u.GetWindow(h, 4):  # 4 = GW_OWNER: janelas donas são diálogos
                return True
            t, c = ctypes.create_unicode_buffer(256), ctypes.create_unicode_buffer(256)
            self._u.GetWindowTextW(h, t, 256)
            self._u.GetClassNameW(h, c, 256)
            # claude.exe também é o CLI, mas ele não tem janela Chrome_WidgetWin_1
            if c.value == "Chrome_WidgetWin_1" and t.value.startswith("Claude") and self._programa(h) == "claude.exe":
                achados.append(h)
            return True

        self._u.EnumWindows(olhar, 0)
        return achados[0] if achados else None

    def retangulo_groov(self) -> tela.Retangulo | None:
        janela = self.achar(self._titulo_groov)
        if janela is None:
            return None
        r = wt.RECT()
        self._u.GetWindowRect(janela, ctypes.byref(r))  # em tela cheia a janela é toda área do cliente
        return r.left, r.top, r.right, r.bottom

    def posicao(self, janela: int) -> _Placement:
        p = _Placement()
        p.length = ctypes.sizeof(p)
        if not self._u.GetWindowPlacement(janela, ctypes.byref(p)):
            raise ctypes.WinError(ctypes.get_last_error())
        return p

    def encaixar(self, janela: int, ret: tela.Retangulo) -> None:
        if self._u.IsIconic(janela) or self._u.IsZoomed(janela):
            self._u.ShowWindow(janela, self.SW_RESTORE)  # maximizada não aceita outro tamanho
        e, t, d, b = ret
        # duas vezes: ao trocar de monitor com outra escala o app aplica o tamanho sugerido pelo Windows (WM_DPICHANGED)
        for _ in range(2):
            if not self._u.SetWindowPos(janela, self.HWND_TOPMOST, e, t, d - e, b - t,
                                        self.SWP_SHOWWINDOW | self.SWP_ASYNCWINDOWPOS):
                raise ctypes.WinError(ctypes.get_last_error())

    def ativar(self, janela: int) -> None:
        self._u.SetForegroundWindow(janela)  # pode ser recusado pelo Windows; aí o clique do usuário dá o foco

    def soltar(self, janela: int, posicao: _Placement) -> None:
        if not self._u.IsWindow(janela):
            return
        self._u.SetWindowPos(janela, self.HWND_NOTOPMOST, 0, 0, 0, 0,
                             self.SWP_NOMOVE | self.SWP_NOSIZE | self.SWP_NOACTIVATE | self.SWP_ASYNCWINDOWPOS)
        if not self._u.SetWindowPlacement(janela, ctypes.byref(posicao)):
            raise ctypes.WinError(ctypes.get_last_error())


_encaixe: Encaixe | None = None


def ativar(porta: int, backend: Backend | None = None) -> None:
    """Desligado por padrão: só servidor.main() liga, como tela.ativar (os testes não mexem em janela alguma)."""
    global _encaixe
    _encaixe = Encaixe(backend or Win32(tela.titulo_da_janela(porta)))


def abrir(cli_id: str) -> bool:
    if _encaixe is None:
        raise Recusada("app do Claude indisponível")
    return _encaixe.abrir(cli_id)


def area(a: Area) -> None:
    if _encaixe:
        _encaixe.area(a)


def soltar() -> None:
    if _encaixe:
        _encaixe.soltar()


def ao_estado(estado: str) -> None:
    if estado == "dormindo":  # a janela do GROOV some: o Claude não fica flutuando sozinho no 2º monitor
        soltar()
