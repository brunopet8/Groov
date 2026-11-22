import json

import pytest

from src.conversa import claude_app
from src.conversa.claude_app import Encaixe, ler_area, link, retangulo, sessao_do_app
from src.conversa.mensagens import Recusada

CLI = "00000000-0000-4000-8000-000000000001"


def _sessao(raiz, nome, **dados):
    pasta = raiz / "conta" / "org"
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / f"{nome}.json").write_text(json.dumps(dados), encoding="utf-8")


def test_sessao_do_app_acha_pelo_id_do_chat(tmp_path):
    _sessao(tmp_path, "local_aaa", sessionId="local_aaa", cliSessionId="outro", isArchived=False)
    _sessao(tmp_path, "local_bbb", sessionId="local_bbb", cliSessionId=CLI, isArchived=False)
    assert sessao_do_app(CLI, tmp_path) == "local_bbb"


def test_sessao_do_app_sem_par_arquivada_ou_estranha_vira_last(tmp_path):
    assert sessao_do_app(CLI, tmp_path / "nao_existe") == "last"
    _sessao(tmp_path, "local_ccc", sessionId="local_ccc", cliSessionId=CLI, isArchived=True)
    _sessao(tmp_path, "local_ddd", sessionId="local_x&y=1", cliSessionId=CLI, isArchived=False)  # id fora do formato
    (tmp_path / "conta" / "org" / "local_eee.json").write_text("{quebrado", encoding="utf-8")
    assert sessao_do_app(CLI, tmp_path) == "last"


def test_link():
    assert link("local_bbb") == "claude://code/continue?session=local_bbb"
    assert link("last") == "claude://code/continue?session=last"


@pytest.mark.parametrize("d", [None, {}, {"x": 0, "y": 0, "w": 1}, {"x": "0", "y": 0, "w": 1, "h": 1},
                               {"x": -0.1, "y": 0, "w": 0.5, "h": 0.5}, {"x": 0.6, "y": 0, "w": 0.5, "h": 0.5},
                               {"x": 0, "y": 0, "w": 0, "h": 0.5}, {"x": 0, "y": 0, "w": float("nan"), "h": 0.5},
                               {"x": True, "y": 0, "w": 0.5, "h": 0.5}])
def test_ler_area_recusa_o_que_nao_e_fracao(d):
    with pytest.raises(Recusada):
        ler_area(d)


def test_ler_area_e_retangulo():
    area = ler_area({"x": 0.1, "y": 0.2, "w": 0.5, "h": 0.25})
    # GROOV em tela cheia no 2º monitor, à esquerda do primário
    assert retangulo((-1920, 0, 0, 1080), area) == (-1728, 216, -768, 486)


class BackendFalso:
    def __init__(self, claude=7, groov=(0, 0, 1000, 500)):
        self.claude, self.groov, self.feitos = claude, groov, []

    def achar_claude(self):
        return self.claude

    def retangulo_groov(self):
        return self.groov

    def posicao(self, janela):
        return f"posicao-de-{janela}"

    def encaixar(self, janela, ret):
        self.feitos.append(("encaixar", janela, ret))

    def soltar(self, janela, posicao):
        self.feitos.append(("soltar", janela, posicao))

    def ativar(self, janela):
        self.feitos.append(("ativar", janela))


AREA = {"x": 0.1, "y": 0.1, "w": 0.8, "h": 0.8}


def _encaixe(tmp_path, backend=None, **extra):
    abertos = []
    e = Encaixe(backend or BackendFalso(), abrir_link=abertos.append, raiz=tmp_path, esperar=lambda: None, **extra)
    return e, abertos


def test_abrir_e_area_encaixam_e_soltar_devolve(tmp_path):
    _sessao(tmp_path, "local_bbb", sessionId="local_bbb", cliSessionId=CLI, isArchived=False)
    b = BackendFalso()
    e, abertos = _encaixe(tmp_path, b)
    e.area(ler_area(AREA))
    assert b.feitos == []  # sem pedido de abrir, a área só fica guardada
    assert e.abrir(CLI) is True
    assert abertos == ["claude://code/continue?session=local_bbb"]
    assert b.feitos == [("encaixar", 7, (100, 50, 900, 450)), ("ativar", 7)]
    e.area(ler_area({"x": 0, "y": 0, "w": 0.5, "h": 0.5}))  # painel mudou de tamanho
    assert b.feitos[-1] == ("encaixar", 7, (0, 0, 500, 250))
    e.soltar()
    assert b.feitos[-1] == ("soltar", 7, "posicao-de-7")  # a posição de antes do 1º encaixe, não a do 2º
    n = len(b.feitos)
    e.soltar()  # idempotente
    e.area(ler_area(AREA))  # depois de solto, área nova não puxa o Claude de volta
    assert len(b.feitos) == n


