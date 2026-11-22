import asyncio
import subprocess
import sys
from pathlib import Path

import pytest

from src.conversa import ajudante
from src.conversa.ajudante import Ajudante, montar_comando, resumir


def falso(codigo):
    return lambda pedido: [sys.executable, "-c", codigo]


def test_montar_comando_so_busca():
    cmd = montar_comando("clima em Tóquio")
    assert Path(cmd[0]).stem.lower() == "hermes" and cmd[1] == "-z" and cmd[-2:] == ["-t", "search"]
    assert "clima em Tóquio" in cmd[2]


def test_resumir_vazio_e_longo():
    assert resumir("   ") == "Não encontrei nada, senhor."
    longo = "Frase um. " * 80
    r = resumir(longo)
    assert len(r) <= 400 and r.endswith(".")


def test_executar_devolve_saida():
    a = Ajudante(comando=falso("print('Camberra é a capital.')"))
    assert asyncio.run(a.executar("x")) == "Camberra é a capital."


def test_executar_estoura_teto():
    a = Ajudante(comando=falso("import time; time.sleep(30)"), teto=0.5)
    assert asyncio.run(a.executar("x")) == "A tarefa demorou demais, senhor. Cancelei."


def test_executar_falha():
    a = Ajudante(comando=falso("import sys; sys.exit(2)"))
    assert asyncio.run(a.executar("x")) == "O Hermes falhou nessa tarefa, senhor."


def test_cancelar_mata_processo():
    async def cenario():
        a = Ajudante(comando=falso("import time; time.sleep(30)"))
        t = asyncio.create_task(a.executar("x"))
        await asyncio.sleep(0.5)
        a.cancelar()
        return a, await asyncio.wait_for(t, 5)  # volta logo, sem esperar 30 s

    a, resultado = asyncio.run(cenario())
    assert resultado and a.cancelado


def test_executar_nova_tarefa_limpa_o_cancelamento():
    a = Ajudante(comando=falso("print('ok')"))
    a.cancelado = True
    assert asyncio.run(a.executar("x")) == "ok" and not a.cancelado


@pytest.mark.skipif(sys.platform != "win32", reason="janela de console só existe no Windows")
def test_hermes_roda_sem_janela(monkeypatch):
    visto = {}
    real = asyncio.create_subprocess_exec

    async def espiao(*args, **kwargs):
        visto.update(kwargs)
        return await real(*args, **kwargs)

    monkeypatch.setattr(ajudante.asyncio, "create_subprocess_exec", espiao)
    assert asyncio.run(Ajudante(comando=falso("print('ok')")).executar("x")) == "ok"
    assert visto["creationflags"] == subprocess.CREATE_NO_WINDOW


@pytest.mark.skipif(sys.platform != "win32", reason="taskkill e janela de console só existem no Windows")
def test_cancelar_mata_a_arvore_sem_janela(monkeypatch):
    chamadas = []
    monkeypatch.setattr(ajudante.subprocess, "run", lambda cmd, **kw: chamadas.append((cmd, kw)))

    class Proc:
        returncode, pid = None, 4242
        def kill(self): pass

    ajudante._matar(Proc())
    cmd, kw = chamadas[0]
    assert cmd == ["taskkill", "/PID", "4242", "/T", "/F"]
    assert kw["creationflags"] == subprocess.CREATE_NO_WINDOW


def test_hermes_nao_herda_nenhum_segredo(monkeypatch):
    monkeypatch.setenv("TRELLO_TOKEN", "segredo-do-teste")
    a = Ajudante(comando=falso("import os; print(os.environ.get('TRELLO_TOKEN', 'ausente'))"),
                 segredos=frozenset({"TRELLO_TOKEN"}))
    assert asyncio.run(a.executar("x")) == "ausente"


def test_hermes_nao_herda_a_chave_da_groq(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "segredo-do-teste")
    a = Ajudante(comando=falso("import os; print(os.environ.get('GROQ_API_KEY', 'ausente'))"))
    assert asyncio.run(a.executar("x")) == "ausente"
