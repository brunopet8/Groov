"""Efeitos da abertura (V3 "holograma", escolhida pelo usuário em 29/10): painel holográfico ligando, inspirado no
som de início antigo (graves com subida, chiado, arpejo de bipes, catraca, acorde de "pronto", servo, bipes de
painel e um encaixe). Sintetizado aqui, sem gravação de terceiros; semente fixa = sempre o mesmo som."""
import numpy as np

TAXA = 24000
DURACAO_S = 6.6
PICO = 0.89  # -1 dBFS


def _t(n):
    return np.arange(n) / TAXA


def _envelope(n, ataque, queda):
    t = _t(n)
    return np.clip(t / max(ataque, 1e-4), 0, 1) * np.exp(-np.maximum(t - ataque, 0) / max(queda, 1e-4))


def _banda(sinal, baixo, alto):
    espectro = np.fft.rfft(sinal)
    f = np.fft.rfftfreq(len(sinal), 1 / TAXA)
    espectro[(f < baixo) | (f > alto)] = 0
    return np.fft.irfft(espectro, len(sinal))


def _varredura(f0, f1, dur, harm):
    n = int(dur * TAXA)
    f = f0 * (f1 / f0) ** ((_t(n) / dur) ** 2)
    fase = 2 * np.pi * np.cumsum(f) / TAXA
    return sum(a * np.sin((k + 1) * fase) for k, a in enumerate(harm))


def _ping(freq, dur, queda, parciais, pesos):
    t = _t(int(dur * TAXA))
    return sum(p * np.sin(2 * np.pi * freq * r * t) * np.exp(-t / (queda / (1 + i)))
               for i, (r, p) in enumerate(zip(parciais, pesos)))


def _clique(rng, freq, forca):
    n = int(0.012 * TAXA)
    s = np.zeros(int(0.08 * TAXA))
    s[:n] += 0.8 * _banda(rng.standard_normal(n), 1500, 9000) * _envelope(n, 0.0005, 0.003)
    return forca * (s + 0.5 * _ping(freq, 0.08, 0.02, (1.0, 2.31), (1.0, 0.4)))


def _encaixe(rng, peso, metal):
    n = int(0.5 * TAXA)
    t = _t(n)
    baque = np.sin(2 * np.pi * (45 + 35 * np.exp(-t / 0.04)) * t) * np.exp(-t / 0.09)
    ruido = _banda(rng.standard_normal(n), 200, 5000) * _envelope(n, 0.001, 0.015)
    metalico = _ping(metal, 0.5, 0.25, (1.0, 2.76, 5.40, 8.93), (1.0, 0.5, 0.3, 0.15))
    return peso * (baque + 0.6 * ruido + 0.25 * metalico)


def _bipe(freq, dur, quadrado):
    t = _t(int(dur * TAXA))
    return (np.sin(2 * np.pi * freq * t) + quadrado * np.sin(6 * np.pi * freq * t) / 3) * _envelope(len(t), 0.003, dur / 3)


def _servo(f0, f1, dur, vibrato):
    t = _t(int(dur * TAXA))
    f = f0 + (f1 - f0) * (t / dur) ** 0.7 + 12 * np.sin(2 * np.pi * vibrato * t)
    fase = 2 * np.pi * np.cumsum(f) / TAXA
    return (np.sin(fase) + 0.4 * np.sin(2 * fase)) * np.minimum(1, t / 0.08) * np.minimum(1, (dur - t) / 0.12)


def _chiado(rng, dur, baixo, alto):
    n = int(dur * TAXA)
    return _banda(rng.standard_normal(n), baixo, alto) * np.sin(np.pi * _t(n) / dur) ** 2


def _drone(dur, freq):
    t = _t(int(dur * TAXA))
    onda = np.sin(2 * np.pi * freq * t) + 0.5 * np.sin(4 * np.pi * freq * t) + 0.2 * np.sin(2 * np.pi * 3.01 * freq * t)
    return onda * np.minimum(1, t / 0.4) * np.minimum(1, (dur - t) / 1.2)


def _acorde(freqs, dur, queda):
    return sum(_ping(f, dur, queda, (1.0, 2.0), (1.0, 0.2)) for f in freqs) / len(freqs)


def _reverb(rng, sinal, tempo_s, mistura):
    n = int(tempo_s * TAXA)
    ir = _banda(rng.standard_normal(n) * np.exp(-_t(n) / (tempo_s / 5)), 200, 7000)
    molhado = np.fft.irfft(np.fft.rfft(sinal, len(sinal) + n) * np.fft.rfft(ir, len(sinal) + n))[:len(sinal)]
    return (1 - mistura) * sinal / np.max(np.abs(sinal)) + mistura * molhado / np.max(np.abs(molhado))


def abertura(semente: int = 7) -> np.ndarray:
    """~6,6 s mono 24 kHz em float, pico em PICO e fim em fade de 0,3 s."""
    rng = np.random.default_rng(semente)
    eventos = [(0.0, _drone(2.6, 55.0), 0.3),
               (0.1, _varredura(220, 1760, 1.0, (1, 0.25)) * _envelope(int(1.0 * TAXA), 0.9, 0.25), 0.4),
               (0.9, _chiado(rng, 0.6, 5000, 11500), 0.25)]
    notas = (880, 1108.7, 1318.5, 1760, 2217.5, 2637)
    eventos += [(1.30 + 0.09 * k, _bipe(f, 0.08, 0.1), 0.3) for k, f in enumerate(notas)]
    eventos += [(1.95 + 0.11 * k, _clique(rng, 2600, 0.6), 0.4) for k in range(6)]
    eventos += [(2.70, _acorde((880, 1320, 1760, 2640), 2.0, 0.9), 0.5),
                (3.60, _servo(1200, 1700, 0.7, 4.0), 0.15),
                (4.40, _bipe(3500, 0.05, 0.3), 0.3), (4.55, _bipe(2500, 0.05, 0.3), 0.3),
                (4.70, _bipe(2000, 0.05, 0.3), 0.3),
                (5.20, _chiado(rng, 0.4, 4000, 11000), 0.2), (5.45, _encaixe(rng, 0.6, 900), 0.6)]
    mix = np.zeros(int(DURACAO_S * TAXA))
    for inicio, som, ganho in eventos:
        i = int(inicio * TAXA)
        fim = min(len(mix), i + len(som))
        mix[i:fim] += ganho * som[:fim - i]
    mix = _reverb(rng, mix, 1.2, 0.3)
    mix = mix / np.max(np.abs(mix)) * PICO
    fade = int(0.3 * TAXA)
    mix[-fade:] *= np.linspace(1, 0, fade)
    return mix.astype(np.float32)
