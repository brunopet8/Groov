"""Triagem pelo Jev (TypeSafe): o pedido é conversa (nível 2, Haiku) ou trabalho (nível 3, Claude Code)? Sai do PC só o
texto do pedido e os nomes das pastas de workspace. Qualquer falha vira None (nível 2)."""
import asyncio
import json
import logging
import urllib.request
from dataclasses import dataclass

log = logging.getLogger("groov.jev")

CHAVE = "TYPESAFE_API_KEY"
URL = "https://api.typesafe.ai/v1/systemone"
MODELO = "jev-1.14.0"  # fixo: o que a prova real (13/11) devolveu; "jev-latest" muda sozinho
TETO_S = 1.0
LIMIAR = 0.7

CONVERSA = ("Pergunta, conversa, controlar o PC, abrir app ou site, música ou vídeo, timer, clima ou pesquisa rápida: "
            "resolve na hora, falando.")
TRABALHO = ("Trabalho longo que gera arquivo ou relatório, mexer num projeto, rodar uma skill, organizar o vault ou "
            "procurar vagas: precisa de tempo e de ferramentas.")


@dataclass
class Triagem:
    nivel: int
    workspace: str | None
    prob: float


def montar_corpo(texto: str, workspaces: list[str]) -> dict:
    perguntas = {"nivel": {"type": "choice", "instructions": "Que tipo de pedido é este, feito ao assistente GROOV?",
                           "criteria": {"conversa": CONVERSA, "trabalho": TRABALHO}}}
    if workspaces:
        perguntas["workspace"] = {"type": "choice", "instructions": "Se for trabalho, em qual pasta ele deve ser feito?",
                                  "criteria": {nome: None for nome in workspaces}}
    return {"model": MODELO, "state": texto, "questions": perguntas}


async def enviar_http(corpo: dict, chave: str) -> dict:
    def post() -> dict:
        req = urllib.request.Request(URL, data=json.dumps(corpo).encode("utf-8"), method="POST", headers={
            "Authorization": f"Bearer {chave}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=TETO_S + 1) as r:
            return json.loads(r.read())
    return await asyncio.to_thread(post)


async def triar(texto: str, workspaces: list[str], chave: str, enviar=None) -> Triagem | None:
    try:
        resposta = await asyncio.wait_for((enviar or enviar_http)(montar_corpo(texto, workspaces), chave), TETO_S)
        respostas = resposta["answers"]
        prob = float(respostas["nivel"]["probabilities"]["trabalho"])
        ws = (respostas.get("workspace") or {}).get("choice")
    except Exception as e:  # rede, HTTP, JSON torto ou demora: o Haiku atende
        log.warning("jev falhou: %s", type(e).__name__)
        return None
    return Triagem(3 if prob >= LIMIAR else 2, ws if isinstance(ws, str) else None, prob)


OPCOES_MAX = 40
OPCAO_MAX = 60  # caracteres de cada opção
NENHUM = "nenhum"


async def escolher(estado: str, instrucao: str, opcoes: list[str], chave: str, enviar=None) -> tuple[int, float] | None:
    """Escolha rápida entre opções (textos da tela, controles): (índice, probabilidade) ou None para "nenhum", erro ou
    demora. Sai do PC só `estado`, `instrucao` e as opções."""
    opcoes = opcoes[:OPCOES_MAX]
    if not chave or not opcoes:
        return None
    criterios = {f"{i}: {o[:OPCAO_MAX]}": None for i, o in enumerate(opcoes)} | {NENHUM: None}
    corpo = {"model": MODELO, "state": estado, "questions": {
        "alvo": {"type": "choice", "instructions": instrucao, "criteria": criterios}}}
    try:
        resposta = await asyncio.wait_for((enviar or enviar_http)(corpo, chave), TETO_S)
        alvo = resposta["answers"]["alvo"]
        escolha = alvo["choice"]
        if escolha == NENHUM or escolha not in criterios:
            return None
        return int(escolha.split(":", 1)[0]), float(alvo["probabilities"][escolha])
    except Exception as e:  # rede, HTTP, JSON torto ou demora: o próximo degrau resolve
        log.warning("jev escolher falhou: %s", type(e).__name__)
        return None
