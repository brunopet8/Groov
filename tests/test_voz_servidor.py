import io
import json
import sys
import threading
import urllib.error
import urllib.request
import wave

import pytest

from src.voz_servidor import (
    ESPERA_MAX,
    TAXA,
    conferir_taxa,
    criar_servidor,
    garantir_saida,
    hora_de_desligar,
    ler_pedido,
    para_pcm16,
)

CHAVE = {"Authorization": "Bearer local"}


def test_pedido_valido():
    corpo = json.dumps({"input": " Bom dia, senhor. ", "response_format": "pcm"}).encode()
    assert ler_pedido(corpo) == ("Bom dia, senhor.", "pcm")


@pytest.mark.parametrize("corpo", [
    b"nao e json",
    b"\xff\xfe",  # UTF-8 inválido
    json.dumps({"input": "   "}).encode(),
    json.dumps({"input": "oi", "response_format": "mp3"}).encode(),
    json.dumps({"input": "x" * 2001}).encode(),
])
def test_pedido_invalido(corpo):
    with pytest.raises(ValueError):
        ler_pedido(corpo)


def _falar_teste(texto):
    if texto == "quebra":
        raise RuntimeError("CUDA out of memory")
    return [b"\x01\x00", b"\x02\x00"]


@pytest.fixture
def servidor():
    desligados = []
    s = criar_servidor(_falar_teste, lambda: desligados.append(True), porta=0)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield s, f"http://127.0.0.1:{s.server_address[1]}", desligados
    s.shutdown()
    s.server_close()


def _post(url, dados=None, cabecalhos=CHAVE):
    corpo = json.dumps(dados).encode() if dados is not None else b""
    pedido = urllib.request.Request(url, data=corpo, method="POST", headers=cabecalhos)
    with urllib.request.urlopen(pedido) as r:
        return r.headers, r.read()


def _codigo_de_erro(url, dados=None, cabecalhos=CHAVE):
    with pytest.raises(urllib.error.HTTPError) as erro:
        _post(url, dados, cabecalhos)
    return erro.value.code


def test_pcm_em_pedacos_com_taxa(servidor):
    _, url, _ = servidor
    cabecalhos, audio = _post(f"{url}/v1/audio/speech", {"input": "oi", "response_format": "pcm"})
    assert audio == b"\x01\x00\x02\x00"
    assert cabecalhos["X-Audio-Sample-Rate"] == str(TAXA)


def test_wav_completo(servidor):
    _, url, _ = servidor
    _, audio = _post(f"{url}/v1/audio/speech", {"input": "oi", "response_format": "wav"})
    with wave.open(io.BytesIO(audio)) as w:
        assert (w.getframerate(), w.getnchannels(), w.readframes(2)) == (TAXA, 1, b"\x01\x00\x02\x00")


def test_erros_de_pedido(servidor):
    _, url, _ = servidor
    assert _codigo_de_erro(f"{url}/v1/audio/speech", {"input": ""}) == 400
    assert _codigo_de_erro(f"{url}/outro", {"input": "oi"}) == 404
    assert _codigo_de_erro(f"{url}/v1/audio/speech", {"input": "quebra", "response_format": "wav"}) == 500


def test_sem_chave_ou_de_outro_site_e_recusado(servidor):
    _, url, desligados = servidor
    assert _codigo_de_erro(f"{url}/desligar", cabecalhos={}) == 401
    host_falso = {**CHAVE, "Host": "site-malicioso.com"}  # DNS rebinding
    assert _codigo_de_erro(f"{url}/desligar", cabecalhos=host_falso) == 403
    assert desligados == []


def test_desligar(servidor):
    _, url, desligados = servidor
    _post(f"{url}/desligar")
    assert desligados == [True]


def test_registra_inicio_da_ultima_fala(servidor):
    s, url, _ = servidor
    _post(f"{url}/v1/audio/speech", {"input": "oi", "response_format": "pcm"})
    assert s.estado["ativos"] == 0 and s.estado["inicio"] > 0


def test_desliga_so_depois_da_despedida():
    pedido = 100.0
    assert not hora_de_desligar(102, pedido, inicio_ultima_fala=90, ativos=0)  # despedida ainda não veio
    assert not hora_de_desligar(103, pedido, inicio_ultima_fala=101, ativos=1)  # despedida tocando
    assert hora_de_desligar(104, pedido, inicio_ultima_fala=101, ativos=0)  # despedida terminou
    assert hora_de_desligar(pedido + ESPERA_MAX, pedido, inicio_ultima_fala=90, ativos=0)  # teto


def test_pcm16_corta_o_que_passa_de_1_e_vira_16_bits():
    np = pytest.importorskip("numpy")
    pcm = para_pcm16(np.array([0.0, 0.5, 1.5, -2.0], dtype=np.float32))
    assert np.frombuffer(pcm, dtype="<i2").tolist() == [0, 16383, 32767, -32767]


def test_pcm16_aceita_pedaco_em_duas_dimensoes():
    np = pytest.importorskip("numpy")
    assert len(para_pcm16(np.zeros((1, 5), dtype=np.float32))) == 10  # 5 amostras x 2 bytes


def test_get_diz_qual_motor_esta_na_porta():
    """Sem isto o bot não distingue um XTTS esquecido ligado de um Qwen: ambos respondem na 8765."""
    s = criar_servidor(_falar_teste, lambda: None, porta=0)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{s.server_address[1]}/") as r:
            assert r.status == 200 and json.loads(r.read()) == {"motor": "qwen"}
    finally:
        s.shutdown()
        s.server_close()


def test_taxa_diferente_de_24k_e_recusada():
    conferir_taxa(24000)
    with pytest.raises(RuntimeError):
        conferir_taxa(22050)  # a voz sairia com a altura errada, sem erro nenhum


def test_sem_console_stdout_e_stderr_vao_para_o_log(monkeypatch, tmp_path):
    """Sob pythonw (atalho de início) sys.stdout/stderr são None e a barra tqdm do Hugging Face quebra ao escrever."""
    log = tmp_path / "voz.log"
    monkeypatch.setattr("src.voz_servidor.LOG", log)
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    garantir_saida()
    try:
        sys.stdout.write("barra ")
        sys.stderr.write("aviso\n")
        sys.stdout.flush()
        sys.stderr.flush()
        assert sys.stdout is not None and sys.stderr is not None
    finally:
        sys.stdout.close()  # o monkeypatch devolve os None depois
    assert log.read_text(encoding="utf-8") == "barra aviso\n"


def test_com_console_nao_mexe_na_saida(monkeypatch, tmp_path):
    log = tmp_path / "voz.log"
    monkeypatch.setattr("src.voz_servidor.LOG", log)
    saida, erro = sys.stdout, sys.stderr
    garantir_saida()
    assert (sys.stdout, sys.stderr) == (saida, erro) and not log.exists()


def test_escuta_so_local_e_nao_divide_a_porta():
    s = criar_servidor(_falar_teste, lambda: None, porta=0)
    try:
        assert s.server_address[0] == "127.0.0.1"
        with pytest.raises(OSError):  # 2ª cópia não sobe (no Windows SO_REUSEADDR deixaria)
            criar_servidor(_falar_teste, lambda: None, porta=s.server_address[1])
    finally:
        s.server_close()
