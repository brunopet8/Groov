"""Ações da janela para o painel PROJETOS: listar, abrir, mandar prompt, abrir no app Claude (claude_app) e ditar. Sem pipecat."""
import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from src.conversa import chats, claude_app
from src.conversa.ajudante import CANCELADA, ESTOUROU, FALHOU
from src.conversa.cerebro_pc import achar_claude as _achar_claude
from src.conversa.mensagens import Recusada, ler_envio, ler_id
from src.conversa.sessao import Estado
from src.conversa.trabalho import comando_retomar

log = logging.getLogger("groov.chats")
RESPOSTA_MAX = 8000
DITADO_S = 30.0  # o microfone do chat desarma sozinho: voltar, dormir ou esquecer não manda a fala seguinte ao campo
ERROS = {FALHOU: "falhou", ESTOUROU: "demorou", CANCELADA: "cancelado"}
_tarefas: set[asyncio.Task] = set()


def criar_acoes_dos_chats(projetos: Callable[[], Path], mandar: Callable[[dict], Awaitable[None]], trabalho, sessao,
                          retomar, ditado: dict, claude=claude_app, achar_claude=_achar_claude,
                          agora=time.time, relogio=time.monotonic) -> dict[str, Callable]:
    async def _chat(id_: str) -> tuple[Path, Path | None]:
        arquivo = await asyncio.to_thread(chats.achar, projetos(), id_)
        if arquivo is None:
            raise Recusada("chat não encontrado")
        return arquivo, await asyncio.to_thread(chats.pasta, arquivo)

    async def listar(_d):
        ws = await asyncio.to_thread(chats.listar, projetos(), agora())
        await mandar({"projetos": chats.para_janela(ws)})

    async def abrir_chat(d):
        id_ = ler_id(d)
        arquivo, pasta = await _chat(id_)
        msgs = await asyncio.to_thread(chats.mensagens, arquivo)
        await mandar({"chat": {"id": id_, "workspace": pasta.name if pasta else "", "mensagens": msgs}})

    async def enviar(d):
        id_, texto = ler_envio(d)
        _, pasta = await _chat(id_)
        if pasta is None:
            raise Recusada("pasta do chat não existe")
        if trabalho.rodando:
            raise Recusada("ocupado")
        trabalho.rodando = True
        trabalho.comando = lambda prompt: comando_retomar(achar_claude() or "claude", id_, prompt)

        async def correr():
            try:
                saida = await trabalho.executar(texto, pasta)
                resposta = ({"id": id_, "erro": ERROS[saida]} if saida in ERROS
                            else {"id": id_, "texto": saida.strip()[:RESPOSTA_MAX]})
            except Exception as erro:  # só o tipo: nada do chat vai ao log
                log.warning("chat: envio caiu (%s)", type(erro).__name__)
                resposta = {"id": id_, "erro": "falhou"}
            finally:
                trabalho.rodando = False
            try:
                await mandar({"chat_resposta": resposta})
            except Exception as erro:  # conexão já fechada
                log.warning("chat: resposta não saiu (%s)", type(erro).__name__)
        t = asyncio.create_task(correr())
        _tarefas.add(t)
        t.add_done_callback(_tarefas.discard)

    # O painel grande "CLAUDE CODE" manda a área dele ao montar e ao mudar de tamanho, e "solto" ao sumir (fechou, dormiu).
    async def abrir_no_app(d):
        id_ = ler_id(d)
        await _chat(id_)
        if not await asyncio.to_thread(claude.abrir, id_):  # espera o app frio mostrar a janela (até ~10 s)
            raise Recusada("o app do Claude não abriu")

    async def area(d):
        a = claude_app.ler_area(d)
        await asyncio.to_thread(claude.area, a)

    async def solto(_d):
        await asyncio.to_thread(claude.soltar)

    async def ditar(_d):
        if sessao.estado is Estado.OCIOSO:
            await retomar(com_fala=False)
        elif sessao.estado is not Estado.CONVERSANDO:
            raise Recusada("está desligado")
        ditado.update(armado=True, usado=False, ate=relogio() + DITADO_S)

    return {"projetos": listar, "chat": abrir_chat, "chat_enviar": enviar, "chat_claude": abrir_no_app, "claude_area": area,
            "claude_solto": solto, "ditar": ditar}
