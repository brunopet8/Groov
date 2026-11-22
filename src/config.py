"""Preferências não secretas de quem instala (nome, cidade, vault...).

Ordem: variável de ambiente > privado/.env > padrão neutro. Lê o arquivo a cada
chamada (sem cache) e sem dotenv, porque o .venv do roteador não o tem.
"""
import os
from pathlib import Path

ENV = Path(__file__).resolve().parents[1] / "privado" / ".env"

CHAVES = (
    "GROOV_NOME_USUARIO",
    "GROOV_CIDADE",
    "GROOV_LAT",
    "GROOV_LON",
    "GROOV_MAR",
    "GROOV_PERFIL_NETFLIX",
    "GROOV_VAULT",
    "GROOV_FRASES_EXTRA",
    "GROOV_HOTWORDS_EXTRA",
    "GROOV_WORKSPACES_EXTRA",
    "TRELLO_QUADROS_CONTAGEM",
)


def _do_arquivo(nome: str) -> str | None:
    try:
        linhas = ENV.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return None
    for linha in linhas:
        chave, igual, resto = linha.strip().partition("=")
        if igual and not chave.startswith("#") and chave.strip() == nome:
            resto = resto.strip()
            if len(resto) >= 2 and resto[0] == resto[-1] and resto[0] in "\"'":
                resto = resto[1:-1]
            return resto
    return None


def valor(nome: str, padrao: str = "") -> str:
    if nome in os.environ:
        return os.environ[nome]
    achado = _do_arquivo(nome)
    return padrao if achado is None else achado


def lista(nome: str) -> list[str]:
    return [item.strip() for item in valor(nome).split(",") if item.strip()]


def apresentar_usuario() -> str:
    nome = valor("GROOV_NOME_USUARIO").strip()
    return f"O usuário se chama {nome}." if nome else ""
