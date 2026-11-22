import ctypes
import ctypes.wintypes
import sys

import pytest

from src.conversa import tela
from src.conversa.tela import Monitor, Tela, escolher_monitor, titulo_da_janela

PRIMARIO = Monitor((0, 0, 1920, 1080), True)
SECUNDARIO = Monitor((-1366, 0, 0, 768), False)


class Falso:
    """Backend sem Win32: guarda o que a Tela mandou fazer."""

    def __init__(self, janela=7, monitores=(PRIMARIO, SECUNDARIO)):
        self.janela, self._monitores, self.chamadas = janela, list(monitores), []

    def achar(self, titulo):
        self.chamadas.append(("achar", titulo))
        return self.janela

    def monitores(self):
        return self._monitores

    def esconder(self, janela):
        self.chamadas.append(("esconder", janela))

    def mostrar(self, janela, retangulo):
        self.chamadas.append(("mostrar", janela, retangulo))

    def fechar(self, janela):
        self.chamadas.append(("fechar", janela))


def acoes(backend):
    return [c for c in backend.chamadas if c[0] != "achar"]


def test_segundo_monitor_e_o_primeiro_que_nao_e_primario():
    assert escolher_monitor([PRIMARIO, SECUNDARIO]) == SECUNDARIO.rect
    assert escolher_monitor([SECUNDARIO, PRIMARIO]) == SECUNDARIO.rect  # a ordem da lista não importa
    terceiro = Monitor((1920, 0, 3840, 1080), False)
    assert escolher_monitor([PRIMARIO, SECUNDARIO, terceiro]) == SECUNDARIO.rect


def test_com_um_monitor_so_usa_o_primario_e_sem_monitor_nao_escolhe():
    assert escolher_monitor([PRIMARIO]) == PRIMARIO.rect
    assert escolher_monitor([]) is None


def test_titulo_da_janela_por_porta():
    assert titulo_da_janela(7860) == "GROOV"
    assert titulo_da_janela(7861) == "GROOV :7861"  # um teste em outra porta nunca esconde a janela de verdade


@pytest.mark.parametrize("estado", ["acordando", "carregando", "conversando", "ocioso"])
def test_acordado_mostra_a_janela_no_segundo_monitor(estado):
    b = Falso()
    Tela("GROOV", b).ao_estado(estado)
    assert acoes(b) == [("mostrar", 7, SECUNDARIO.rect)] and ("achar", "GROOV") in b.chamadas


def test_fechar_manda_fechar_a_janela_achada():
    b = Falso()
    Tela("GROOV", b).fechar()
    assert acoes(b) == [("fechar", 7)]


def test_fechar_nunca_levanta():
    Tela("GROOV", Falso(janela=None)).fechar()  # sem janela
    b = Falso()
    b.fechar = lambda janela: 1 / 0
    Tela("GROOV", b).fechar()


def test_fechar_do_modulo_sem_tela_ativa_nao_faz_nada(monkeypatch):
    monkeypatch.setattr(tela, "_tela", None)
    tela.fechar()
    b = Falso()
    tela.ativar(7861, backend=b)
    tela.fechar()
    assert acoes(b) == [("fechar", 7)]


def test_dormindo_esconde():
    b = Falso()
    Tela("GROOV", b).ao_estado("dormindo")
    assert acoes(b) == [("esconder", 7)]  # também no boot: a janela nasce em tela cheia e o 1º "dormindo" a guarda


def test_cada_estado_refaz_a_acao_sem_guardar_memoria():
    """Idempotente: uma falha ou um clique do usuário na janela se corrigem no próximo estado; sem flag para ficar velha."""
    b = Falso()
    t = Tela("GROOV", b)
    for estado in ["acordando", "carregando", "conversando"]:
        t.ao_estado(estado)
    t.ao_estado("dormindo")
    t.ao_estado("dormindo")
    t.ao_estado("acordando")
    assert [c[0] for c in acoes(b)] == ["mostrar"] * 3 + ["esconder"] * 2 + ["mostrar"]


def test_estado_desconhecido_nao_mexe_na_janela():
    b = Falso()
    Tela("GROOV", b).ao_estado("sei-la")
    assert b.chamadas == []


def test_janela_nao_achada_nao_quebra_e_tenta_de_novo_no_proximo_estado():
    b = Falso(janela=None)
    t = Tela("GROOV", b)
    t.ao_estado("acordando")
    t.ao_estado("dormindo")
    assert acoes(b) == []
    b.janela = 9
    t.ao_estado("conversando")
    assert acoes(b) == [("mostrar", 9, SECUNDARIO.rect)]


def test_falha_do_win32_nao_chega_na_conversa_e_o_proximo_estado_tenta_de_novo():
    b = Falso()
    falhas = [True]
    original = b.mostrar

    def mostrar(janela, retangulo):
        if falhas:
            falhas.pop()
            raise OSError("Win32 falhou")
        original(janela, retangulo)

    b.mostrar = mostrar
    t = Tela("GROOV", b)
    t.ao_estado("acordando")  # não levanta
    t.ao_estado("conversando")
    assert acoes(b) == [("mostrar", 7, SECUNDARIO.rect)]


def test_gancho_global_fica_desligado_ate_ativar(monkeypatch):
    monkeypatch.setattr(tela, "_tela", None)
    tela.ao_estado("acordando")  # sem ativar não faz nada (testes e medições não mexem em janela alguma)
    b = Falso()
    tela.ativar(7861, backend=b)
    tela.ao_estado("dormindo")
    assert ("achar", "GROOV :7861") in b.chamadas and acoes(b) == [("esconder", 7)]


@pytest.mark.skipif(sys.platform != "win32", reason="Win32")
def test_win32_de_verdade_com_uma_janela_tk():
    tk = pytest.importorskip("tkinter")
    w = tela.Win32(classe="TkTopLevel")  # antes de criar janelas: liga o DPI por monitor do processo
    try:
        raiz = tk.Tk()
    except tk.TclError:
        pytest.skip("sem área de trabalho para abrir a janela")
    raiz.title("GROOV :9999")
    raiz.geometry("200x80+300+300")
    raiz.update()
    try:
        h = w.achar("GROOV :9999")
        assert h and w.achar("GROOV :9998") is None
        monitores = w.monitores()
        assert monitores and sum(m.primario for m in monitores) == 1
        w.esconder(h)
        raiz.update()
        assert raiz.state() == "withdrawn"  # oculta de vez: sem botão na barra de tarefas nem Alt+Tab
        assert not ctypes.windll.user32.IsWindowVisible(ctypes.c_void_p(h))
        w.mostrar(h, (300, 300, 500, 380))
        raiz.update()
        assert raiz.state() == "normal"
        r = ctypes.wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(ctypes.c_void_p(h), ctypes.byref(r))
        assert (r.left, r.top, r.right, r.bottom) == (300, 300, 500, 380)
    finally:
        raiz.destroy()
