"""Grava o banco de trechos da fala de início (hermes/voz/frases/, voz pessoal: fora do git, nunca publicar) com o
servidor de voz local no ar (127.0.0.1:8765). Rodar da pasta do GROOV: `.venv\\Scripts\\python scripts\\gerar_frases.py`.
Pula o que já existe; para regravar um trecho, apague o .wav dele."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.briefing import PASTA_FRASES, catalogo, gerar_banco, sintetizar  # noqa: E402


def falar(texto: str) -> bytes:
    wav = sintetizar(texto)
    if wav is None:  # não grava lixo: o trecho fica faltando e a próxima rodada tenta de novo
        raise SystemExit("servidor de voz fora do ar ou falhou (suba o GROOV voz e rode de novo)")
    return wav


def main():
    feitos = gerar_banco(falar)
    print(f"{feitos} trechos gravados ({len(catalogo())} no catálogo) em {PASTA_FRASES}")


if __name__ == "__main__":
    main()
