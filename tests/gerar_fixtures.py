"""Gera tests/fixtures/*.wav (16 kHz mono, fora do git) com o Kokoro, para os testes do despertador e do Whisper.

hey_jarvis.wav: "Hey Jarvis" (voz inglesa) com 1 s de silêncio antes e depois.
jarvis_hora.wav: "Jarvis, que horas são?" (voz pt-BR).
acorda_groov.wav: "Acorda, Gruv." (voz pt-BR), para o despertador pelo nome.
Uso: .venv-conversa/Scripts/python tests/gerar_fixtures.py
"""
from pathlib import Path

import numpy as np
import soundfile as sf
import soxr
from kokoro_onnx import Kokoro
from pipecat.services.kokoro.tts import KOKORO_CACHE_DIR, _ensure_model_files

PASTA = Path(__file__).with_name("fixtures")


def falar(kokoro, texto, voz, lingua, silencio_s):
    audio, taxa = kokoro.create(texto, voice=voz, lang=lingua)
    audio = soxr.resample(audio, taxa, 16000)
    pausa = np.zeros(int(16000 * silencio_s), dtype=np.float32)
    return np.concatenate([pausa, audio, pausa])


def main():
    modelo, vozes = KOKORO_CACHE_DIR / "kokoro-v1.0.onnx", KOKORO_CACHE_DIR / "voices-v1.0.bin"
    _ensure_model_files(modelo, vozes)  # já em cache; só baixa se faltar
    kokoro = Kokoro(str(modelo), str(vozes))
    PASTA.mkdir(exist_ok=True)
    sf.write(PASTA / "hey_jarvis.wav", falar(kokoro, "Hey Jarvis", "am_adam", "en-us", 1.0), 16000, subtype="PCM_16")
    sf.write(PASTA / "jarvis_hora.wav", falar(kokoro, "Jarvis, que horas são?", "pm_alex", "pt-br", 0.5), 16000, subtype="PCM_16")
    sf.write(PASTA / "acorda_groov.wav", falar(kokoro, "Acorda, Gruv.", "pm_alex", "pt-br", 0.5), 16000, subtype="PCM_16")
    print(f"fixtures em {PASTA}")


if __name__ == "__main__":
    main()
