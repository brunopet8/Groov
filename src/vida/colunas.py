"""Colunas do Trello que o usuário manda não cobrar, por voz e com confirmação.

O cérebro só extrai o nome falado; quem acha a coluna, pergunta e guarda é o PC. O pedido fica pendente em Confirmacao
e só é guardado se a fala seguinte for um "sim" dentro do prazo: uma transcrição errada não grava nada sozinha.
"""
from dataclasses import dataclass

from src.vida.banco import Banco
from src.vida.trello import _normal

MAX_OPCOES = 3


@dataclass(frozen=True)
class Pedido:
    acao: str  # "ignorar" ou "voltar"
    quadro: str
    lista: str


def _achar(colunas: set[tuple[str, str]], lista: str, quadro: str) -> list[tuple[str, str]]:
    """Nome igual vence nome contido ("Vagas" não puxa "Vagas recusadas"); o quadro falado só filtra."""
    n, q = _normal(lista), _normal(quadro)
    if not n:
        return []
    candidatas = sorted(c for c in colunas if not q or q in _normal(c[0]))
    iguais = [c for c in candidatas if _normal(c[1]) == n]
    return iguais or [c for c in candidatas if n in _normal(c[1])]


def _nome(quadro: str, lista: str) -> str:
    return f"{lista}, do {quadro}"


def propor_coluna(banco: Banco, acao: str, lista: str, quadro: str = "") -> tuple[str, Pedido | None]:
    """(fala, pedido a confirmar). Ignorar casa com as listas da última coleta; voltar, com as já ignoradas."""
    ignoradas = banco.colunas_ignoradas()
    if acao == "voltar":
        achadas = _achar(ignoradas, lista, quadro)
        if not achadas:
            return f"A coluna {lista.strip()} não está ignorada, senhor.", None
    else:
        vistas = {(c["quadro"], c["lista"]) for c in banco.itens("trello").values() if not c["contagem"]}
        achadas = _achar(vistas, lista, quadro)
        if not achadas:
            return f"Não achei a coluna {lista.strip()} no seu Trello, senhor.", None
    if len(achadas) > 1:
        opcoes = "; ".join(_nome(q, l) for q, l in achadas[:MAX_OPCOES])
        return f"Achei mais de uma: {opcoes}. Qual delas, senhor?", None
    q, l = achadas[0]
    if acao == "voltar":
        return f"Voltar a cobrar a coluna {_nome(q, l)}? Confirma, senhor?", Pedido("voltar", q, l)
    if (q, l) in ignoradas:
        return f"Já não cobro a coluna {_nome(q, l)}, senhor.", None
    return f"Parar de cobrar prazo da coluna {_nome(q, l)}? Confirma, senhor?", Pedido("ignorar", q, l)


def guardar(banco: Banco, pedido: Pedido) -> str:
    if pedido.acao == "voltar":
        banco.voltar_coluna(pedido.quadro, pedido.lista)
        return f"Pronto, senhor. Volto a cobrar a coluna {_nome(pedido.quadro, pedido.lista)}."
    banco.ignorar_coluna(pedido.quadro, pedido.lista)
    return f"Pronto, senhor. Não cobro mais a coluna {_nome(pedido.quadro, pedido.lista)}."


class Confirmacao:
    """Um pedido pendente por vez; pegar() o consome, esteja ele no prazo ou não."""

    def __init__(self, prazo: float = 30):
        self._prazo = prazo
        self._pedido: Pedido | None = None
        self._ate = 0.0

    @property
    def prazo(self) -> float:
        return self._prazo

    def propor(self, pedido: Pedido, agora: float) -> None:
        self._pedido, self._ate = pedido, agora + self._prazo

    def pegar(self, agora: float) -> Pedido | None:
        pedido, self._pedido = self._pedido, None
        return pedido if pedido is not None and agora <= self._ate else None
