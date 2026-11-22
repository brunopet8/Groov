import os
from pathlib import Path

import pytest

from src import config

# antes de qualquer módulo de teste ser importado: nem o que roda no import (ex.: vault.raiz() no bot) lê o .env real
config.ENV = Path(__file__).with_name("sem.env")
for _nome in config.CHAVES:
    os.environ.pop(_nome, None)


@pytest.fixture(autouse=True)
def _config_neutra(tmp_path, monkeypatch):
    """Nenhum teste lê o privado/.env real nem herda GROOV_* do ambiente."""
    monkeypatch.setattr(config, "ENV", tmp_path / "sem.env")
    for nome in config.CHAVES:
        monkeypatch.delenv(nome, raising=False)
    monkeypatch.setenv("GROOV_VAULT", str(tmp_path / "vault"))  # o bot prepara o vault: nunca na pasta do projeto
