"""Painéis de resultado da janela (sem pipecat). O conteúdo de um painel nunca vai para o log."""
import math
import re
from dataclasses import dataclass
from urllib.parse import urlparse

TIPOS = ("texto", "lista", "numero", "passos")
PASSOS_NA_TELA = 6
_TEMPERATURA = re.compile(r"(-?\d+(?:[.,]\d+)?)\s*(°\s*C)")


@dataclass(frozen=True)
class Painel:
    id: str
    tipo: str
    titulo: str
    meta: str = ""
    corpo: str = ""
    itens: tuple[str, ...] = ()
    valor: str = ""
    unidade: str = ""
    fim: float | None = None  # epoch em segundos (time.time()): com ele o painel numero vira contagem regressiva


def para_janela(p: Painel) -> dict:
    """Dict da mensagem `painel`: tamanhos cortados, chaves vazias ausentes, `fim` só se for finito (JSON sem NaN)."""
    d = {"id": p.id, "tipo": p.tipo, "titulo": p.titulo[:80]}
    opcionais = {"meta": p.meta[:40], "corpo": p.corpo[:600], "itens": [i[:120] for i in p.itens[:8]],
                 "valor": p.valor[:12], "unidade": p.unidade[:8]}
    d.update({k: v for k, v in opcionais.items() if v})
    if p.fim is not None and math.isfinite(p.fim):
        d["fim"] = p.fim
    return d


def de_pesquisa(pedido: str, resultado: str) -> Painel:
    return Painel("pesquisa", "texto", pedido, corpo=resultado)


def de_clima(texto: str) -> Painel:
    m = _TEMPERATURA.search(texto)
    if not m:
        return Painel("clima", "texto", "CLIMA", corpo=texto)
    return Painel("clima", "numero", "CLIMA", corpo=texto, valor=m.group(1), unidade="°C")


def de_briefing(tipo: str, textos: list[str]) -> Painel:
    return Painel(tipo, "lista", tipo.upper(), itens=tuple(textos))


def de_vida(consulta: str, texto: str) -> Painel:
    return Painel("vida", "texto", consulta, corpo=texto)


def de_timer(desligar: bool, fim: float) -> Painel:
    return Painel("timer-desligar" if desligar else "timer", "numero", "DESLIGAR O PC" if desligar else "TIMER", fim=fim)


def descrever_passo(passo: dict) -> str:
    """Só a ação e o alvo público (host do site, nome do app): nunca texto digitado, nome de elemento, pergunta ou URL inteira."""
    acao = passo.get("acao")
    if acao == "abrir_site":
        url = str(passo.get("url") or "")
        try:
            host = urlparse(url if "//" in url else "//" + url).hostname or ""
        except ValueError:  # URL malformada (ex.: "//[x"): fica só a ação
            host = ""
        return f"abrir site {host.removeprefix('www.')}".strip()
    if acao == "abrir_app":
        return f"abrir app {passo.get('app') or ''}".strip()
    if acao == "rolar":
        return f"rolar {passo['direcao']}" if passo.get("direcao") in ("cima", "baixo", "up", "down") else "rolar"
    return acao if acao in ("clicar", "digitar", "buscar", "perguntar", "responder", "desistir") else "passo"


def de_passos(pedido: str, passos: list[str], desfecho: tuple[str, str] | None = None) -> Painel:
    meta, corpo = desfecho or ("", "")
    return Painel("pc", "passos", pedido, meta=meta, corpo=corpo, itens=tuple(passos[-PASSOS_NA_TELA:]))
