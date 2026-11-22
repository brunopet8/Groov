"""Linhas de log por turno e por passo do laço. Só tipos, contagens e tempos: nunca fala, página ou resposta de modelo."""

RESULTADO_ACEITO, RESULTADO_RECUSADO, RESULTADO_INVALIDO = "aceito", "recusado", "inválido"


def linha_turno(modelo: str | None, entrada: int, saida: int) -> str:
    return f"turno: modelo={modelo or '?'} entrada={entrada} saida={saida}"


def linha_ferramenta(ferramenta: str, ok: bool) -> str:
    return f"turno: ferramenta={ferramenta} resultado={'ok' if ok else 'erro'}"


def linha_passo(numero: int, quem: str, sonda: str, chamada_s: float, leitura_s: float, resultado: str) -> str:
    return (f"passo do laço: n={numero} quem={quem} sonda={sonda} chamada={chamada_s:.2f}s "
            f"leitura={leitura_s:.2f}s resultado={resultado}")
