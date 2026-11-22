import dataclasses

from src.conversa import gravacao
from src.conversa import laco as L
from src.conversa.gravacao import Gravacoes
from src.conversa.pc import Falso, Midia
from src.conversa.regras_pc import Elemento
from tests.test_conversa_laco import (ABRIR_NETFLIX, CARTAO, JANELAS, NETFLIX, PLAYER, P, Roteiro, acoes, fazer, leitura,
                                      rodar)

TOCANDO = [(), (Midia("Chrome", True, "Sora no Kanata", ""),)]


def cena(cartao=CARTAO):
    """Netflix com o cartão no browse e o player depois do clique; `cartao` troca o elemento da tela."""
    pagina = leitura("www.netflix.com/browse", elementos=[cartao], titulo="Netflix")
    return Falso(leituras=[pagina, PLAYER], janelas=list(JANELAS), midias=list(TOCANDO))


def gravar_uma_vez(tmp_path):
    g = Gravacoes(tmp_path / "g.json")
    pensar = Roteiro(ABRIR_NETFLIX, P("clicar", id=5))
    laco, _ = fazer(cena(), pensar, NETFLIX, gravacoes=g)
    assert rodar(laco, NETFLIX).tipo == "tocou" and len(pensar.chamadas) == 2
    return g


def test_segunda_vez_sem_modelo(tmp_path):
    g = gravar_uma_vez(tmp_path)
    cartao_novo_id = dataclasses.replace(CARTAO, id=41, runtime_id="outro")  # outra sonda: mesmos campos, outro id
    fb = cena(cartao_novo_id)
    pensar = Roteiro()
    laco, ctx = fazer(fb, pensar, NETFLIX, gravacoes=g)
    d = rodar(laco, NETFLIX)
    assert d.tipo == "tocou" and pensar.chamadas == [] and ctx.dormiu == 1
    assert [c[2].id for c in fb.chamadas if c[0] == "clicar"] == [41]


def test_tela_diferente_volta_ao_laco(tmp_path):
    g = gravar_uma_vez(tmp_path)
    outro = Elemento(5, "Naruto", "Hyperlink", ancestrais=("Continuar assistindo",))
    pagina = leitura("www.netflix.com/browse", elementos=[outro, Elemento(6, "Sora no Kanata", "Hyperlink",
                                                                      ancestrais=("Em alta",))])
    fb = cena()
    fb.leituras = [pagina, PLAYER]
    pensar = Roteiro(P("clicar", id=6))
    laco, _ = fazer(fb, pensar, NETFLIX, gravacoes=g)
    assert rodar(laco, NETFLIX).tipo == "tocou"
    assert len(pensar.chamadas) == 1  # a abertura veio da gravação; o clique, do modelo
    assert g.buscar(laco._chave)[-1]["elemento"]["ancestrais"] == ["Em alta"]  # regravou com o que deu certo


def test_repeticao_passa_pelas_regras(tmp_path):
    g = Gravacoes(tmp_path / "g.json")
    g.guardar(gravacao.chave(L._norm(NETFLIX), None), [
        {"acao": "abrir_site", "url": "https://www.netflix.com/"},
        {"acao": "clicar", "elemento": gravacao.ficha(Elemento(0, "Pagar agora", "Button"))}])
    pagar = Elemento(9, "Pagar agora", "Button")
    fb = Falso(leituras=[leitura("www.netflix.com/browse", elementos=[pagar])], janelas=list(JANELAS))
    laco, ctx = fazer(fb, Roteiro(P("desistir")), NETFLIX, gravacoes=g)
    d = rodar(laco, NETFLIX)
    assert "clicar" not in acoes(fb) and d.tipo == "parou"  # classificar_clique manda parar: nada de clique sem volta
    assert g.buscar(gravacao.chave(L._norm(NETFLIX), None)) is None  # a gravação que não terminou bem sai


def test_desligada_nao_grava_nem_repete(tmp_path, monkeypatch):
    monkeypatch.setattr(gravacao, "GRAVACAO_LIGADA", False)
    g = Gravacoes(tmp_path / "g.json")
    laco, _ = fazer(cena(), Roteiro(ABRIR_NETFLIX, P("clicar", id=5)), NETFLIX, gravacoes=g)
    assert rodar(laco, NETFLIX).tipo == "tocou" and not (tmp_path / "g.json").exists()


def test_arquivo_de_formato_errado_roda_com_o_modelo(tmp_path):
    caminho = tmp_path / "g.json"
    g = Gravacoes(caminho)
    k = gravacao.chave(L._norm(NETFLIX), None)
    for lixo in ({k: [1]}, {k: [{"acao": "clicar", "elemento": "x"}]}, {k: "texto"}, [1, 2]):
        caminho.write_text(__import__("json").dumps(lixo), encoding="utf-8")
        pensar = Roteiro(ABRIR_NETFLIX, P("clicar", id=5))
        laco, _ = fazer(cena(), pensar, NETFLIX, gravacoes=g)
        assert rodar(laco, NETFLIX).tipo == "tocou" and len(pensar.chamadas) == 2


def test_gravacao_boa_nao_some_se_a_repeticao_nem_foi_usada(tmp_path):
    g = Gravacoes(tmp_path / "g.json")
    k = gravacao.chave(L._norm(NETFLIX), None)
    g.guardar(k, [{"acao": "clicar", "elemento": gravacao.ficha(CARTAO)}])  # 1º passo exige janela: sem janela, abandona
    laco, _ = fazer(Falso(leituras=[leitura()], janelas=list(JANELAS)), Roteiro(P("desistir")), NETFLIX, gravacoes=g)
    assert rodar(laco, NETFLIX).tipo == "desistiu" and g.buscar(k) is not None


def test_passo_repetido_que_nao_muda_a_tela_passa_a_vez_ao_modelo(tmp_path):
    g = Gravacoes(tmp_path / "g.json")
    k = gravacao.chave(L._norm(NETFLIX), None)
    ficha = gravacao.ficha(CARTAO)
    g.guardar(k, [{"acao": "abrir_site", "url": "https://www.netflix.com/"}, {"acao": "clicar", "elemento": ficha},
                  {"acao": "clicar", "elemento": ficha}])
    fb = Falso(leituras=[leitura("www.netflix.com/browse", elementos=[CARTAO])], janelas=list(JANELAS))
    pensar = Roteiro(P("responder", texto="Feito."))
    laco, _ = fazer(fb, pensar, NETFLIX, gravacoes=g)
    assert rodar(laco, NETFLIX).tipo == "respondeu" and len(pensar.chamadas) == 1


def test_passo_gravado_zera_o_tempo_do_cerebro(tmp_path):
    import asyncio
    g = Gravacoes(tmp_path / "g.json")
    laco, _ = fazer(Falso(), Roteiro(), NETFLIX, gravacoes=g)
    laco._t_chamada, laco._repeticao = 3.0, [{"acao": "abrir_site", "url": "https://www.netflix.com/"}]
    passo, quem = asyncio.run(laco._proximo_passo())
    assert quem == "gravacao" and laco._t_chamada == 0.0
