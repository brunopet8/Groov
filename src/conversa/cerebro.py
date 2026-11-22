"""O provedor do cérebro da conversa num lugar só: o Haiku do plano do usuário (Claude Code CLI, processo sempre aberto),
a criação e o que o resto do bot precisa saber dele."""
from src.conversa.claude_voz import ClaudeVozLLMService
from src.conversa.ferramentas import ESQUEMA

MODELO_CONVERSA = "haiku"  # alias do CLI; roda no plano, sem chave de API


def criar_llm(system: str) -> ClaudeVozLLMService:
    return ClaudeVozLLMService(system=system, ferramentas=ESQUEMA, modelo=MODELO_CONVERSA)


def ajuste(**campos):
    """O delta que vai no LLMUpdateSettingsFrame."""
    return ClaudeVozLLMService.Settings(**campos)


def e_do_cerebro(processador) -> bool:
    return isinstance(processador, ClaudeVozLLMService)
