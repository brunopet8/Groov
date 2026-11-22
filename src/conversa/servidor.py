"""Servidor da conversa do GROOV: serve a janela (Reactor) e a sinalização WebRTC. Só escuta em 127.0.0.1.

A lógica das rotas /api/offer vem de pipecat/runner/run.py (1.13.0, BSD-2), sem o /client pronto.
"""
import asyncio
import functools
import logging
import os
import re
import sqlite3
import sys
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from loguru import logger
from pipecat.runner.types import SmallWebRTCRunnerArguments
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
from pipecat.transports.smallwebrtc.request_handler import (
    IceCandidate,
    SmallWebRTCPatchRequest,
    SmallWebRTCRequest,
    SmallWebRTCRequestHandler,
)

from src.conversa import claude_app, tela
from src.conversa.segredos import ler_segredos
from src.vida.banco import Banco
from src.vida.coletor import Coletor, descrever_erro, fonte_trello
from src.vida.trava import travar

HOST, PORTA = "127.0.0.1", tela.porta()
RAIZ = Path(__file__).resolve().parents[2]
LOG = RAIZ / "conversa.log"  # só quando roda sem console (pythonw, atalho de início)
JANELA = Path(__file__).parent / "janela"
DESIGN_SYSTEM = RAIZ / "ROSE HUD Design System"
DS_ARQUIVOS = ("styles.css", "_ds_bundle.js")
DS_PASTAS = (("tokens",), ("assets", "fonts"))  # o resto da pasta (componentes, referências, ...) não é servido
ICONES_CDN = "https://unpkg.com/lucide-static@0.460.0/icons/"  # o que o bundle traz; servido como "/janela/icones/"
CSP = "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self' blob: mediastream:"
ESPERA_BOT_ANTIGO = 15  # s para o pipeline antigo largar a GPU antes de abrir o novo


def _arquivo(pasta: Path, caminho: str) -> Path:
    alvo = (pasta / caminho).resolve()
    if not alvo.is_relative_to(pasta.resolve()) or not alvo.is_file():
        raise HTTPException(404)
    return alvo


def _logar_falha(tarefa: asyncio.Task) -> None:
    if not tarefa.cancelled() and tarefa.exception():  # sem isto a falha do pipeline some em silêncio
        logger.opt(exception=tarefa.exception()).error("pipeline da conversa falhou")


def _logar_coletor(tarefa: asyncio.Task) -> None:
    if not tarefa.cancelled() and tarefa.exception():  # só o tipo: a mensagem do erro pode trazer conteúdo
        logger.error(f"coletor parou ({descrever_erro(tarefa.exception())})")


