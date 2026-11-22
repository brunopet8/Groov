"""Janela do GROOV (Chrome --app): oculta (sem botão na barra de tarefas) quando ele dorme e volta em tela cheia no 2º monitor quando ele acorda.

Só Win32 por ctypes (sem porta de depuração). O Chrome nasce em --start-fullscreen (ver abrir_janela.py) e restaura em tela cheia;
a janela nunca é ativada, então o teclado fica com o que o usuário estiver usando. Oculta, o microfone/WebRTC e o áudio de saída seguem vivos (medido).
"""
import ctypes
import ctypes.wintypes as wt
import logging
import os
import threading
from typing import NamedTuple, Protocol

log = logging.getLogger("groov.tela")

PORTA_PADRAO = 7860
ACORDADO = ("acordando", "carregando", "conversando", "ocioso")
Retangulo = tuple[int, int, int, int]  # esquerda, topo, direita, base, em pixels da área de trabalho virtual


class Monitor(NamedTuple):
    rect: Retangulo
    primario: bool


def porta() -> int:
    return int(os.environ.get("GROOV_PORTA", PORTA_PADRAO))  # outra porta só para testar sem brigar com a janela aberta


def titulo_da_janela(porta: int) -> str:
    """Igual ao <title> servido por servidor.py: um teste em outra porta não pode ter o título da janela de verdade."""
    return "GROOV" if porta == PORTA_PADRAO else f"GROOV :{porta}"


def escolher_monitor(monitores: list[Monitor]) -> Retangulo | None:
    """O 2º monitor é o primeiro que não é o primário; com um só, o primário."""
    for m in monitores:
        if not m.primario:
            return m.rect
    return monitores[0].rect if monitores else None


class Backend(Protocol):
    def achar(self, titulo: str) -> int | None: ...
    def monitores(self) -> list[Monitor]: ...
    def esconder(self, janela: int) -> None: ...
    def mostrar(self, janela: int, retangulo: Retangulo | None) -> None: ...
    def fechar(self, janela: int) -> None: ...


class _MonitorInfo(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("rcMonitor", wt.RECT), ("rcWork", wt.RECT), ("dwFlags", wt.DWORD)]


