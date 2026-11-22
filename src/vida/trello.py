"""Trello só leitura: lê os quadros escolhidos, compara com a última foto e acha o que vence ou está parado.

Nunca pede `desc` (descrição dos cartões: texto de terceiros raspado da web nos leads). Chave e token vão no
cabeçalho Authorization, nunca na URL.
"""
import json
import re
import unicodedata
import urllib.request
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from src.vida.banco import Evento

API = "https://api.trello.com/1"
CAMPOS_CARTAO = "name,idList,due,dueComplete,closed,dateLastActivity,badges"
LIMITE_NOME = 80
_CONCLUIDO = re.compile(r"conclu|feito|done|arquiv")  # cartão aqui já acabou, tenha ou não o prazo marcado como feito
_FIM_DE_FLUXO = re.compile(_CONCLUIDO.pattern + r"|aguard|esperando")  # parado nessas listas não é problema


def cabecalho(chave: str, token: str) -> dict[str, str]:
    return {"Authorization": f'OAuth oauth_consumer_key="{chave}", oauth_token="{token}"'}


def _buscar_json(url: str, cabecalhos: dict[str, str]) -> Any:
    pedido = urllib.request.Request(url, headers=cabecalhos)
    with urllib.request.urlopen(pedido, timeout=15) as resposta:
        return json.load(resposta)


def _normal(texto: str) -> str:
    """Sem maiúscula, acento e pontuação: "Empresa X — Prospecção" e "empresa x - prospeccao" ficam iguais."""
    sem_acento = unicodedata.normalize("NFKD", texto.casefold()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", sem_acento).strip()


def ler_quadros(chave: str, token: str, nomes: list[str], buscar=_buscar_json,
                contagem: Iterable[str] = ()) -> tuple[dict[str, dict], list[str]]:
    """(itens por id de cartão, nomes pedidos que não casaram com nenhum quadro aberto)."""
    cab = cabecalho(chave, token)
    quadros = {_normal(q["name"]): q for q in buscar(f"{API}/members/me/boards?filter=open&fields=name", cab)}
    itens: dict[str, dict] = {}
    faltando: list[str] = []
    so_contar = {_normal(n) for n in contagem}
    for nome in nomes:
        if not _normal(nome):
            continue
        quadro = quadros.get(_normal(nome))
        if quadro is None:
            faltando.append(nome)
            continue
        so_contagem = _normal(quadro["name"]) in so_contar  # TRELLO_QUADROS_CONTAGEM: leads contados, não cobrados
        url = f"{API}/boards/{quadro['id']}/lists?fields=name,closed&cards=open&card_fields={CAMPOS_CARTAO}"
        for lista in buscar(url, cab):
            if lista.get("closed"):
                continue
            for c in lista.get("cards", []):
                if c.get("closed"):
                    continue
                badges = c.get("badges") or {}
                feito = c["dueComplete"] if c.get("dueComplete") is not None else bool(badges.get("dueComplete"))
                itens[c["id"]] = {
                    "quadro": quadro["name"][:LIMITE_NOME], "lista": lista["name"][:LIMITE_NOME],
                    "nome": c["name"][:LIMITE_NOME], "prazo": c.get("due"), "feito": feito,
                    "atividade": c.get("dateLastActivity"),
                    "checks": [badges.get("checkItemsChecked", 0), badges.get("checkItems", 0)],
                    "contagem": so_contagem,
                }
    return itens, faltando


def comparar(antes: dict[str, dict], depois: dict[str, dict]) -> list[Evento]:
    """Eventos do que mudou entre as duas fotos. Primeira coleta (antes vazio) só cria a base."""
    if not antes:
        return []
    eventos: list[Evento] = []
    contagens: dict[str, list[int]] = {}  # quadro de prospecção -> [leads novos, leads que mudaram de etapa]
    for id_, c in depois.items():
        a = antes.get(id_)
        if c["contagem"]:
            if a is None:
                contagens.setdefault(c["quadro"], [0, 0])[0] += 1
            elif a["lista"] != c["lista"]:
                contagens.setdefault(c["quadro"], [0, 0])[1] += 1
            continue
        if a is None:
            eventos.append(Evento("trello", id_, "novo", f"Cartão novo no {c['quadro']}: {c['nome']}."))
            continue
        if a["lista"] != c["lista"]:
            eventos.append(Evento("trello", id_, "mudou", f"No {c['quadro']}, {c['nome']} foi para {c['lista']}."))
        if c["feito"] and not a["feito"]:
            eventos.append(Evento("trello", id_, "feito", f"{c['nome']} foi concluído."))
        feitos, total = c["checks"]
        if total > 0 and feitos > a["checks"][0]:
            eventos.append(Evento("trello", id_, "checklist", f"{c['nome']}: {feitos} de {total} itens feitos."))
    for quadro, (novos, movidos) in contagens.items():
        partes = []
        if novos:
            partes.append(f"{novos} lead novo" if novos == 1 else f"{novos} leads novos")
        if movidos:
            partes.append("1 mudou de etapa" if movidos == 1 else f"{movidos} mudaram de etapa")
        if partes:
            eventos.append(Evento("trello", f"contagem:{quadro}", "prospeccao", f"{quadro}: {' e '.join(partes)}."))
    return eventos


def _data(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def _ignorada(c: dict, ignoradas: set[tuple[str, str]]) -> bool:
    return (_normal(c["quadro"]), _normal(c["lista"])) in ignoradas


def _normais(ignoradas: Iterable[tuple[str, str]]) -> set[tuple[str, str]]:
    return {(_normal(q), _normal(l)) for q, l in ignoradas}


def parados(itens: dict[str, dict], agora: datetime, dias: int = 5, limite: int = 3,
            ignoradas: Iterable[tuple[str, str]] = ()) -> list[tuple[str, int]]:
    """(nome, dias parado) dos cartões abertos sem atividade há `dias` ou mais; os mais antigos primeiro.
    `ignoradas`: (quadro, lista) que o usuário mandou não cobrar."""
    achados, ignoradas = [], _normais(ignoradas)
    for c in itens.values():
        if (c["contagem"] or c["feito"] or not c["atividade"] or _FIM_DE_FLUXO.search(_normal(c["lista"]))
                or _ignorada(c, ignoradas)):
            continue
        parado = (agora - _data(c["atividade"])).days
        if parado >= dias:
            achados.append((c["nome"], parado))
    return sorted(achados, key=lambda x: -x[1])[:limite]


def prazos(itens: dict[str, dict], agora: datetime,
           ignoradas: Iterable[tuple[str, str]] = ()) -> dict[str, list[tuple[str, datetime]]]:
    """Prazos de cartões abertos por dia LOCAL (o Trello manda UTC): vencidos, hoje (ainda por vir) e amanhã."""
    saida: dict[str, list[tuple[str, datetime]]] = {"vencidos": [], "hoje": [], "amanha": []}
    ignoradas = _normais(ignoradas)
    for c in itens.values():
        if (c["contagem"] or c["feito"] or not c["prazo"] or _CONCLUIDO.search(_normal(c["lista"]))
                or _ignorada(c, ignoradas)):
            continue
        local = _data(c["prazo"]).astimezone(agora.tzinfo)
        if local < agora:
            saida["vencidos"].append((c["nome"], local))
        elif local.date() == agora.date():
            saida["hoje"].append((c["nome"], local))
        elif (local.date() - agora.date()).days == 1:
            saida["amanha"].append((c["nome"], local))
    for lista in saida.values():
        lista.sort(key=lambda x: x[1])
    return saida
