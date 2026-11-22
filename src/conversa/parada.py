"""Parada da tarefa em curso (Hermes ou laço do PC) por tchau, "vá embora", teto ou fim da conexão. Sem pipecat."""
from src.conversa.ajudante import ESTOUROU
from src.conversa.sessao import Sessao

MOTIVOS = {"tchau", "desligar", "teto", "conexao"}


async def parar(motivo: str, sessao: Sessao, ajudante, laco, falar) -> None:
    """Só a parada: dormir e avisar a janela ficam com quem chama. `laco` é None enquanto o bot não tem laço."""
    if motivo not in MOTIVOS:
        raise ValueError(f"motivo desconhecido: {motivo}")
    dono = sessao.dono
    if motivo == "tchau":
        if dono == "laco":  # a pesquisa do Hermes segue e o resultado fica guardado, como sempre
            laco.cancelar()
            sessao.cancelar_tarefa()
        return
    ajudante.cancelar()
    if laco is not None:
        laco.cancelar()
    sessao.cancelar_tarefa()
    if motivo == "teto" and dono == "hermes":
        await falar(ESTOUROU)
    elif motivo == "teto" and dono == "laco":  # estourou no meio de um passo longo: o laço já foi cancelado e não fala
        await falar(laco.fala_do_teto())
