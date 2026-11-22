"""Fechar e minimizar janelas por comando direto (fase 6), sem modelo no meio. A janela vem do PC (primeiro plano ou o
app citado), nunca da fala; quem decide se pode é `regras_pc.decidir_janela`."""
from dataclasses import dataclass

from src.conversa.pc import APPS_PC
from src.conversa.regras_pc import decidir_janela

FRASE_FEITO = "Feito, senhor."
FRASE_JANELA_PROIBIDA = "Não mexo nessa janela, senhor."
FRASE_JANELA_NAO_ACHEI = "Não achei a janela, senhor."
FRASE_JANELA_QUAL = "Qual janela, senhor? Diga o app."
FRASE_JANELA_FALHOU = "Não consegui, senhor."
FRASE_NAO_FECHEI = "Certo, senhor. Não fechei."


@dataclass(frozen=True)
class PedidoJanela:
    """Pergunta pendente "fecho mesmo?"; o "sim" vale para esta janela."""
    hwnd: int


def frase_abas(abas: int) -> str:  # sem "confirma" no fim: o eco da pergunta não pode confirmar
    return f"O Chrome tem {abas} abas abertas. Fecho a janela inteira, senhor?"


async def _achar(backend, proibidos, acao: str, alvo: str):
    """(hwnd, info) da janela do pedido: a da frente se casar com o alvo (sem alvo: qualquer uma que não seja proibida); senão a única do alvo
    (sem alvo: a única das janelas que a sonda lista, fora o GROOV, que fica em tela cheia quando se fala). Aba é sempre do
    Chrome. Mais de uma candidata: (None, None) e quem chama pergunta qual."""
    alvo = "chrome" if acao == "fechar_aba" else alvo.strip().lower()
    alvo = APPS_PC.get(alvo, (alvo,))[0].lower()  # "bloco de notas" é o processo notepad
    fg = await backend.primeiro_plano()
    info = await backend.info_janela(fg) if fg else None
    nunca = {p.lower() for p in proibidos}
    do_pedido = (lambda i: i.processo.lower() == alvo) if alvo else (lambda i: i.processo.lower() not in nunca)
    if info and not info.groov and do_pedido(info):
        return fg, info, False
    achadas = []
    for h in sorted(await backend.janelas(alvo)):
        i = await backend.info_janela(h)
        if i and not i.groov and do_pedido(i):
            achadas.append((h, i))
    if len(achadas) == 1:
        return (*achadas[0], False)
    if not achadas and not alvo and info:
        return fg, info, False  # nada a que cair: as regras recusam a da frente (GROOV ou processo proibido)
    return None, None, len(achadas) > 1


async def agir_na_janela(backend, proibidos, acao: str, alvo: str = "", hwnd: int | None = None,
                         confirmado: bool = False) -> tuple[list[str], PedidoJanela | None]:
    """(falas, pergunta pendente). `hwnd` + `confirmado`: o "sim" à pergunta; a janela é lida e decidida de novo."""
    if hwnd is None:
        hwnd, info, varias = await _achar(backend, proibidos, acao, alvo)
        if hwnd is None:
            return [FRASE_JANELA_QUAL if varias else FRASE_JANELA_NAO_ACHEI], None  # quem fala diz o app e repete
    else:
        info = await backend.info_janela(hwnd)
    d = decidir_janela(acao, info.processo if info else "", info.abas if info else 0, bool(info and info.groov),
                       proibidos, confirmado)
    if d.tipo == "recusar":
        return [FRASE_JANELA_PROIBIDA], None
    if d.tipo == "perguntar":
        return [frase_abas(int(d.valor))], PedidoJanela(hwnd)
    agir = {"fechar": backend.fechar, "fechar_aba": backend.fechar_aba, "minimizar": backend.minimizar}[acao]
    return [FRASE_FEITO if await agir(hwnd) else FRASE_JANELA_FALHOU], None