class Win32:
    SW_HIDE, SW_SHOWNOACTIVATE = 0, 4
    HWND_TOPMOST, HWND_NOTOPMOST = -1, -2
    SWP_NOACTIVATE, SWP_SHOWWINDOW = 0x0010, 0x0040
    WM_CLOSE = 0x0010

    def __init__(self, classe: str = "Chrome_WidgetWin_1"):
        self._classe = classe
        self._u = u = ctypes.WinDLL("user32", use_last_error=True)
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # pixels físicos, senão o monitor com escala ≠ 100% vem virtualizado (devolve HRESULT: não levanta se já estava definido)
        h = ctypes.c_void_p
        u.GetWindowTextW.argtypes = [h, wt.LPWSTR, ctypes.c_int]
        u.GetClassNameW.argtypes = [h, wt.LPWSTR, ctypes.c_int]
        u.GetMonitorInfoW.argtypes = [h, ctypes.POINTER(_MonitorInfo)]
        u.ShowWindow.argtypes = [h, ctypes.c_int]
        u.SetWindowPos.argtypes = [h, h, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
        u.PostMessageW.argtypes = [h, ctypes.c_uint, wt.WPARAM, wt.LPARAM]

    def achar(self, titulo: str) -> int | None:
        achados: list[int] = []

        @ctypes.WINFUNCTYPE(wt.BOOL, ctypes.c_void_p, wt.LPARAM)
        def olhar(h, _):
            t, c = ctypes.create_unicode_buffer(256), ctypes.create_unicode_buffer(256)
            self._u.GetWindowTextW(h, t, 256)
            self._u.GetClassNameW(h, c, 256)
            if t.value == titulo and c.value == self._classe:
                achados.append(h)
            return True

        self._u.EnumWindows(olhar, 0)
        return achados[0] if achados else None

    def monitores(self) -> list[Monitor]:
        lista: list[Monitor] = []

        @ctypes.WINFUNCTYPE(wt.BOOL, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(wt.RECT), wt.LPARAM)
        def olhar(hm, _hdc, _rect, _):
            mi = _MonitorInfo()
            mi.cbSize = ctypes.sizeof(mi)
            self._u.GetMonitorInfoW(hm, ctypes.byref(mi))
            r = mi.rcMonitor
            lista.append(Monitor((r.left, r.top, r.right, r.bottom), bool(mi.dwFlags & 1)))  # 1 = MONITORINFOF_PRIMARY
            return True

        self._u.EnumDisplayMonitors(None, None, olhar, 0)
        return lista

    def esconder(self, janela: int) -> None:
        # SW_HIDE e não minimizar: minimizada ela deixava um botão na barra de tarefas (e no Alt+Tab). Reaparece em tela cheia
        # com o mostrar(). Limite medido: se a janela tinha o foco (o boot, logo depois de o Chrome abrir) o foco pode ficar
        # nela, invisível, até o usuário clicar em qualquer outra janela; minimizar tinha o mesmo limite.
        self._u.ShowWindow(janela, self.SW_HIDE)

    def mostrar(self, janela: int, retangulo: Retangulo | None) -> None:
        self._u.ShowWindow(janela, self.SW_SHOWNOACTIVATE)  # mostra a oculta (ou restaura a minimizada) sem ativar
        if retangulo is None:
            return
        e, t, d, b = retangulo
        # TOPMOST traz à frente sem precisar do foco; NOTOPMOST em seguida deixa o usuário clicar em outra janela por cima
        for z in (self.HWND_TOPMOST, self.HWND_NOTOPMOST):
            if not self._u.SetWindowPos(janela, z, e, t, d - e, b - t, self.SWP_NOACTIVATE | self.SWP_SHOWWINDOW):
                raise ctypes.WinError(ctypes.get_last_error())  # o ctypes não levanta sozinho

    def fechar(self, janela: int) -> None:
        if not self._u.PostMessageW(janela, self.WM_CLOSE, 0, 0):  # assíncrono: o Chrome fecha sozinho
            raise ctypes.WinError(ctypes.get_last_error())


class Tela:
    def __init__(self, titulo: str, backend: Backend | None = None):
        self._titulo = titulo
        self._backend = backend or Win32()
        self._trava = threading.Lock()  # o servidor chama de threads diferentes

    def ao_estado(self, estado: str) -> None:
        """Nunca levanta: a janela é enfeite e não pode derrubar a conversa."""
        try:
            with self._trava:
                if estado == "dormindo":
                    self._esconder()
                elif estado in ACORDADO:
                    self._aparecer()
        except Exception:
            log.exception("não consegui mexer na janela do GROOV")

    def fechar(self) -> None:
        """Nunca levanta: quem encerra o GROOV ainda precisa parar o servidor."""
        try:
            with self._trava:
                janela = self._backend.achar(self._titulo)
                if janela is not None:
                    self._backend.fechar(janela)
        except Exception:
            log.exception("não consegui fechar a janela do GROOV")

    # Sem memória do que já fez: cada estado refaz a ação (idempotente), então uma falha ou um clique do usuário se corrige sozinho
    # no próximo estado, e no boot (janela nascida em tela cheia) o 1º "dormindo" a guarda.
    def _esconder(self) -> None:
        janela = self._backend.achar(self._titulo)
        if janela is not None:
            self._backend.esconder(janela)

    def _aparecer(self) -> None:
        janela = self._backend.achar(self._titulo)
        if janela is None:
            log.warning("janela %r não encontrada", self._titulo)  # warning: o info não chega ao conversa.log (sem handler)
            return
        self._backend.mostrar(janela, escolher_monitor(self._backend.monitores()))


_tela: Tela | None = None


def ativar(porta: int, backend: Backend | None = None) -> None:
    """Desligada por padrão: só servidor.main() liga (os testes não mexem em janela alguma; uma medição em outra porta só
    enxerga a janela de título "GROOV :<porta>", nunca a de verdade)."""
    global _tela
    _tela = Tela(titulo_da_janela(porta), backend)


def ao_estado(estado: str) -> None:
    if _tela:
        _tela.ao_estado(estado)


def fechar() -> None:
    if _tela:
        _tela.fechar()