def criar_app(bot=None, porta: int = PORTA, coletor: Coletor | None = None) -> FastAPI:
    """bot(runner_args) é a corrotina do pipeline; None usa src.conversa.bot.bot (importado na 1ª conexão).
    coletor (só o main() passa) roda como tarefa enquanto o servidor estiver de pé."""
    hosts = {f"127.0.0.1:{porta}", f"localhost:{porta}"}
    origens = {f"http://{h}" for h in hosts}

    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI):
        # create_task sem await: a porta abre na hora (o atalho de início desiste em 90 s)
        tarefa = asyncio.create_task(coletor.rodar()) if coletor else None
        if tarefa:
            tarefa.add_done_callback(_logar_coletor)
        try:
            yield
        finally:
            if tarefa:
                tarefa.cancel()
                try:
                    await tarefa
                except (asyncio.CancelledError, Exception):  # se morreu sozinha, _logar_coletor já registrou o tipo
                    pass

    app = FastAPI(lifespan=ciclo_de_vida)
    handler = SmallWebRTCRequestHandler()
    atual: dict[str, asyncio.Task | None] = {"bot": None}

    @app.middleware("http")
    async def so_localhost(request: Request, call_next):
        # Barra DNS rebinding e páginas de outros sites mandando ofertas para cá.
        origem = request.headers.get("origin")
        if request.headers.get("host") not in hosts or (origem is not None and origem not in origens):
            return JSONResponse({"erro": "acesso negado"}, status_code=403)
        resposta = await call_next(request)
        resposta.headers["Content-Security-Policy"] = CSP
        resposta.headers["Cache-Control"] = "no-cache"  # 14/11: a janela rodava JS antigo do cache; revalida (304 é barato)
        return resposta

    versao = str(int(time.time()))  # 14/11: o no-cache não alcança o JS que já estava no cache; o endereço novo, sim

    @app.get("/", include_in_schema=False)
    async def raiz():
        pagina = (JANELA / "index.html").read_text(encoding="utf-8")
        pagina = re.sub(r'((?:src|href)="/(?:janela|ds)/[^"?]+\.(?:js|css))"', rf'\1?v={versao}"', pagina)
        return HTMLResponse(pagina.replace("<title>GROOV</title>", f"<title>{tela.titulo_da_janela(porta)}</title>"))

    @app.get("/janela/{caminho:path}", include_in_schema=False)
    async def janela(caminho: str):
        return FileResponse(_arquivo(JANELA, caminho))

    @app.get("/ds/{caminho:path}", include_in_schema=False)
    async def design_system(caminho: str):
        alvo = _arquivo(DESIGN_SYSTEM, caminho)
        relativo = alvo.relative_to(DESIGN_SYSTEM.resolve())  # a lista vale para o caminho já resolvido, não para o texto
        if relativo.as_posix() not in DS_ARQUIVOS and not any(relativo.parts[:len(p)] == p for p in DS_PASTAS):
            raise HTTPException(404)
        if relativo.as_posix() == "_ds_bundle.js":  # nada da internet: o Icon do bundle busca os SVG aqui
            texto = alvo.read_text(encoding="utf-8").replace(ICONES_CDN, "/janela/icones/")
            return Response(texto, media_type="text/javascript")
        return FileResponse(alvo)

    async def encerrar_anterior():
        """Uma conexão só: janela recarregada ou 2ª aba derruba a antiga e espera o pipeline dela acabar."""
        await handler.close()
        antigo = atual["bot"]
        if antigo and not antigo.done():
            try:
                await asyncio.wait_for(asyncio.shield(antigo), ESPERA_BOT_ANTIGO)
            except (asyncio.TimeoutError, Exception):
                antigo.cancel()

    @app.post("/api/offer")
    async def offer(request: SmallWebRTCRequest):
        if not request.pc_id:  # a janela sempre abre uma conexão nova, sem renegociar
            await encerrar_anterior()

        async def ao_conectar(conexao: SmallWebRTCConnection):
            funcao = bot
            if funcao is None:
                from src.conversa.bot import bot as funcao
            resultado = funcao(SmallWebRTCRunnerArguments(webrtc_connection=conexao, body=request.request_data))
            if asyncio.iscoroutine(resultado):
                atual["bot"] = asyncio.create_task(resultado)
                atual["bot"].add_done_callback(_logar_falha)

        return await handler.handle_web_request(request=request, webrtc_connection_callback=ao_conectar)

    @app.patch("/api/offer")
    async def ice_candidate(request: SmallWebRTCPatchRequest):
        await handler.handle_patch_request(request)
        return {"status": "success"}

    return app


def criar_encerrar(servidor_uvicorn, fechar_janela=tela.fechar) -> Callable[[], None]:
    """Fecha a janela e manda o uvicorn parar; a falha da janela não pode deixar o servidor de pé."""
    def encerrar() -> None:
        try:
            fechar_janela()
        except Exception:
            logger.error("encerrar: não consegui fechar a janela")
        finally:
            servidor_uvicorn.should_exit = True

    return encerrar


def garantir_saida() -> bool:
    """O atalho de início roda pythonw, sem stdout/stderr (None): o uvicorn quebra em sys.stdout.isatty().
    Manda tudo para um .log; True se precisou."""
    if sys.stdout is not None and sys.stderr is not None:
        return False
    log = open(LOG, "a", encoding="utf-8", buffering=1)
    sys.stdout = sys.stdout or log
    sys.stderr = sys.stderr or log
    return True


# Módulos do pipecat cujos avisos e depurações gravam o texto falado ou o SYSTEM (que leva o perfil do usuário).
MODULOS_COM_TEXTO = (
    "pipecat.services.tts_service", "pipecat.services.openai.tts", "pipecat.services.llm_service",
    "pipecat.services.openai.base_llm", "pipecat.processors.frameworks.rtvi", "pipecat.transports.smallwebrtc",
    "pipecat.pipeline.worker",
)


