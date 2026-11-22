"""Mensagens da janela para o servidor: validação e despacho, sem pipecat."""
import logging
from collections.abc import Awaitable, Callable

from src.conversa.chats import valido

log = logging.getLogger("groov.mensagens")  # ponte do servidor.configurar_log; sem loguru, roda nos dois venvs

TEXTO_MAX = 2000
OPCAO_MAX = 80


class Recusada(Exception):
    """str(erro) é o motivo curto que vai na resposta de erro."""


def criar_despacho(acoes: dict[str, Callable[[object], Awaitable[None]]],
                   responder: Callable[[object, dict], Awaitable[None]],
                   recusar: Callable[[object, str], Awaitable[None]]) -> Callable[[object], Awaitable[None]]:
    async def despachar(msg) -> None:
        acao = acoes.get(msg.type)
        if acao is None:
            log.warning("janela: tipo desconhecido")  # o tipo vem de fora: nunca vai ao log
            await recusar(msg, "tipo desconhecido")
            return
        try:
            try:
                await acao(msg.data)
            except Recusada as erro:
                await recusar(msg, str(erro))
            except Exception as erro:  # só o tipo da exceção: a mensagem pode trazer o que o usuário digitou
                log.warning(f"janela: {msg.type} falhou ({type(erro).__name__})")
                await recusar(msg, "falhou")
            else:
                await responder(msg, {"ok": True})
        except Exception as erro:  # canal fechado ao responder: não sobe para o laço de eventos do pipecat
            log.warning(f"janela: resposta não saiu ({type(erro).__name__})")
    return despachar


def _campo(d: object, nome: str) -> object:
    if not isinstance(d, dict) or nome not in d:
        raise Recusada(f"falta {nome}")
    return d[nome]


def ler_texto(d: object) -> str:
    texto = _campo(d, "texto")
    if not isinstance(texto, str) or not texto.strip() or len(texto) > TEXTO_MAX:
        raise Recusada("texto inválido")
    return texto.strip()


def ler_id(d: object) -> str:
    id_ = _campo(d, "id")
    if not valido(id_):
        raise Recusada("id inválido")
    return id_


def ler_envio(d: object) -> tuple[str, str]:
    return ler_id(d), ler_texto(d)


def ler_resposta(d: object) -> tuple[str, str]:
    id_, opcao = _campo(d, "id"), _campo(d, "opcao")
    if not (isinstance(id_, str) and id_ and isinstance(opcao, str) and opcao and len(opcao) <= OPCAO_MAX):
        raise Recusada("resposta inválida")
    return id_, opcao


def ler_ligada(d: object) -> bool:
    ligada = _campo(d, "ligada")
    if not isinstance(ligada, bool):
        raise Recusada("ligada inválido")
    return ligada
