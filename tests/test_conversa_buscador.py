import asyncio
from types import SimpleNamespace

import pytest

pytest.importorskip("google.genai")

from src.conversa import buscador as b
from src.conversa.ajudante import CANCELADA, ESTOUROU, VAZIO


class Modelos:
    def __init__(self, fazer):
        self.fazer, self.chamadas = fazer, []

    async def generate_content(self, **kw):
        self.chamadas.append(kw)
        return await self.fazer()


def buscador(fazer, teto=5.0):
    modelos = Modelos(fazer)
    return b.Buscador(cliente=SimpleNamespace(aio=SimpleNamespace(models=modelos)), teto=teto), modelos


async def _resposta(texto):
    return SimpleNamespace(text=texto)


def test_resposta_normal_liga_busca_do_google():
    asyncio.run(_test_resposta_normal_liga_busca_do_google())


async def _test_resposta_normal_liga_busca_do_google():
    bus, modelos = buscador(lambda: _resposta("  Faz 25 graus.  "))
    assert await bus.executar("tempo?") == "Faz 25 graus."
    kw = modelos.chamadas[0]
    assert kw["contents"] == "tempo?" and kw["model"] == b.MODELO_BUSCA
    assert kw["config"].tools[0].google_search is not None


def test_resposta_vazia():
    asyncio.run(_test_resposta_vazia())


async def _test_resposta_vazia():
    bus, _ = buscador(lambda: _resposta(None))
    assert await bus.executar("x") == VAZIO


def test_erro_vira_frase_de_falha():
    asyncio.run(_test_erro_vira_frase_de_falha())


async def _test_erro_vira_frase_de_falha():
    async def erro():
        raise RuntimeError("429")
    bus, _ = buscador(erro)
    assert await bus.executar("x") == b.FALHOU


def test_teto_estoura():
    asyncio.run(_test_teto_estoura())


async def _test_teto_estoura():
    async def lento():
        await asyncio.sleep(10)
    bus, _ = buscador(lento, teto=0.05)
    assert await bus.executar("x") == ESTOUROU


def test_cancelar_corta_a_chamada():
    asyncio.run(_test_cancelar_corta_a_chamada())


async def _test_cancelar_corta_a_chamada():
    async def lento():
        await asyncio.sleep(10)
    bus, _ = buscador(lento)
    t = asyncio.ensure_future(bus.executar("x"))
    await asyncio.sleep(0.05)
    bus.cancelar()
    assert await asyncio.wait_for(t, 1) == CANCELADA
    assert bus.cancelado


def test_text_que_levanta_vira_frase_de_falha():
    asyncio.run(_test_text_que_levanta_vira_frase_de_falha())


async def _test_text_que_levanta_vira_frase_de_falha():
    class Quebrada:
        @property
        def text(self):
            raise ValueError("resposta bloqueada")

    async def quebrada():
        return Quebrada()
    bus, _ = buscador(quebrada)
    assert await bus.executar("x") == b.FALHOU
