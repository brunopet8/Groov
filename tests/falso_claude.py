"""Falso `claude` stream-json para tests/test_conversa_claude_voz.py: lê uma mensagem por linha e responde pelo texto dela.
Variáveis: FALSO_LOG (arquivo onde registra processo e mensagens recebidas), FALSO_MARCA (arquivo que faz "MORRE" valer só 1 vez)."""
import json
import os
import queue
import sys
import threading
import time

sys.stdin.reconfigure(encoding="utf-8")  # o Windows entregaria cp1252
sys.stdout.reconfigure(encoding="utf-8")
LOG = os.environ["FALSO_LOG"]


def registrar(**campos):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"pid": os.getpid(), **campos}, ensure_ascii=False) + "\n")


def enviar(**obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def delta(texto):
    enviar(type="stream_event", event={"type": "content_block_delta", "delta": {"type": "text_delta", "text": texto}})


def fim(erro=False):
    enviar(type="result", subtype="success", is_error=erro, usage={"output_tokens": 3})


registrar(abriu=True, argv=sys.argv[1:])
entrada = queue.Queue()  # uma thread lê o stdin: o falso precisa ver o pedido de interrupção no meio da resposta lenta


def ler():
    for linha in sys.stdin:
        entrada.put(json.loads(linha))
    entrada.put(None)


threading.Thread(target=ler, daemon=True).start()
while (msg := entrada.get()) is not None:
    if msg.get("type") == "control_request":
        registrar(controle=msg["request"]["subtype"])
        continue
    texto = msg["message"]["content"]
    registrar(recebeu=texto)
    if "MORRE_SEMPRE" in texto:
        sys.exit(1)
    if "MORRE" in texto and not os.path.exists(os.environ["FALSO_MARCA"]):
        open(os.environ["FALSO_MARCA"], "w").close()
        sys.exit(1)
    if texto.startswith("LENTO"):
        interrompida = False
        for i in range(200):
            delta(f"palavra{i} ")
            time.sleep(0.03)
            try:
                outra = entrada.get_nowait()
            except queue.Empty:
                continue
            if outra and outra.get("type") == "control_request":
                registrar(controle=outra["request"]["subtype"])
                interrompida = True
                break  # o CLI de verdade encerra a resposta com result de erro
        if interrompida and "_SAI" in texto:  # morre ao ser interrompido, sem result
            sys.exit(1)
        enviar(type="control_response", response={"subtype": "success"})
        fim(erro=interrompida)
        continue
    if "SILENTE" in texto:
        delta('<ferramenta>{"nome":"pc","args":{}}</ferramenta>')
    elif "TOOL" in texto:
        delta("Um instante. <ferr")
        delta('amenta>{"nome":"clima","args":{"cidade":"Rio"}}</ferr')
        delta("amenta>")
    else:
        delta("Claro, ")
        delta("senhor.")
    fim()
