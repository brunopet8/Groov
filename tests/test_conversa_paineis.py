import json

from src.conversa import paineis as P


def test_para_janela_corta_e_omite_chaves_vazias():
    p = P.Painel("x", "lista", "t" * 100, itens=tuple("i" * 200 for _ in range(10)), corpo="c" * 700,
                 meta="m" * 50, fim=1234.5)
    d = P.para_janela(p)
    assert len(d["titulo"]) == 80 and len(d["meta"]) == 40 and len(d["corpo"]) == 600
    assert len(d["itens"]) == 8 and all(len(i) == 120 for i in d["itens"])
    assert d["fim"] == 1234.5 and d["id"] == "x" and d["tipo"] == "lista"
    assert P.para_janela(P.Painel("y", "texto", "T")) == {"id": "y", "tipo": "texto", "titulo": "T"}


def test_para_janela_valor_e_unidade_sao_texto_e_fim_nunca_nan():
    d = P.para_janela(P.Painel("n", "numero", "T", valor="0" * 20, unidade="°C" * 9, fim=float("nan")))
    assert len(d["valor"]) == 12 and len(d["unidade"]) == 8 and "fim" not in d
    assert "fim" not in P.para_janela(P.Painel("n", "numero", "T", fim=float("inf")))
    json.dumps(d, allow_nan=False)


def test_clima_com_numero_vira_numero():
    p = P.de_clima("Recife agora: 24°C, céu limpo.")
    assert (p.id, p.tipo, p.valor, p.unidade) == ("clima", "numero", "24", "°C")
    assert "céu limpo" in p.corpo
    assert P.de_clima("Recife agora: -3°C.").valor == "-3"
    assert P.de_clima("Rio agora: 24,5°C.").valor == "24,5"
    assert P.de_clima("Rio agora: -3,5°C.").valor == "-3,5"


def test_clima_sem_numero_vira_texto():
    p = P.de_clima("Sem dados agora.")
    assert (p.id, p.tipo, p.valor) == ("clima", "texto", "") and p.corpo == "Sem dados agora."


def test_pesquisa_briefing_vida_timer():
    p = P.de_pesquisa("capital da Austrália", "Camberra.")
    assert (p.id, p.tipo, p.titulo, p.corpo) == ("pesquisa", "texto", "capital da Austrália", "Camberra.")
    b = P.de_briefing("hoje", ["a", "b"])
    assert (b.id, b.tipo, b.titulo, b.itens) == ("hoje", "lista", "HOJE", ("a", "b"))
    v = P.de_vida("agenda", "texto")
    assert (v.id, v.tipo, v.titulo, v.corpo) == ("vida", "texto", "agenda", "texto")
    assert (P.de_timer(False, 5.0).id, P.de_timer(True, 5.0).id) == ("timer", "timer-desligar")
    assert P.de_timer(False, 5.0).tipo == "numero" and P.de_timer(False, 5.0).fim == 5.0


def test_descrever_passo_so_acao_e_alvo_publico():
    base = {"url": None, "app": None, "id": None, "texto": None, "direcao": None}
    assert P.descrever_passo({**base, "acao": "abrir_site", "url": "https://www.netflix.com/watch/8?x=1"}) == "abrir site netflix.com"
    assert P.descrever_passo({**base, "acao": "abrir_site", "url": "g1.globo.com/politica?q=segredo"}) == "abrir site g1.globo.com"
    assert P.descrever_passo({**base, "acao": "abrir_app", "app": "spotify"}) == "abrir app spotify"
    assert P.descrever_passo({**base, "acao": "rolar", "direcao": "baixo"}) == "rolar baixo"
    assert P.descrever_passo({**base, "acao": "clicar", "id": 5}) == "clicar"
    for acao in ("digitar", "buscar", "perguntar", "responder"):
        d = P.descrever_passo({**base, "acao": acao, "id": 7, "texto": "minha senha 123 e meu pix"})
        assert d == acao and "senha" not in d and "123" not in d


def test_descrever_passo_nunca_levanta_com_url_malformada():
    for url in ("//[x", "", None, "http://[::1"):
        assert P.descrever_passo({"acao": "abrir_site", "url": url}) == "abrir site"


def test_de_passos_ultimos_seis_e_desfecho():
    p = P.de_passos("abre o g1", [f"p{i}" for i in range(9)])
    assert (p.id, p.tipo, p.titulo, p.itens) == ("pc", "passos", "abre o g1", tuple(f"p{i}" for i in range(3, 9)))
    assert p.meta == "" and p.corpo == ""
    f = P.de_passos("abre o g1", ["abrir site g1.globo.com"], ("respondeu", "Pronto, senhor."))
    assert f.meta == "respondeu" and f.corpo == "Pronto, senhor."
