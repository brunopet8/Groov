"""Áudio de início numa peça só: efeitos da abertura, a música de início por baixo e a voz do GROOV por cima.

A música (hermes/voz/musica_inicio.wav, do usuário: uso pessoal, fora do git) toca forte com a abertura, desce sob a
voz e some no fim. A Trilha guarda onde a música está, para os pedaços seguirem um no outro sem emenda.
"""
import io
import wave
from pathlib import Path

import numpy as np

TAXA = 24000
VOL_ALTO = 0.35  # música junto com os efeitos (o usuário calibra de ouvido)
VOL_BAIXO = 0.12  # música sob a fala
GANHO_EFEITOS = 0.8
DESCIDA_S = 0.3  # a música desce antes de a voz entrar
SUMIR_S = 1.5


def ler_wav(fonte: Path | bytes) -> np.ndarray | None:
    """Mono 16-bit 24 kHz em float -1..1 (arquivo ou o WAV inteiro em bytes); None se faltar ou for outro formato."""
    try:
        with wave.open(io.BytesIO(fonte) if isinstance(fonte, bytes) else str(fonte)) as w:
            if (w.getnchannels(), w.getsampwidth(), w.getframerate()) != (1, 2, TAXA):
                return None
            dados = w.readframes(w.getnframes())
    except (OSError, EOFError, wave.Error):
        return None
    return np.frombuffer(dados[: len(dados) // 2 * 2], dtype="<i2").astype(np.float32) / 32767


def _pcm(sinal: np.ndarray) -> bytes:
    return (np.clip(sinal, -1, 1) * 32767).astype("<i2").tobytes()


class Trilha:
    def __init__(self, musica: np.ndarray | None):
        self._musica = musica
        self.posicao = 0

    def _musica_seguinte(self, n: int) -> np.ndarray:
        trecho = np.zeros(n, dtype=np.float32)
        if self._musica is not None:
            pedaco = self._musica[self.posicao:self.posicao + n]
            trecho[:len(pedaco)] = pedaco  # acabou a música: completa com silêncio
        self.posicao += n
        return trecho

    def abertura(self, efeitos: np.ndarray) -> bytes:
        return _pcm(GANHO_EFEITOS * efeitos + VOL_ALTO * self._musica_seguinte(len(efeitos)))

    def espera(self, seg: float) -> bytes:
        """Só música, enquanto a voz ainda não chegou: nada de silêncio no meio do início."""
        return _pcm(VOL_ALTO * self._musica_seguinte(int(seg * TAXA)))

    def com_voz(self, voz: np.ndarray | None) -> bytes:
        """Música desce de VOL_ALTO a VOL_BAIXO, a voz entra por cima e a música some em SUMIR_S. Sem voz, só some."""
        sumir = np.linspace(VOL_BAIXO if voz is not None else VOL_ALTO, 0, int(SUMIR_S * TAXA), dtype=np.float32)
        if voz is None:
            return _pcm(sumir * self._musica_seguinte(len(sumir)))
        descida = np.linspace(VOL_ALTO, VOL_BAIXO, int(DESCIDA_S * TAXA), dtype=np.float32)
        volumes = np.concatenate([descida, np.full(len(voz), VOL_BAIXO, dtype=np.float32), sumir])
        fala = np.concatenate([np.zeros(len(descida), dtype=np.float32), voz, np.zeros(len(sumir), dtype=np.float32)])
        return _pcm(volumes * self._musica_seguinte(len(volumes)) + fala)
