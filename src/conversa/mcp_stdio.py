"""Cliente MCP mínimo por stdio (JSON-RPC, uma mensagem por linha): initialize + tools/call, nada mais. Escrito aqui em vez de usar o
pacote `mcp` (2.3.0 traria 9 pacotes novos, entre eles pywin32, para o venv que o master também usa; a sessão dele é presa a um
task group do anyio, ruim para uma conexão aberta sob demanda e mantida). Um processo só, aberto na primeira chamada e mantido.

Falha (teto, processo morto, ferramenta com erro) vira ErroSonda com mensagem fixa: o texto do erro de uma ferramenta pode trazer
conteúdo de página e nunca vai para o log. Depois de uma falha o processo é morto e a próxima chamada abre outro.
"""
import asyncio
import json
import logging
import subprocess

from src.conversa.ajudante import SEM_JANELA, _matar
from src.conversa.pc import ErroSonda

log = logging.getLogger("groov.mcp")

VERSAO_PROTOCOLO = "2025-06-18"
LIMITE_LINHA = 32 * 2**20  # uma resposta (snapshot) é uma linha só; o padrão do asyncio é 64 KB


# Categorias do erro de uma ferramenta, pelo trecho fixo que o Playwright usa; o texto do erro em si nunca sai daqui.
CATEGORIAS_ERRO = (("intercepts pointer", "intercepta_ponteiro"), ("not visible", "nao_visivel"), ("strict mode", "varios_alvos"),
                   ("timeout", "timeout"), ("not found", "ref_nao_encontrada"), ("not attached", "desanexado"),
                   ("not enabled", "desabilitado"), ("not stable", "instavel"), ("outside of the viewport", "fora_da_viewport"))


def categoria_do_erro(texto: str) -> str:
    t = texto.lower()
    return next((c for trecho, c in CATEGORIAS_ERRO if trecho in t), "outra")


class ErroFerramenta(ErroSonda):
    """Erro devolvido pela ferramenta (o servidor segue de pé): não mata o processo. `categoria` é um nome fixo de CATEGORIAS_ERRO."""

    def __init__(self, mensagem: str, categoria: str = "outra"):
        super().__init__(mensagem)
        self.categoria = categoria


class ClienteMCP:
    def __init__(self, comando: list[str], env: dict[str, str], teto: float, teto_abertura: float):
        self.comando, self.env, self.teto, self.teto_abertura = comando, env, teto, teto_abertura
        self._proc: asyncio.subprocess.Process | None = None
        self._id = 0
        self._trava = asyncio.Lock()

    async def _enviar(self, mensagem: dict) -> None:
        self._proc.stdin.write(json.dumps(mensagem).encode() + b"\n")
        await self._proc.stdin.drain()

    async def _receber(self, id_: int) -> dict:
        while True:  # notificações e pedidos do servidor (sem o nosso id) são ignorados
            linha = await self._proc.stdout.readline()
            if not linha:
                raise ErroSonda("mcp: servidor encerrou")
            try:
                m = json.loads(linha)
            except ValueError:
                continue
            if isinstance(m, dict) and m.get("id") == id_ and "method" not in m:
                return m

    async def _pedir(self, metodo: str, params: dict) -> dict:
        self._id += 1
        await self._enviar({"jsonrpc": "2.0", "id": self._id, "method": metodo, "params": params})
        return await self._receber(self._id)

    async def _abrir(self) -> None:
        try:
            self._proc = await asyncio.create_subprocess_exec(
                *self.comando, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=subprocess.DEVNULL,
                env=self.env, creationflags=SEM_JANELA, limit=LIMITE_LINHA)
        except OSError:
            raise ErroSonda("mcp: não consegui iniciar o servidor") from None
        r = await self._pedir("initialize", {"protocolVersion": VERSAO_PROTOCOLO, "capabilities": {},
                                             "clientInfo": {"name": "groov", "version": "1"}})
        if "result" not in r:
            raise ErroSonda("mcp: initialize recusado")
        await self._enviar({"jsonrpc": "2.0", "method": "notifications/initialized"})

    async def chamar(self, ferramenta: str, argumentos: dict | None = None) -> str:
        """Texto da resposta da ferramenta (os blocos `text` juntos). A primeira chamada tem o teto de abertura: a extensão
        pode levar segundos para conectar ao Chrome."""
        async with self._trava:
            primeira = self._proc is None
            try:
                return await asyncio.wait_for(self._chamar(ferramenta, argumentos or {}),
                                              self.teto_abertura if primeira else self.teto)
            except asyncio.TimeoutError:
                self._matar()
                raise ErroSonda(f"{ferramenta}: estourou o teto") from None
            except ErroFerramenta:
                raise  # o servidor segue de pé
            except (asyncio.CancelledError, ErroSonda, OSError, ValueError):
                self._matar()  # estado do protocolo desconhecido: recomeça na próxima
                raise

    async def _chamar(self, ferramenta: str, argumentos: dict) -> str:
        if self._proc is None:
            await self._abrir()
        r = await self._pedir("tools/call", {"name": ferramenta, "arguments": argumentos})
        res = r.get("result")
        if not isinstance(res, dict):
            raise ErroSonda(f"{ferramenta}: sem resultado")
        texto = "\n".join(str(b.get("text", "")) for b in res.get("content") or () if isinstance(b, dict) and b.get("type") == "text")
        if res.get("isError"):
            categoria = categoria_do_erro(texto)
            raise ErroFerramenta(f"{ferramenta}: erro da ferramenta ({categoria})", categoria)
        return texto

    def _matar(self) -> None:
        if self._proc is not None:
            _matar(self._proc)
            self._proc = None

    async def fechar(self) -> None:
        self._matar()

