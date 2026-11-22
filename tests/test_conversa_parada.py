import asyncio

import pytest

from src.conversa.ajudante import ESTOUROU
from src.conversa.parada import parar
from src.conversa.sessao import Sessao


class FakeLaco:
    def __init__(self):
        self.cancelado = False

    def cancelar(self):
        self.cancelado = True

    def fala_do_teto(self):
        return "Parei pelo limite, senhor. Fiz 3 passos e não terminei."


class FakeAjudante(FakeLaco):
    pass


def rodar(motivo, dono):
    s, ajudante, laco, falas = Sessao(), FakeAjudante(), FakeLaco(), []

    async def falar(texto):
        falas.append(texto)

    s.iniciar_tarefa(0, dono=dono)
    asyncio.run(parar(motivo, s, ajudante, laco, falar))
    return s, ajudante, laco, falas


def test_tchau_cancela_laco_e_solta_a_vaga():
    s, ajudante, laco, falas = rodar("tchau", "laco")
    assert laco.cancelado and s.dono is None and not falas


def test_tchau_nao_cancela_hermes():
    s, ajudante, laco, falas = rodar("tchau", "hermes")
    assert not ajudante.cancelado and not laco.cancelado and s.dono == "hermes" and not falas


@pytest.mark.parametrize("motivo", ["desligar", "teto", "conexao"])
@pytest.mark.parametrize("dono", ["laco", "hermes"])
def test_parar_cancela_os_dois(motivo, dono):
    s, ajudante, laco, _ = rodar(motivo, dono)
    assert ajudante.cancelado and laco.cancelado and s.dono is None


def test_teto_do_laco_fala_o_resumo_do_laco_e_nao_estourou():
    s, _, laco, falas = rodar("teto", "laco")
    assert falas == [laco.fala_do_teto()] and ESTOUROU not in falas


def test_teto_do_hermes_fala_estourou():
    assert rodar("teto", "hermes")[3] == [ESTOUROU]


@pytest.mark.parametrize("motivo", ["desligar", "conexao"])
def test_so_o_teto_fala(motivo):
    assert rodar(motivo, "hermes")[3] == []


def test_sem_laco_ainda():  # antes da ligação do laço (Task 11) o bot passa None
    s, falas = Sessao(), []
    s.iniciar_tarefa(0)
    asyncio.run(parar("desligar", s, FakeAjudante(), None, None))
    assert s.dono is None


def test_motivo_desconhecido_falha():
    with pytest.raises(ValueError):
        asyncio.run(parar("outro", Sessao(), FakeAjudante(), None, None))
