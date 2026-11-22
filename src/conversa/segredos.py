"""Chaves de privado/.env: lidas aqui e entregues só a quem precisa. Nunca entram em os.environ (os filhos herdariam)."""
from pathlib import Path

from dotenv import dotenv_values

ENV = Path(__file__).resolve().parents[2] / "privado" / ".env"


def ler_segredos(caminho: Path = ENV) -> dict[str, str]:
    return {nome: valor for nome, valor in dotenv_values(caminho).items() if valor}
