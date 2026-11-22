"""Ajudante de tarefas: roda `hermes -z` (só toolset search, sem confirmações do Hermes) em segundo plano."""
import asyncio
import os
import shutil
import subprocess
import sys
from collections.abc import Iterable

INSTRUCAO = "Responda em até 3 frases curtas em português, para serem faladas: sem markdown, listas ou links."
VAZIO = "Não encontrei nada, senhor."
ESTOUROU = "A tarefa demorou demais, senhor. Cancelei."
FALHOU = "O Hermes falhou nessa tarefa, senhor."
CANCELADA = "Tarefa cancelada, senhor."
# o servidor roda sob pythonw: sem isso, cada programa de console (hermes, taskkill) abre uma janela na tela
SEM_JANELA = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def montar_comando(pedido: str, hermes: str = "hermes") -> list[str]:
    if hermes == "hermes":
        hermes = shutil.which("hermes") or hermes
    return [hermes, "-z", f"{INSTRUCAO}\n\nPedido: {pedido}", "-t", "search"]


def resumir(saida: str, limite: int = 400) -> str:
    texto = saida.strip()
    if not texto:
        return VAZIO
    if len(texto) <= limite:
        return texto
    corte = max(texto.rfind(c, 0, limite) for c in ".!?")
    return texto[:corte + 1] if corte > 0 else texto[:limite].rstrip()


def _matar(proc: asyncio.subprocess.Process) -> None:
    if proc.returncode is not None:
        return
    if sys.platform == "win32":  # o launcher do Hermes cria um filho: mata a árvore toda
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, creationflags=SEM_JANELA)
    try:
        proc.kill()
    except ProcessLookupError:
        pass


# chaves de modelo de privado/.env que nenhum processo filho herda (o Claude do plano, o Hermes, a sonda do PC)
CHAVES_DOS_MODELOS = frozenset({"GROQ_API_KEY", "GOOGLE_API_KEY"})


def ambiente_sem(nomes: Iterable[str]) -> dict[str, str]:
    """Cópia do ambiente sem as chaves de privado/.env: o Hermes e o XTTS não precisam (nem devem) delas."""
    tirar = set(nomes)
    return {k: v for k, v in os.environ.items() if k not in tirar}


class Ajudante:
    def __init__(self, comando=montar_comando, teto: float = 180.0, segredos: frozenset[str] = CHAVES_DOS_MODELOS):
        self.comando = comando
        self.teto = teto
        self.segredos = segredos
        self.cancelado = False
        self._proc: asyncio.subprocess.Process | None = None

    async def executar(self, pedido: str) -> str:
        self.cancelado = False
        env = {**ambiente_sem(self.segredos), "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
        proc = self._proc = await asyncio.create_subprocess_exec(
            *self.comando(pedido), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, env=env, creationflags=SEM_JANELA)
        try:
            saida, _ = await asyncio.wait_for(proc.communicate(), self.teto)
        except asyncio.TimeoutError:
            _matar(proc)
            await proc.wait()
            return ESTOUROU
        except asyncio.CancelledError:
            _matar(proc)
            raise
        finally:
            self._proc = None
        if self.cancelado:
            return CANCELADA
        if proc.returncode != 0:
            return FALHOU
        return resumir(saida.decode("utf-8", errors="replace"))

    def cancelar(self) -> None:
        self.cancelado = True
        if self._proc is not None:
            _matar(self._proc)