def test_abrir_espera_a_janela_do_app_aparecer(tmp_path):
    b = BackendFalso(claude=None)
    esperas = []

    def esperar():
        esperas.append(1)
        if len(esperas) == 3:
            b.claude = 9  # o app terminou de abrir
    e = Encaixe(b, abrir_link=lambda _l: None, raiz=tmp_path, esperar=esperar)
    e.area(ler_area(AREA))
    assert e.abrir(CLI) is True
    assert b.feitos == [("encaixar", 9, (100, 50, 900, 450)), ("ativar", 9)]


def test_abrir_desiste_se_o_app_nao_aparece(tmp_path):
    e, _ = _encaixe(tmp_path, BackendFalso(claude=None), tentativas=4)
    e.area(ler_area(AREA))
    assert e.abrir(CLI) is False


def test_sem_janela_do_groov_nao_encaixa(tmp_path):
    b = BackendFalso(groov=None)
    e, _ = _encaixe(tmp_path, b)
    e.area(ler_area(AREA))
    assert e.abrir(CLI) is True and b.feitos == []


def test_abrir_antes_da_area_encaixa_quando_ela_chega(tmp_path):
    b = BackendFalso()
    e, _ = _encaixe(tmp_path, b)
    assert e.abrir(CLI) is True  # o app abriu; o painel ainda não mediu
    assert b.feitos == []
    e.area(ler_area(AREA))
    assert b.feitos == [("encaixar", 7, (100, 50, 900, 450)), ("ativar", 7)]


def test_modulo_desligado_nao_faz_nada():
    claude_app._encaixe = None
    claude_app.ao_estado("dormindo")
    claude_app.soltar()


def test_ao_estado_dormindo_solta(tmp_path):
    b = BackendFalso()
    e, _ = _encaixe(tmp_path, b)
    claude_app._encaixe = e
    try:
        e.area(ler_area(AREA))
        e.abrir(CLI)
        claude_app.ao_estado("ocioso")
        assert b.feitos[-1][0] == "ativar"
        claude_app.ao_estado("dormindo")
        assert b.feitos[-1] == ("soltar", 7, "posicao-de-7")
    finally:
        claude_app._encaixe = None


def test_erro_do_backend_nao_sobe_no_soltar(tmp_path):
    class Quebrado(BackendFalso):
        def soltar(self, janela, posicao):
            raise OSError("janela sumiu")
    e, _ = _encaixe(tmp_path, Quebrado())
    e.area(ler_area(AREA))
    e.abrir(CLI)
    e.soltar()  # não levanta: o Claude fechado pelo usuário não derruba a conversa


def test_painel_fechado_enquanto_o_app_abre_nao_encaixa(tmp_path):
    """Revisão: soltar durante a espera do app frio; a janela que aparece depois não pode ficar TOPMOST sem painel."""
    b = BackendFalso(claude=None)
    e = None

    def esperar():
        e.soltar()  # o usuário fechou o painel
        b.claude = 9
    e = Encaixe(b, abrir_link=lambda _l: None, raiz=tmp_path, esperar=esperar)
    e.area(ler_area(AREA))
    assert e.abrir(CLI) is True and b.feitos == []


def test_foco_so_no_primeiro_encaixe(tmp_path):
    b = BackendFalso()
    e, _ = _encaixe(tmp_path, b)
    e.area(ler_area(AREA))
    e.abrir(CLI)
    e.area(ler_area({"x": 0, "y": 0, "w": 0.5, "h": 0.5}))
    assert [f[0] for f in b.feitos].count("ativar") == 1


def test_app_abriu_mas_sem_janela_do_groov_nao_e_erro(tmp_path):
    e, _ = _encaixe(tmp_path, BackendFalso(groov=None))
    e.area(ler_area(AREA))
    assert e.abrir(CLI) is True  # o app abriu; "não abriu" seria mentira


def test_soltar_nao_mexe_em_janela_que_ja_nao_e_o_claude(tmp_path):
    b = BackendFalso()
    e, _ = _encaixe(tmp_path, b)
    e.area(ler_area(AREA))
    e.abrir(CLI)
    b.claude = None  # o usuário fechou o app (o HWND pode ser reaproveitado por outra janela)
    e.soltar()
    assert b.feitos[-1][0] != "soltar"


def test_ler_area_recusa_painel_minusculo_e_id_com_quebra(tmp_path):
    with pytest.raises(Recusada):
        ler_area({"x": 0, "y": 0, "w": 1e-9, "h": 0.5})
    _sessao(tmp_path, "local_fff", sessionId="local_fff\n", cliSessionId=CLI, isArchived=False)
    assert sessao_do_app(CLI, tmp_path) == "last"
