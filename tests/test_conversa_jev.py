import asyncio

import pytest

from src.conversa import jev

WS = ["Groov-vault", "projeto"]


def _resposta(trabalho: float, ws: str = "projeto") -> dict:
    return {"model": "jev-x", "answers": {
        "nivel": {"type": "choice", "choice": "trabalho" if trabalho >= 0.5 else "conversa", "confidence": 0.9,
                  "probabilities": {"conversa": 1 - trabalho, "trabalho": trabalho}},
        "workspace": {"type": "choice", "choice": ws, "confidence": 0.8, "probabilities": {ws: 0.8}}}}


def test_corpo_tem_as_duas_perguntas():
    corpo = jev.montar_corpo("faz um relatório", WS)
    assert corpo["model"] == jev.MODELO and corpo["state"] == "faz um relatório"
    assert set(corpo["questions"]["nivel"]["criteria"]) == {"conversa", "trabalho"}
    assert corpo["questions"]["nivel"]["type"] == "choice"
    assert corpo["questions"]["workspace"]["criteria"] == {"Groov-vault": None, "projeto": None}


def test_triar_trabalho():
    async def enviar(corpo, chave):
        assert chave == "k"
        return _resposta(0.9)
    assert asyncio.run(jev.triar("x", WS, "k", enviar)) == jev.Triagem(3, "projeto", 0.9)


def test_triar_abaixo_do_limiar():
    async def enviar(corpo, chave):
        return _resposta(0.6)
    t = asyncio.run(jev.triar("x", WS, "k", enviar))
    assert t.nivel == 2 and t.prob == pytest.approx(0.6)


async def _levanta(corpo, chave):
    raise OSError("rede")


async def _vazio(corpo, chave):
    return {}


async def _sem_prob(corpo, chave):
    return {"answers": {"nivel": {}}}


async def _demora(corpo, chave):
    await asyncio.sleep(2)
    return _resposta(0.9)


@pytest.mark.parametrize("enviar", [_levanta, _vazio, _sem_prob, _demora])
def test_triar_falha_vira_none(enviar):
    assert asyncio.run(jev.triar("x", WS, "k", enviar)) is None


# --- escolher: escolha genérica entre opções (visão e clique simples) ---

def _escolha(choice: str, probs: dict) -> dict:
    return {"answers": {"alvo": {"type": "choice", "choice": choice, "probabilities": probs}}}


def test_escolher_devolve_indice():
    vistos = []

    async def enviar(corpo, chave):
        vistos.append(corpo)
        return _escolha("1: Pular anúncio", {"0: Início": 0.05, "1: Pular anúncio": 0.9, "nenhum": 0.05})
    assert asyncio.run(jev.escolher("pular o anúncio", "Qual?", ["Início", "Pular anúncio"], "k", enviar)) == (1, 0.9)
    q = vistos[0]["questions"]["alvo"]
    assert vistos[0]["model"] == jev.MODELO and vistos[0]["state"] == "pular o anúncio"
    assert set(q["criteria"]) == {"0: Início", "1: Pular anúncio", "nenhum"} and q["type"] == "choice"


def test_escolher_nenhum():
    async def enviar(corpo, chave):
        return _escolha("nenhum", {"0: a": 0.1, "nenhum": 0.9})
    assert asyncio.run(jev.escolher("x", "Qual?", ["a"], "k", enviar)) is None


@pytest.mark.parametrize("enviar", [_levanta, _vazio, _sem_prob, _demora])
def test_escolher_erro_e_none(enviar):
    assert asyncio.run(jev.escolher("x", "Qual?", ["a", "b"], "k", enviar)) is None


def test_escolher_sem_chave_ou_sem_opcoes_nem_chama():
    async def enviar(corpo, chave):
        raise AssertionError("não devia chamar")
    assert asyncio.run(jev.escolher("x", "Qual?", ["a"], "", enviar)) is None
    assert asyncio.run(jev.escolher("x", "Qual?", [], "k", enviar)) is None


def test_escolher_corta_em_40():
    vistos = []

    async def enviar(corpo, chave):
        vistos.append(corpo)
        return _escolha("nenhum", {"nenhum": 1.0})
    asyncio.run(jev.escolher("x", "Qual?", [f"op{i}" for i in range(60)], "k", enviar))
    assert len(vistos[0]["questions"]["alvo"]["criteria"]) == jev.OPCOES_MAX + 1


def test_escolher_corta_opcao_longa():
    async def enviar(corpo, chave):
        return _escolha("0: " + "a" * 60, {"0: " + "a" * 60: 0.95})
    assert asyncio.run(jev.escolher("x", "Qual?", ["a" * 200], "k", enviar)) == (0, 0.95)
