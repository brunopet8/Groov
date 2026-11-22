import os

import pytest

pytest.importorskip("dotenv")

from src.conversa.segredos import ler_segredos


def test_ler_segredos_nao_mexe_no_ambiente(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("GROQ_API_KEY=a\nTRELLO_TOKEN=b\nVAZIO=\n", encoding="utf-8")
    monkeypatch.delenv("TRELLO_TOKEN", raising=False)
    assert ler_segredos(env) == {"GROQ_API_KEY": "a", "TRELLO_TOKEN": "b"}
    assert "TRELLO_TOKEN" not in os.environ


def test_ler_segredos_sem_arquivo_devolve_vazio(tmp_path):
    assert ler_segredos(tmp_path / "nao-existe.env") == {}


def test_filhos_nao_herdam_chave_nova(monkeypatch):
    """O Claude do plano, o Hermes e a sonda do PC não herdam a chave do Gemini (nem a da Groq, enquanto existir)."""
    import asyncio

    from src.conversa import cerebro_pc
    from src.conversa.ajudante import Ajudante
    from src.conversa.pc import Sonda

    for nome in ("GOOGLE_API_KEY", "GROQ_API_KEY"):
        monkeypatch.setenv(nome, "nao-vazar")
        assert nome in Ajudante().segredos and nome in Sonda().segredos
    visto = {}

    async def abrir(*cmd, **kw):
        visto.update(env=kw["env"])
        raise OSError("só quero o ambiente")

    monkeypatch.setattr(cerebro_pc.asyncio, "create_subprocess_exec", abrir)
    asyncio.run(cerebro_pc.PensadorClaude(achar=lambda: "C:/x/claude.exe")([{"role": "user", "content": "x"}]))
    assert "GOOGLE_API_KEY" not in visto["env"] and "GROQ_API_KEY" not in visto["env"]
