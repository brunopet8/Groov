"""Prova real do Jev: 3 chamadas com um texto neutro. Mostra só o modelo, as probabilidades e o tempo (nunca a chave).
Uso: python scripts/provar_jev.py [caminho do .env]"""
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.conversa import jev  # noqa: E402
from src.conversa.segredos import ENV, ler_segredos  # noqa: E402

TEXTOS = ["abre a netflix e põe um desenho", "faz um relatório das vagas de emprego desta semana", "que horas são em Tóquio?"]
WS = ["Groov-vault", "MeuProjeto"]


async def main() -> None:
    chave = ler_segredos(Path(sys.argv[1]) if len(sys.argv) > 1 else ENV).get(jev.CHAVE)
    if not chave:
        print(f"{jev.CHAVE} ausente")
        return
    for texto in TEXTOS:
        t0 = time.perf_counter()
        try:
            r = await jev.enviar_http(jev.montar_corpo(texto, WS), chave)
            a = r.get("answers", {})
            print(f"{time.perf_counter() - t0:.2f}s modelo={r.get('model')} nivel={a.get('nivel', {}).get('probabilities')} "
                  f"ws={a.get('workspace', {}).get('choice')} | {texto}")
        except Exception as e:
            corpo = getattr(e, "read", lambda: b"")()[:300]
            print(f"{time.perf_counter() - t0:.2f}s ERRO {type(e).__name__} {getattr(e, 'code', '')} {corpo!r}")
    # escolher (visão): 3 opções neutras, como os textos de um player
    opcoes, estado = ["Início", "Pular anúncio", "Inscrever-se"], "o usuário quer pular o anúncio do vídeo"
    t0 = time.perf_counter()
    corpo = {"model": jev.MODELO, "state": estado, "questions": {"alvo": {
        "type": "choice", "instructions": "Qual destes textos da tela é o alvo descrito?",
        "criteria": {f"{i}: {o}": None for i, o in enumerate(opcoes)} | {jev.NENHUM: None}}}}
    try:
        r = await jev.enviar_http(corpo, chave)
        a = r.get("answers", {}).get("alvo", {})
        print(f"{time.perf_counter() - t0:.2f}s escolher: {a.get('choice')} probs={a.get('probabilities')}")
    except Exception as e:
        print(f"{time.perf_counter() - t0:.2f}s escolher ERRO {type(e).__name__} {getattr(e, 'code', '')}")


asyncio.run(main())
