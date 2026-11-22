"""Timers da conversa: simples (toca "Senhor, deu o tempo.") e de desligar (`shutdown /s /t`, feito pelo Windows,
sobrevive a queda do GROOV). Sem pipecat. `TIMERS` mora no módulo, como `BRIEFING`, para sobreviver à recarga da
janela; cada `bot()` conecta o seu aviso no início e desconecta no `finally`."""
import asyncio
import logging
import subprocess
import time
from collections.abc import Awaitable, Callable

from src.briefing import DEU_O_TEMPO
from src.conversa.ajudante import SEM_JANELA
from src.conversa.regras_pc import PedidoTimer, cita_desligar, qual_timer

log = logging.getLogger("groov.timers")

# no catálogo do briefing: scripts/gerar_frases.py grava hermes/voz/frases/deu_o_tempo.wav
FRASE_DEU_O_TEMPO, CHAVE_DEU_O_TEMPO = DEU_O_TEMPO
NADA_AGENDADO = 1116  # ERROR_NO_SHUTDOWN_IN_PROGRESS: `shutdown /a` sem nada agendado já é o que se queria
JA_AGENDADO = 1190  # ERROR_SHUTDOWN_IS_SCHEDULED: agendado antes de o GROOV reiniciar, `TIMERS` não sabia

Aviso = Callable[[], Awaitable[None]]


async def rodar_sem_janela(cmd: list[str]) -> int:
    try:
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                                    creationflags=SEM_JANELA)
    except OSError:
        return -1
    return await proc.wait()


class Timers:
    def __init__(self, rodar: Callable[[list[str]], Awaitable[int]], dormir=asyncio.sleep, agora=time.time):
        self._rodar = rodar
        self._dormir = dormir
        self._agora = agora  # relógio de parede: o `fim` vai para a janela, que lê a hora de verdade
        self._fim_simples: float | None = None
        self._fim_desligar: float | None = None
        self._ao_mudar: Callable[[], None] | None = None
        self._aviso: Aviso | None = None
        self._simples: asyncio.Task | None = None
        self._desligar = False

    def conectar(self, tocar_aviso: Aviso) -> None:
        self._aviso = tocar_aviso

    def observar(self, ao_mudar: Callable[[], None] | None) -> None:
        """Avisa (síncrono) ao armar, cancelar e disparar; quem observa consulta `fins()`."""
        self._ao_mudar = ao_mudar

    def desobservar(self, ao_mudar: Callable[[], None]) -> None:
        if self._ao_mudar is ao_mudar:  # a recarga pode já ter ligado o observador do bot novo
            self._ao_mudar = None

    def _mudou(self) -> None:
        if self._ao_mudar is None:
            return
        try:
            self._ao_mudar()
        except Exception as erro:  # o painel é enfeite: não pode quebrar o timer
            log.warning("observador do timer falhou: %s", type(erro).__name__)

    def fins(self) -> dict[str, float]:
        """Quando vence cada timer armado: {"simples": epoch, "desligar": epoch}."""
        fins = {}
        if self._simples_armado() and self._fim_simples is not None:
            fins["simples"] = self._fim_simples
        if self._desligar and self._fim_desligar is not None:
            fins["desligar"] = self._fim_desligar
        return fins

    def desconectar(self, tocar_aviso: Aviso) -> None:
        if self._aviso is tocar_aviso:  # a recarga pode já ter conectado o bot novo
            self._aviso = None

    def _simples_armado(self) -> bool:
        return self._simples is not None and not self._simples.done()

    def armado(self) -> bool:
        return self._desligar or self._simples_armado()

    async def _abortar(self) -> bool:
        ok = await self._rodar(["shutdown", "/a"]) in (0, NADA_AGENDADO)
        if ok:
            self._desligar = False
            self._mudou()
        return ok

    def _parar_simples(self) -> None:
        if self._simples_armado():
            self._simples.cancel()
        self._simples = None
        self._fim_simples = None
        self._mudou()

    async def armar(self, pedido: PedidoTimer) -> bool:
        """Timer novo substitui o do mesmo tipo. False: não armou (ambíguo, sem minutos ou o Windows recusou)."""
        if pedido.ambiguo or not pedido.minutos or pedido.minutos <= 0:
            return False
        if not pedido.desligar:
            self._parar_simples()
            self._simples = asyncio.create_task(self._esperar(pedido.minutos * 60))
            self._fim_simples = self._agora() + pedido.minutos * 60
            self._mudou()
            return True
        if self._desligar and not await self._abortar():
            return False
        cmd = ["shutdown", "/s", "/t", str(pedido.minutos * 60)]
        codigo = await self._rodar(cmd)
        if codigo == JA_AGENDADO and await self._abortar():
            codigo = await self._rodar(cmd)
        self._desligar = codigo == 0
        if self._desligar:
            self._fim_desligar = self._agora() + pedido.minutos * 60
            self._mudou()
        return self._desligar

    async def _esperar(self, segundos: int) -> None:
        await self._dormir(segundos)
        self._fim_simples = None
        self._mudou()
        if self._aviso is None:
            log.info("timer acabou sem conexão: aviso perdido")
            return
        try:
            await self._aviso()
        except Exception as erro:  # o aviso falhar não pode derrubar o resto
            log.warning("aviso do timer falhou: %s", type(erro).__name__)

    async def cancelar(self, transcricao: str) -> str:
        """"simples" | "desligar" | "ambos" | "qual" | "nenhum", ou "falhou" se o `shutdown /a` não confirmou.
        Citando desligar ou PC, roda `shutdown /a` sempre, mesmo sem registro."""
        alvo = qual_timer(transcricao)
        if alvo is None:
            if self._desligar and self._simples_armado():
                return "qual"
            alvo = "desligar" if self._desligar else "simples" if self._simples_armado() else None
            if alvo is None:
                return "nenhum"
        if alvo in ("desligar", "ambos") and not await self._abortar():
            return "falhou"
        if alvo == "simples" and cita_desligar(transcricao):  # "desligar o forno": o /a roda mesmo assim
            estava = self._desligar
            if await self._abortar() and estava:
                alvo = "ambos"
        if alvo in ("simples", "ambos"):
            self._parar_simples()
        return alvo


TIMERS = Timers(rodar_sem_janela)
