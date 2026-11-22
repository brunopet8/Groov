import math
import wave
from array import array
from datetime import date, datetime, timedelta

import pytest

from src.briefing import (
    PAUSA_S,
    TAXA,
    catalogo,
    descrever_mar,
    frases_do_inicio,
    saudacao,
    gerar_banco,
    montar_audio,
    montar_briefing,
    texto_falado,
)


from src.clima import CONDICOES, Mar, Tempo

AGORA = datetime(2026, 10, 28, 8, 0)
TEMPO = Tempo(24, "parcialmente nublado", 29, 21, 30)


def test_briefing_completo_do_desenho():
    assert date(2026, 10, 28).weekday() == 2
    assert texto_falado(montar_briefing(AGORA, TEMPO, Mar(1.58, "Boa Viagem"))) == (
        "Hoje é quarta-feira, 28 de outubro. Faz 24 graus, parcialmente nublado, máxima de 29 e mínima de 21. "
        "30 por cento de chance de chuva. O mar em Boa Viagem está grande, com ondas de um metro e meio.")


def test_sem_rede_so_a_data():
    frases = montar_briefing(AGORA, None, None)
    assert len(frases) == 1 and texto_falado(frases) == "Hoje é quarta-feira, 28 de outubro."


def test_chuva_baixa_some_e_mar_fora_some():
    seco = texto_falado(montar_briefing(AGORA, Tempo(24, None, 29, 21, 10), Mar(6.0, "Boa Viagem")))
    assert seco == "Hoje é quarta-feira, 28 de outubro. Faz 24 graus, máxima de 29 e mínima de 21."
    frio = montar_briefing(AGORA, Tempo(-2, "céu limpo", 3, -4, 0), None)
    assert texto_falado(frio) == "Hoje é quarta-feira, 28 de outubro."


@pytest.mark.parametrize("altura, esperado", [
    (0.3, ("flat", "meio metro")), (0.7, ("pequeno", "meio metro")), (1.2, ("médio", "um metro")),
    (2.0, ("grande", "dois metros")), (3.1, ("muito grande", "três metros")), (4.9, ("muito grande", "cinco metros")),
    (5.1, None),
])
def test_faixas_do_mar(altura, esperado):
    assert descrever_mar(altura) == esperado


def test_toda_chave_usada_esta_no_catalogo(monkeypatch):
    monkeypatch.setenv("GROOV_MAR", "Boa Viagem;-8.13;-34.9")
    todos = catalogo()
    condicoes = [None, *sorted(set(CONDICOES.values()))]
    dia = datetime(2026, 1, 1, 8)
    usados = {}
    while dia.year == 2026:
        for frase in montar_briefing(dia, None, None):
            usados.update({chave: texto for texto, chave in frase})
        dia += timedelta(days=1)
    for t in range(-5, 50):
        for cond in condicoes:
            for chuva in range(0, 101, 5):
                for frase in montar_briefing(AGORA, Tempo(t, cond, t, t, chuva), None):
                    usados.update({chave: texto for texto, chave in frase})
    for decimos in range(0, 61):
        for frase in montar_briefing(AGORA, None, Mar(decimos / 10, "Boa Viagem")):
            usados.update({chave: texto for texto, chave in frase})
    assert usados and all(todos.get(chave) == texto for chave, texto in usados.items())
    assert all(chave.isascii() and " " not in chave for chave in todos)  # vira nome de arquivo


