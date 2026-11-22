"""Buscador: pesquisa pela busca do Google embutida no Gemini flash-lite (chamada separada do cérebro), no lugar do Hermes."""
import asyncio

from google import genai
from google.genai import types

from src.conversa.ajudante import CANCELADA, ESTOUROU, INSTRUCAO, resumir

CHAVE = "GOOGLE_API_KEY"  # nome em privado/.env: só a pesquisa usa o Google agora
MODELO_BUSCA = "gemini-3.5-flash-lite"  # só a busca; o cérebro é o Haiku (cerebro.py)
TETO_BUSCA = 20.0  # segundos; o Hermes levava ~15 s e tinha teto de 180
FALHOU = "A pesquisa falhou, senhor."


class Buscador:
    """Mesma interface do Ajudante: executar(pedido) -> str, cancelar(), cancelado."""

    def __init__(self, api_key: str | None = None, cliente=None, teto: float = TETO_BUSCA):
        self.cliente = cliente or genai.Client(api_key=api_key)
        self.teto = teto
        self.cancelado = False
        self._tarefa: asyncio.Task | None = None

    async def executar(self, pedido: str) -> str:
        self.cancelado = False
        config = types.GenerateContentConfig(
            system_instruction=INSTRUCAO, tools=[types.Tool(google_search=types.GoogleSearch())])
        # as citações vêm à parte (grounding_metadata): response.text já é texto limpo
        tarefa = self._tarefa = asyncio.ensure_future(self.cliente.aio.models.generate_content(
            model=MODELO_BUSCA, contents=pedido, config=config))
        try:
            resposta = await asyncio.wait_for(asyncio.shield(tarefa), self.teto)
            texto = resumir(resposta.text or "")  # dentro do try: resposta bloqueada ou SDK estranho também vira FALHOU
        except asyncio.TimeoutError:
            tarefa.cancel()
            return ESTOUROU
        except asyncio.CancelledError:
            tarefa.cancel()
            if self.cancelado:  # cancelar() cortou a chamada
                return CANCELADA
            raise
        except Exception:  # o detalhe do erro pode ter texto da resposta: não vai para lugar nenhum
            return CANCELADA if self.cancelado else FALHOU
        finally:
            self._tarefa = None
        return CANCELADA if self.cancelado else texto

    def cancelar(self) -> None:
        self.cancelado = True
        if self._tarefa is not None:
            self._tarefa.cancel()
