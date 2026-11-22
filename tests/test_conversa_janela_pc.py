import asyncio

from src.conversa import janela_pc as j
from src.conversa.pc import PROCESSOS_PROIBIDOS, ErroSonda, Falso, InfoJanela, Sonda

PERMITIDOS = PROCESSOS_PROIBIDOS  # o nome ficou: é o terceiro argumento de agir_na_janela (agora os proibidos)


def rodar(c):
    return asyncio.run(c)


def backend(plano=1, infos=None, janelas=(1,)):
    f = Falso(janelas=[frozenset(janelas)], plano=plano)
    f.infos = infos or {}
    return f


def acoes(f):
    return [c for c in f.chamadas if c[0] in ("fechar", "minimizar", "fechar_aba")]


def test_fecha_o_chrome_de_uma_aba_na_hora():
    f = backend(infos={1: InfoJanela("chrome", 1, False)})
    assert rodar(j.agir_na_janela(f, PERMITIDOS, "fechar", "chrome")) == ([j.FRASE_FEITO], None)
    assert acoes(f) == [("fechar", 1)]


def test_chrome_com_abas_pergunta_e_so_fecha_no_sim():
    f = backend(infos={1: InfoJanela("chrome", 4, False)})
    falas, pedido = rodar(j.agir_na_janela(f, PERMITIDOS, "fechar", "chrome"))
    assert falas == [j.frase_abas(4)] and pedido == j.PedidoJanela(1) and acoes(f) == []
    assert rodar(j.agir_na_janela(f, PERMITIDOS, "fechar", hwnd=pedido.hwnd, confirmado=True)) == ([j.FRASE_FEITO], None)
    assert acoes(f) == [("fechar", 1)]


def test_sim_rele_a_janela_e_o_groov_continua_proibido():
    f = backend(infos={1: InfoJanela("chrome", 4, True)})  # a janela virou a do GROOV entre a pergunta e o sim
    assert rodar(j.agir_na_janela(f, PERMITIDOS, "fechar", hwnd=1, confirmado=True)) == ([j.FRASE_JANELA_PROIBIDA], None)
    assert acoes(f) == []


def test_app_fora_da_antiga_lista_e_tocado_e_processo_proibido_nao():
    f = backend(infos={1: InfoJanela("notepad", 0, False)})
    assert rodar(j.agir_na_janela(f, PERMITIDOS, "fechar")) == ([j.FRASE_FEITO], None) and acoes(f) == [("fechar", 1)]
    f = backend(infos={1: InfoJanela("consent", 0, False)})  # o aviso de UAC
    assert rodar(j.agir_na_janela(f, PERMITIDOS, "fechar")) == ([j.FRASE_JANELA_PROIBIDA], None) and acoes(f) == []


def test_alvo_por_apelido_acha_o_processo():
    f = backend(plano=9, infos={9: InfoJanela("chrome", 1, True), 2: InfoJanela("notepad", 0, False)}, janelas=(2,))
    assert rodar(j.agir_na_janela(f, PERMITIDOS, "fechar", "bloco de notas")) == ([j.FRASE_FEITO], None)
    assert acoes(f) == [("fechar", 2)]


def test_janela_da_frente_do_groov_ou_proibida_nao_e_tocada():
    for info in (InfoJanela("chrome", 1, True), InfoJanela("logonui", 0, False), None):
        f = backend(infos={1: info} if info else {})
        falas, _ = rodar(j.agir_na_janela(f, PERMITIDOS, "minimizar"))
        assert falas in ([j.FRASE_JANELA_PROIBIDA], [j.FRASE_JANELA_NAO_ACHEI]) and acoes(f) == []


def test_aba_vai_para_o_chrome_mesmo_com_outro_app_na_frente():
    f = backend(plano=2, infos={1: InfoJanela("chrome", 3, False), 2: InfoJanela("Spotify", 0, False)}, janelas=(1, 2))
    assert rodar(j.agir_na_janela(f, PERMITIDOS, "fechar_aba")) == ([j.FRASE_FEITO], None)
    assert acoes(f) == [("fechar_aba", 1)]


def test_dois_chromes_e_nenhum_na_frente_nao_adivinha():
    f = backend(plano=9, infos={1: InfoJanela("chrome", 1, False), 2: InfoJanela("chrome", 1, False)}, janelas=(1, 2))
    assert rodar(j.agir_na_janela(f, PERMITIDOS, "fechar", "chrome")) == ([j.FRASE_JANELA_QUAL], None)
    assert acoes(f) == []


def test_backend_que_falha_diz_que_nao_conseguiu():
    f = backend(infos={1: InfoJanela("Spotify", 0, False)})
    f.agir = False
    assert rodar(j.agir_na_janela(f, PERMITIDOS, "minimizar")) == ([j.FRASE_JANELA_FALHOU], None)


def test_groov_na_frente_e_chrome_atras_age_no_chrome_sem_alvo():
    f = backend(plano=9, infos={9: InfoJanela("chrome", 1, True), 1: InfoJanela("chrome", 3, False)}, janelas=(1,))
    for acao in ("minimizar", "fechar_aba"):
        f.chamadas.clear()
        assert rodar(j.agir_na_janela(f, PERMITIDOS, acao)) == ([j.FRASE_FEITO], None)
        assert acoes(f) == [(acao, 1)]


def test_groov_na_frente_e_dois_apps_atras_pergunta_qual():
    f = backend(plano=9, infos={9: InfoJanela("chrome", 1, True), 1: InfoJanela("chrome", 1, False),
                                2: InfoJanela("Spotify", 0, False)}, janelas=(1, 2))
    assert rodar(j.agir_na_janela(f, PERMITIDOS, "minimizar")) == ([j.FRASE_JANELA_QUAL], None)
    assert acoes(f) == []


def test_groov_na_frente_processo_proibido_atras_nao_conta_como_candidata():
    f = backend(plano=9, infos={9: InfoJanela("chrome", 1, True), 1: InfoJanela("chrome", 1, False),
                                2: InfoJanela("consent", 0, False)}, janelas=(1, 2))
    assert rodar(j.agir_na_janela(f, PERMITIDOS, "minimizar")) == ([j.FRASE_FEITO], None)
    assert acoes(f) == [("minimizar", 1)]


def test_sonda_info_janela_converte_e_falha_vira_none():
    s = Sonda(titulo_groov="GROOV")

    async def _chamar(op, **dados):
        assert (op, dados) == ("janela_info", {"hwnd": 5})
        return {"processo": "chrome", "abas": 3, "groov": False}
    s._chamar = _chamar
    assert rodar(s.info_janela(5)) == InfoJanela("chrome", 3, False)

    async def quebra(op, **dados):
        raise ErroSonda("x")
    s._chamar = quebra
    assert rodar(s.info_janela(5)) is None
