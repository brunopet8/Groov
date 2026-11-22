"""Coletor: roda as fontes (hoje só o Trello) em laço dentro do servidor da conversa; cada uma falha sozinha."""
import asyncio
import sys
import time
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from datetime import datetime

from src.vida.banco import Banco
from src.vida.trello import _buscar_json, comparar, ler_quadros


@dataclass
class Fonte:
    nome: str
    intervalo: float
    coletar: Callable[[datetime], Awaitable[None]]


def descrever_erro(erro: BaseException) -> str:
    """Só o tipo e o código HTTP: str(erro) pode trazer texto de resposta, URL ou conteúdo, e o log não pode."""
    codigo = getattr(erro, "code", None)
    nome = type(erro).__name__
    return f"{nome} {codigo}" if isinstance(codigo, int) else nome


def _stderr(mensagem: str) -> None:
    print(mensagem, file=sys.stderr)


class Coletor:
    def __init__(self, banco: Banco, fontes: list[Fonte], avisar: Callable[[str], None] = _stderr,
                 agora: Callable[[], datetime] = lambda: datetime.now().astimezone(),
                 relogio: Callable[[], float] = time.monotonic):
        self.banco, self.fontes = banco, fontes
        self.trava = None  # montar_coletor guarda aqui o arquivo travado, para ele não ser fechado
        self._avisar, self._agora, self._relogio = avisar, agora, relogio
        self._pedido = asyncio.Event()

    def pedir_rodada(self) -> None:
        """Todas as fontes rodam já (o "Hey JARVIS" pede, para a resposta de "novidades" estar em dia)."""
        self._pedido.set()

    async def rodar(self) -> None:
        vence = {f.nome: float("-inf") for f in self.fontes}  # -inf: na primeira volta todas rodam
        while True:
            for fonte in self.fontes:
                if vence[fonte.nome] <= self._relogio():
                    try:
                        await fonte.coletar(self._agora())
                    except Exception as erro:  # uma fonte que cai não derruba as outras nem o servidor
                        self._avisar(f"coletor: {fonte.nome} falhou ({descrever_erro(erro)})")
                    vence[fonte.nome] = self._relogio() + fonte.intervalo
            espera = max(0.0, min(vence.values()) - self._relogio()) if vence else None  # None: só pedidos
            try:
                await asyncio.wait_for(self._pedido.wait(), espera)
            except TimeoutError:
                pass
            if self._pedido.is_set():
                self._pedido.clear()
                vence = dict.fromkeys(vence, float("-inf"))


def fonte_trello(banco: Banco, chave: str, token: str, nomes: list[str], avisar: Callable[[str], None],
                 buscar=_buscar_json, intervalo: float = 1800.0, contagem: Iterable[str] = ()) -> Fonte:
    async def coletar(agora: datetime) -> None:
        itens, faltando = await asyncio.to_thread(ler_quadros, chave, token, nomes, buscar, contagem)
        if faltando:
            avisar(f"trello: quadros não achados: {', '.join(faltando)}")
        if faltando and not itens:  # nenhum quadro achado (renomeado? chave de outra conta?): não apaga a foto nem marca coleta
            return
        antes = await asyncio.to_thread(banco.itens, "trello")
        await asyncio.to_thread(banco.registrar_coleta, "trello", itens, comparar(antes, itens), agora)

    return Fonte("trello", intervalo, coletar)
