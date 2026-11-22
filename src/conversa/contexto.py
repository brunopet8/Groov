"""Corte do histórico enviado ao cérebro (trava os tokens de entrada)."""


def _usuario(mensagem) -> bool:
    return isinstance(mensagem, dict) and mensagem.get("role") == "user"


def cortar_historico(mensagens: list, limite: int = 8) -> list:
    """Últimas `limite` mensagens, começando num turno do usuário: o corte nunca separa a chamada de
    ferramenta (assistant) do resultado dela (tool), que o cérebro recusa."""
    inicio = max(len(mensagens) - limite, 0)
    while inicio < len(mensagens) and not _usuario(mensagens[inicio]):
        inicio += 1
    if inicio == len(mensagens):  # nenhum turno do usuário no recorte: volta ao último que houver
        inicio = max((i for i, m in enumerate(mensagens) if _usuario(m)), default=0)
    return mensagens[inicio:]
