import asyncio
from types import SimpleNamespace

import pytest

from src.conversa.mensagens import Recusada, criar_despacho, ler_ligada, ler_resposta, ler_texto


def rodar(despachar, msg):
    asyncio.run(despachar(msg))


def montar(acoes):
    saidas = []

    async def responder(msg, d):
        saidas.append(("ok", d))

    async def recusar(msg, motivo):
        saidas.append(("erro", motivo))
    return criar_despacho(acoes, responder, recusar), saidas


def test_tipo_desconhecido_recusa_sem_chamar_acao():
    chamadas = []

    async def acao(d):
        chamadas.append(d)
    despachar, saidas = montar({"a": acao})
    rodar(despachar, SimpleNamespace(type="b", data={}))
    assert saidas == [("erro", "tipo desconhecido")] and chamadas == []


def test_recusada_leva_o_motivo():
    async def acao(d):
        raise Recusada("x")
    despachar, saidas = montar({"a": acao})
    rodar(despachar, SimpleNamespace(type="a", data=None))
    assert saidas == [("erro", "x")]


def test_excecao_qualquer_vira_falhou_e_o_log_nao_traz_o_conteudo(caplog):
    async def acao(d):
        raise ValueError("segredo")
    despachar, saidas = montar({"a": acao})
    with caplog.at_level("DEBUG", logger="groov.mensagens"):
        rodar(despachar, SimpleNamespace(type="a", data={"texto": "conteudo-privado"}))
    assert saidas == [("erro", "falhou")]
    log = caplog.text
    assert "segredo" not in log and "conteudo-privado" not in log and "ValueError" in log


def test_sucesso_responde_ok():
    async def acao(d):
        pass
    despachar, saidas = montar({"a": acao})
    rodar(despachar, SimpleNamespace(type="a", data=None))
    assert saidas == [("ok", {"ok": True})]


def test_ler_texto():
    assert ler_texto({"texto": "  oi "}) == "oi"
    for ruim in (None, "oi", {}, {"texto": 3}, {"texto": "   "}, {"texto": "a" * 2001}):
        with pytest.raises(Recusada):
            ler_texto(ruim)


def test_ler_resposta():
    assert ler_resposta({"id": "p1", "opcao": "sim"}) == ("p1", "sim")
    for ruim in (None, {"id": "", "opcao": "sim"}, {"id": "p1", "opcao": "a" * 81}, {"id": 1, "opcao": "x"}):
        with pytest.raises(Recusada):
            ler_resposta(ruim)


@pytest.mark.parametrize("quebra", ["responder", "recusar"])
def test_falha_ao_responder_nao_escapa_e_o_log_so_traz_o_tipo(caplog, quebra):
    async def acao(d):
        if quebra == "recusar":
            raise Recusada("x")

    async def estoura(msg, _):
        raise ConnectionError("canal-fechado-texto")

    async def ok(msg, _):
        pass
    despachar = criar_despacho({"a": acao}, estoura if quebra == "responder" else ok,
                               estoura if quebra == "recusar" else ok)
    with caplog.at_level("DEBUG", logger="groov.mensagens"):
        rodar(despachar, SimpleNamespace(type="a", data={"texto": "conteudo-privado"}))
    assert "ConnectionError" in caplog.text
    assert "canal-fechado-texto" not in caplog.text and "conteudo-privado" not in caplog.text


def test_ler_ligada():
    assert ler_ligada({"ligada": False}) is False
    for ruim in (None, {}, {"ligada": 1}, {"ligada": "sim"}):
        with pytest.raises(Recusada):
            ler_ligada(ruim)