def sem_texto(record) -> bool:
    """Filtro do loguru: nesses módulos, em qualquer nível, só fica o nível e o módulo; nunca o texto nem o traceback."""
    nome = record["name"] or ""
    if nome.startswith(MODULOS_COM_TEXTO):
        record["message"] = f"{record['level'].name} em {nome} (texto omitido)"
        record["exception"] = None
    return True


class PonteLog(logging.Handler):
    """Leva o `logging` do controle do PC (groov.laco, groov.pc, groov.timers, ...) ao loguru: sem isto os INFO somem
    e só os WARNING chegam, pelo stderr. Só a mensagem, nunca o traceback: ele pode trazer conteúdo de janela."""

    def emit(self, record: logging.LogRecord) -> None:
        logger.log(record.levelname if record.levelname in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL") else "INFO",
                   record.getMessage())


def configurar_log(destino, nivel: str | None = None) -> None:
    """Um handler só, sem variáveis locais nos erros (diagnose) e sem texto dos módulos acima. GROOV_LOG só para medir."""
    logger.remove()
    logger.add(destino, level=nivel or os.environ.get("GROOV_LOG", "INFO"), diagnose=False, backtrace=False,
               filter=sem_texto)
    groov = logging.getLogger("groov")  # decisão provisória (a revisar): ponte só para os loggers "groov.*"
    groov.handlers = [h for h in groov.handlers if not isinstance(h, PonteLog)] + [PonteLog()]
    groov.setLevel(logging.DEBUG)  # quem filtra o nível é o loguru
    groov.propagate = False


def montar_coletor(raiz: Path = RAIZ, avisar: Callable[[str], None] = logger.warning) -> Coletor | None:
    """Coletor do Trello com as chaves de privado/.env. A trava garante um coletor só: um 2º servidor (teste, medição)
    só lê o banco. Sem chave, nada é coletado e o GROOV responde com o que já está no banco. Se o banco não abre
    (privado/ ausente, arquivo corrompido), devolve None: a conversa sobe sem o contexto de vida."""
    privado = raiz / "privado"
    try:
        banco = Banco(privado / "vida.db")
        trava = travar(privado / "coletor.lock")
    except (OSError, sqlite3.Error) as erro:
        avisar(f"coletor: banco não abriu ({descrever_erro(erro)}); sem coletor")
        return None
    if trava is None:
        avisar("coletor: já roda em outro servidor; este só lê o banco")
        return Coletor(banco, [], avisar)
    segredos = ler_segredos(privado / ".env")
    chave, token, quadros = (segredos.get(n) for n in ("TRELLO_KEY", "TRELLO_TOKEN", "TRELLO_QUADROS"))
    fontes = []
    if chave and token and quadros:
        separar = lambda texto: [q.strip() for q in (texto or "").split(",") if q.strip()]  # noqa: E731
        fontes.append(fonte_trello(banco, chave, token, separar(quadros), avisar,
                                   contagem=separar(segredos.get("TRELLO_QUADROS_CONTAGEM"))))
    else:
        avisar("coletor: Trello sem chave no .env")
    coletor = Coletor(banco, fontes, avisar)
    coletor.trava = trava  # o arquivo travado precisa ficar aberto enquanto o servidor viver
    return coletor


def main():
    garantir_saida()
    configurar_log(sys.stderr)  # com e sem console: o loguru só põe o handler padrão se já houver stderr
    import uvicorn

    from src.conversa.bot import bot  # importa agora: na 1ª conexão atrasaria a resposta em ~5 s

    tela.ativar(PORTA)  # acordar mostra a janela no 2º monitor, dormir a esconde
    claude_app.ativar(PORTA)  # o painel CLAUDE CODE encaixa o app desktop sobre a janela
    coletor = montar_coletor()
    # o bot nasce depois do server; a lambda lê encerrar_tudo só quando o botão é apertado
    app = criar_app(bot=functools.partial(bot, coletor=coletor, encerrar_tudo=lambda: encerrar_tudo()), coletor=coletor)
    server = uvicorn.Server(uvicorn.Config(app, host=HOST, port=PORTA))
    encerrar_tudo = criar_encerrar(server)
    server.run()


if __name__ == "__main__":
    main()
