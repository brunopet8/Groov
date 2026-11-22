import asyncio
import subprocess
import types

import pytest

from src.conversa.telemetria import montar, ler_vram, transmitir


def _rodar(saida="", codigo=0):
    return lambda *a, **k: types.SimpleNamespace(returncode=codigo, stdout=saida)


def test_ler_vram_le_usada_e_total():
    assert ler_vram(_rodar("5903, 8188\n")) == (5903, 8188)


def test_ler_vram_varias_placas_usa_a_primeira_linha():
    assert ler_vram(_rodar("5903, 8188\n100, 4096\n")) == (5903, 8188)


def test_ler_vram_pede_teto_de_2s_e_captura_a_saida():
    visto = {}

    def rodar(*a, **k):
        visto.update(k)
        return types.SimpleNamespace(returncode=0, stdout="1, 2")

    ler_vram(rodar)
    assert visto["timeout"] == 2
    assert visto["capture_output"] is True


def test_ler_vram_falhas_viram_none():
    def levanta(*a, **k):
        raise FileNotFoundError

    def estoura(*a, **k):
        raise subprocess.TimeoutExpired("nvidia-smi", 2)

    assert ler_vram(_rodar("1, 2", codigo=9)) is None
    assert ler_vram(levanta) is None
    assert ler_vram(estoura) is None
    assert ler_vram(_rodar("N/A, N/A")) is None
    assert ler_vram(_rodar("")) is None


def test_montar():
    assert montar((5903, 8188), 1500, True, False) == {
        "vram_usada": 5903, "vram_total": 8188, "latencia_ms": 1500, "voz": True, "whisper": False}
    d = montar(None, None, False, False)
    assert d["vram_usada"] is None and d["vram_total"] is None and d["latencia_ms"] is None


def _rodar_laco(ligada, acordado, coletar):
    enviados = []
    ticks = {"n": 0}

    async def esperar(_s):
        ticks["n"] += 1
        if ticks["n"] == 3:
            raise asyncio.CancelledError

    async def enviar(d):
        enviados.append(d)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(transmitir(ligada, acordado, coletar, enviar, esperar))
    return enviados


def test_transmitir_desligada_nao_envia():
    async def coletar():
        return {"a": 1}

    assert _rodar_laco(lambda: False, lambda: True, coletar) == []


def test_transmitir_dormindo_nao_envia():
    async def coletar():
        return {"a": 1}

    assert _rodar_laco(lambda: True, lambda: False, coletar) == []


def test_transmitir_ligada_e_acordada_envia_a_cada_tique():
    async def coletar():
        return {"a": 1}

    assert _rodar_laco(lambda: True, lambda: True, coletar) == [{"telemetria": {"a": 1}}] * 2


def test_transmitir_erro_ao_coletar_nao_para_o_laco():
    chamadas = []

    async def coletar():
        chamadas.append(1)
        if len(chamadas) == 1:
            raise RuntimeError("falhou")
        return {"a": 1}

    assert _rodar_laco(lambda: True, lambda: True, coletar) == [{"telemetria": {"a": 1}}]
