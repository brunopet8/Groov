"""Gera tests/fala.wav (voz pt-BR do Kokoro, fora do git) para servir de microfone falso em scripts/medir_conversa.py.

Adaptado do projeto REA.
Layout: 6 s de silêncio + pergunta + 14 s de silêncio (resposta do bot). O Chrome toca em loop, então a
pergunta se repete a cada ~23 s e cai depois do pipeline pronto.
Uso: .venv-conversa/Scripts/python scripts/gerar_fala.py
"""
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro
from pipecat.services.kokoro.tts import KOKORO_CACHE_DIR, _ensure_model_files

PERGUNTA = "Oi Jarvis, me diz rapidinho: qual é a capital da Austrália?"


def main(out=Path(__file__).resolve().parents[1] / "tests" / "fala.wav"):
    # Mesmo cache e download do KokoroTTSService do bot.
    model, voices = KOKORO_CACHE_DIR / "kokoro-v1.0.onnx", KOKORO_CACHE_DIR / "voices-v1.0.bin"
    _ensure_model_files(model, voices)
    kokoro = Kokoro(str(model), str(voices))
    audio, sr = kokoro.create(PERGUNTA, voice="pm_alex", lang="pt-br")
    silencio = lambda s: np.zeros(int(sr * s), dtype=np.float32)
    sf.write(out, np.concatenate([silencio(6), audio, silencio(14)]), sr, subtype="PCM_16")
    print(f"{out} fala={len(audio) / sr:.2f}s fim_da_fala={6 + len(audio) / sr:.2f}s")


if __name__ == "__main__":
    main(*map(Path, sys.argv[1:]))