def gravar_trecho(pasta, chave, tom_s=0.2, silencio_s=0.1, taxa=TAXA):
    """Tom de amplitude 5000 com silêncio nas pontas, como um trecho gravado pelo servidor de voz."""
    pasta.mkdir(exist_ok=True)
    silencio = [0] * int(silencio_s * taxa)
    tom = [int(5000 * math.sin(2 * math.pi * 440 * i / taxa)) or 1000 for i in range(int(tom_s * taxa))]
    with wave.open(str(pasta / f"{chave}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taxa)
        w.writeframes(array("h", silencio + tom + silencio).tobytes())


def test_montar_audio_emenda_e_corta_silencio(tmp_path):
    gravar_trecho(tmp_path, "a")
    gravar_trecho(tmp_path, "b")
    audio = montar_audio([[("A", "a"), ("B", "b")]], tmp_path)
    assert len(audio) == round((0.2 + PAUSA_S + 0.2) * TAXA) * 2


def test_frase_com_trecho_faltando_sai_inteira(tmp_path):
    gravar_trecho(tmp_path, "a")
    gravar_trecho(tmp_path, "b")
    so_a = montar_audio([[("A", "a")], [("B", "b"), ("C", "c")]], tmp_path)
    assert so_a == montar_audio([[("A", "a")]], tmp_path) and len(so_a) == round(0.2 * TAXA) * 2


def test_so_none_quando_nenhuma_frase_monta(tmp_path):
    """29/10: a 1ª frase é a saudação; sem ela, o resto ainda toca. None só sem nada gravado."""
    gravar_trecho(tmp_path, "b")
    assert montar_audio([[("A", "a")], [("B", "b")]], tmp_path) == montar_audio([[("B", "b")]], tmp_path)
    assert montar_audio([[("A", "a")]], tmp_path / "nao_existe") is None


def test_wav_de_outra_taxa_conta_como_faltando(tmp_path):
    gravar_trecho(tmp_path, "a", taxa=44100)
    assert montar_audio([[("A", "a")]], tmp_path) is None


def test_gerar_banco_pula_o_que_existe(tmp_path):
    pedidos = []

    def falar(texto):
        pedidos.append(texto)
        return b"RIFF-falso"

    assert gerar_banco(falar, tmp_path / "frases", {"a": "Um.", "b": "Dois."}) == 2
    assert gerar_banco(falar, tmp_path / "frases", {"a": "Um.", "b": "Dois."}) == 0
    assert pedidos == ["Um.", "Dois."] and (tmp_path / "frases" / "a.wav").read_bytes() == b"RIFF-falso"


def test_wav_truncado_conta_como_faltando(tmp_path):
    """Revisão 28/10: dados com número ímpar de bytes levantavam ValueError e derrubavam o acordar."""
    import struct

    fmt = struct.pack("<HHIIHH", 1, 1, TAXA, TAXA * 2, 2, 16)
    dados = b"\x01\x02\x03"  # cabeçalho promete 100 quadros; o arquivo foi cortado no meio de uma amostra
    corpo = b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + fmt + b"data" + struct.pack("<I", 200) + dados
    (tmp_path / "a.wav").write_bytes(b"RIFF" + struct.pack("<I", len(corpo)) + corpo)
    assert montar_audio([[("A", "a")]], tmp_path) is None


@pytest.mark.parametrize("hora, texto", [(8, "Bom dia, senhor."), (13, "Boa tarde, senhor."),
                                         (20, "Boa noite, senhor."), (3, "Boa noite, senhor.")])
def test_saudacao_por_periodo(hora, texto):
    assert saudacao(datetime(2026, 10, 29, hora))[0] == texto


def test_frases_do_inicio():
    agora = datetime(2026, 10, 29, 8)
    assert texto_falado(frases_do_inicio(agora, False, TEMPO, None)) == "Bom dia, senhor."
    longo = texto_falado(frases_do_inicio(agora, True, None, None))
    assert longo == "Bom dia, senhor. Hoje é quinta-feira, 29 de outubro."
    assert {"saud_dia", "saud_tarde", "saud_noite"} <= set(catalogo())


def test_sintetizar_pede_wav_ao_servidor_local():
    import json
    import urllib.error

    from src.briefing import sintetizar

    pedidos = []

    class Resposta:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b"RIFF..."

    def abrir(pedido, timeout):
        pedidos.append(pedido)
        return Resposta()

    assert sintetizar("Bom dia, senhor.", abrir) == b"RIFF..."
    pedido = pedidos[0]
    assert pedido.full_url == "http://127.0.0.1:8765/v1/audio/speech" and pedido.get_method() == "POST"
    assert json.loads(pedido.data) == {"input": "Bom dia, senhor.", "response_format": "wav"}
    assert pedido.get_header("Authorization") == "Bearer local"

    def falha(pedido, timeout):
        raise urllib.error.URLError("fora do ar")

    assert sintetizar("x", falha) is None


def test_mar_sem_lugar_nao_fala_e_sem_config_nao_entra_no_catalogo():
    assert texto_falado(montar_briefing(AGORA, None, Mar(1.58))) == "Hoje é quarta-feira, 28 de outubro."
    assert not any(chave.startswith("mar_") for chave in catalogo())
