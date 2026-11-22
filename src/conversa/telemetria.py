"""Telemetria do painel SISTEMA: leitura da VRAM e o laço que manda uma leitura a cada CADA_S. Sem pipecat."""
import asyncio
import logging
import subprocess
import sys
from typing import Awaitable, Callable

log = logging.getLogger("groov.telemetria")  # ponte do servidor.configurar_log; sem loguru, roda nos dois venvs

CADA_S = 5.0
SEM_JANELA = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0  # o servidor roda sob pythonw


def ler_vram(rodar=subprocess.run) -> tuple[int, int] | None:
    """(usada, total) em MiB da 1ª placa; None se o nvidia-smi falta, demora mais de 2 s ou não dá número."""
    try:
        r = rodar(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
                  capture_output=True, text=True, timeout=2, creationflags=SEM_JANELA)
        if r.returncode != 0:
            return None
        usada, total = (int(x) for x in r.stdout.splitlines()[0].split(","))
        return usada, total
    except Exception:  # falta do programa, tempo, "N/A", saída vazia: o painel mostra "—"
        return None


def montar(vram: tuple[int, int] | None, latencia_ms: int | None, voz: bool, whisper: bool) -> dict:
    usada, total = vram if vram else (None, None)
    return {"vram_usada": usada, "vram_total": total, "latencia_ms": latencia_ms, "voz": voz, "whisper": whisper}


async def transmitir(ligada: Callable[[], bool], acordado: Callable[[], bool], coletar: Callable[[], Awaitable[dict]],
                     enviar: Callable[[dict], Awaitable[None]], esperar=asyncio.sleep) -> None:
    while True:
        await esperar(CADA_S)
        if ligada() and acordado():
            try:
                await enviar({"telemetria": await coletar()})
            except Exception as erro:  # uma leitura ruim não para as seguintes; sem valores no log
                log.warning(f"telemetria falhou ({type(erro).__name__})")
