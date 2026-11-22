"""Grava hermes/voz/abertura.wav (efeitos do áudio de início, 24 kHz mono). Rodar uma vez da pasta do GROOV:
`.venv-conversa\\Scripts\\python scripts\\gerar_abertura.py`."""
import sys
import wave
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from src.conversa.abertura import TAXA, abertura  # noqa: E402

DESTINO = RAIZ / "hermes" / "voz" / "abertura.wav"


def main():
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(DESTINO), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TAXA)
        w.writeframes((abertura() * 32767).astype("<i2").tobytes())
    print(DESTINO)


if __name__ == "__main__":
    main()
