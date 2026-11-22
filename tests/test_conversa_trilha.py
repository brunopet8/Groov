import pytest

np = pytest.importorskip("numpy")

from src.conversa.trilha import DESCIDA_S, SUMIR_S, TAXA, VOL_ALTO, VOL_BAIXO, Trilha


def pcm(b):
    return np.frombuffer(b, dtype=np.int16).astype(np.float32) / 32767


def test_abertura_e_espera_avancam_na_musica():
    musica = np.full(TAXA * 10, 0.5, dtype=np.float32)
    trilha = Trilha(musica)
    abertura = pcm(trilha.abertura(np.zeros(TAXA, dtype=np.float32)))
    assert len(abertura) == TAXA and abertura[100] == pytest.approx(0.5 * VOL_ALTO, abs=1e-3)
    espera = pcm(trilha.espera(0.5))
    assert len(espera) == TAXA // 2 and trilha.posicao == TAXA + TAXA // 2


def test_musica_desce_sob_a_voz_e_some_no_fim():
    trilha = Trilha(np.full(TAXA * 10, 0.5, dtype=np.float32))
    voz = np.zeros(TAXA, dtype=np.float32)
    saida = pcm(trilha.com_voz(voz))
    descida, n_voz, sumir = int(DESCIDA_S * TAXA), len(voz), int(SUMIR_S * TAXA)
    assert len(saida) == descida + n_voz + sumir
    assert saida[0] == pytest.approx(0.5 * VOL_ALTO, abs=1e-2)
    assert saida[descida + n_voz // 2] == pytest.approx(0.5 * VOL_BAIXO, abs=1e-3)
    assert abs(saida[-1]) < 1e-3


def test_voz_entra_por_cima_sem_estourar():
    trilha = Trilha(np.full(TAXA * 10, 1.0, dtype=np.float32))
    saida = pcm(trilha.com_voz(np.full(TAXA, 1.0, dtype=np.float32)))
    assert saida.max() <= 1.0 and saida[int(DESCIDA_S * TAXA) + 10] == pytest.approx(1.0, abs=1e-3)


def test_sem_voz_so_some_e_musica_curta_completa_com_silencio():
    trilha = Trilha(np.full(100, 0.5, dtype=np.float32))
    saida = pcm(trilha.com_voz(None))
    assert len(saida) == int(SUMIR_S * TAXA) and np.all(saida[200:] == 0)


def test_sem_musica_toca_so_efeitos_e_voz():
    trilha = Trilha(None)
    efeitos = np.full(TAXA, 0.5, dtype=np.float32)
    assert pcm(trilha.abertura(efeitos)).max() > 0
    voz = np.full(TAXA, 0.25, dtype=np.float32)
    assert pcm(trilha.com_voz(voz)).max() == pytest.approx(0.25, abs=1e-3)


def test_abertura_v3_deterministica():
    from src.conversa.abertura import DURACAO_S, PICO, abertura

    a, b = abertura(), abertura()
    assert np.array_equal(a, b) and len(a) == int(DURACAO_S * TAXA)
    assert np.max(np.abs(a)) <= PICO + 1e-6 and abs(a[-1]) < 1e-3
