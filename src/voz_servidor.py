"""Servidor de voz local do GROOV: Qwen3-TTS (faster-qwen3-tts) com a voz clonada, falando o protocolo da API de
voz da OpenAI (POST /v1/audio/speech); GET / diz o motor ({"motor": "qwen"}). Só escuta em 127.0.0.1; o Hermes usa via tts.openai.base_url.
POST /desligar encerra o processo (comando "GROOV, desligar") e libera a placa de vídeo."""
import io
import itertools
import json
import logging
import os
import sys
import threading
import time
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LOG = RAIZ / "voz_servidor.log"
HOST, PORTA = "127.0.0.1", 8765
CHAVE = "Bearer local"  # não é segredo: só barra páginas da web, que não mandam este cabeçalho sem permissão
TAXA = 24000  # o Qwen3-TTS gera mono 24 kHz
MAX_CARACTERES = 2000  # igual a tts.openai.max_text_length no Hermes
ESPERA_MAX = 30  # segundos: teto para esperar a despedida antes de desligar
QWEN_MODELO = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
QWEN_COMMIT = "5d83992436eae1d760afd27aff78a71d676296fc"  # pesos Apache-2.0 conferidos
QWEN_PEDACO = 8  # passos de codec por pedaço (~0,7 s de áudio): 1º som em ~0,5 s e gera mais rápido que a fala
MOTOR = "qwen"


def conferir_taxa(taxa):
    """O servidor anuncia 24 kHz: outra taxa sairia com a altura errada, sem erro nenhum."""
    if taxa != TAXA:
        raise RuntimeError(f"o motor devolveu {taxa} Hz, mas o servidor anuncia {TAXA} Hz")


def garantir_saida():
    """O atalho de início roda pythonw, sem stdout/stderr (None): a barra tqdm do Hugging Face quebra ao escrever.
    Manda o que sairia no console para o log."""
    if sys.stdout is None or sys.stderr is None:
        log = open(LOG, "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stdout or log
        sys.stderr = sys.stderr or log


def para_pcm16(audio):
    """Pedaço float (numpy, -1..1) -> bytes PCM 16-bit mono."""
    import numpy as np

    return (np.clip(np.asarray(audio, dtype=np.float32).reshape(-1), -1, 1) * 32767).astype("<i2").tobytes()


def ler_pedido(corpo):
    """(texto, formato) de um pedido /v1/audio/speech; ValueError se inválido."""
    try:
        dados = json.loads(corpo)
    except ValueError:
        raise ValueError("JSON inválido") from None
    texto = dados.get("input") if isinstance(dados, dict) else None
    if not isinstance(texto, str) or not texto.strip():
        raise ValueError("campo 'input' vazio")
    if len(texto) > MAX_CARACTERES:
        raise ValueError(f"texto acima de {MAX_CARACTERES} caracteres")
    formato = dados.get("response_format", "wav")
    if formato not in ("pcm", "wav"):
        raise ValueError(f"formato '{formato}' não suportado: use pcm ou wav")
    return texto.strip(), formato


def hora_de_desligar(agora, pedido_em, inicio_ultima_fala, ativos):
    """Desliga quando a fala que começou depois do pedido (a despedida) terminou, ou no teto."""
    return agora - pedido_em >= ESPERA_MAX or (inicio_ultima_fala > pedido_em and ativos == 0)


def _wav(pcm):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TAXA)
        w.writeframes(pcm)
    return buf.getvalue()


class _Servidor(ThreadingHTTPServer):
    allow_reuse_address = False  # no Windows, SO_REUSEADDR deixaria uma 2ª cópia ocupar a mesma porta

    def handle_error(self, request, client_address):
        logging.exception("erro atendendo %s", client_address)  # sem console (pythonw), vai para o log


def criar_servidor(falar, desligar, porta=PORTA, motor=MOTOR):
    """falar(texto) -> iterável de bytes PCM 16-bit mono; desligar() atende POST /desligar; GET / diz o motor."""

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"  # resposta em pedaços (chunked) para o 1º som sair logo
        timeout = 30  # cliente parado não prende o modelo

        def do_GET(self):
            # o bot confere qual motor está na porta (um servidor antigo esquecido ligado não pode falar no lugar do Qwen)
            self._responder(200, json.dumps({"motor": motor}).encode(), "application/json")

        def do_POST(self):
            corpo = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            porta_real = self.server.server_address[1]
            if self.headers.get("Host") not in (f"127.0.0.1:{porta_real}", f"localhost:{porta_real}"):
                return self._responder(403, "host não permitido".encode())
            if self.headers.get("Authorization") != CHAVE:
                return self._responder(401, "chave ausente".encode())
            if self.path == "/desligar":
                desligar()
                return self._responder(202, "desligando".encode())
            if self.path != "/v1/audio/speech":
                return self._responder(404, "caminho desconhecido".encode())
            try:
                texto, formato = ler_pedido(corpo)
            except ValueError as erro:
                return self._responder(400, str(erro).encode())
            estado = self.server.estado
            estado["ativos"] += 1
            estado["inicio"] = time.monotonic()
            try:
                self._falar(texto, formato)
            finally:
                estado["ativos"] -= 1

        def _falar(self, texto, formato):
            try:
                partes = iter(falar(texto))
                primeira = b"".join(partes) if formato == "wav" else next(partes, b"")
            except Exception:
                logging.exception("falha ao gerar voz")
                return self._responder(500, "falha ao gerar voz".encode())
            if formato == "wav":
                return self._responder(200, _wav(primeira), "audio/wav")
            self.send_response(200)
            self.send_header("Content-Type", f"audio/pcm; rate={TAXA}")
            self.send_header("X-Audio-Sample-Rate", str(TAXA))
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            for parte in itertools.chain([primeira], partes):
                if parte:
                    self.wfile.write(b"%x\r\n%s\r\n" % (len(parte), parte))
                    self.wfile.flush()
            self.wfile.write(b"0\r\n\r\n")

        def _responder(self, codigo, corpo, tipo="text/plain; charset=utf-8"):
            self.send_response(codigo)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def log_message(self, formato, *args):
            logging.info(formato, *args)

    servidor = _Servidor((HOST, porta), Handler)
    servidor.estado = {"ativos": 0, "inicio": 0.0}
    return servidor


def carregar_qwen():
    """Carrega o Qwen3-TTS acelerado (faster-qwen3-tts, CUDA graphs) com a voz de hermes/voz/ref_qwen.wav + .txt;
    devolve falar(texto) que entrega o áudio em pedaços enquanto gera."""
    os.environ.setdefault("HF_HUB_OFFLINE", "1")  # pesos já estão no cache; nada de rede
    from faster_qwen3_tts import FasterQwen3TTS
    from huggingface_hub import snapshot_download

    ref = RAIZ / "hermes" / "voz" / "ref_qwen.wav"
    transcricao = ref.with_suffix(".txt")  # com clonagem por exemplo (ICL) o texto tem de ser exatamente o falado
    if not ref.exists() or not transcricao.exists():
        raise SystemExit("faltam hermes/voz/ref_qwen.wav e ref_qwen.txt (a transcrição exata do áudio)")
    ref_texto = transcricao.read_text(encoding="utf-8").strip()
    if not ref_texto:
        raise SystemExit("hermes/voz/ref_qwen.txt está vazio: precisa da transcrição exata do áudio")
    modelo = FasterQwen3TTS.from_pretrained(snapshot_download(QWEN_MODELO, revision=QWEN_COMMIT))
    modelo.warmup()
    trava = threading.Lock()  # o modelo atende um pedido por vez

    def falar(texto):
        with trava:
            for audio, taxa, _tempos in modelo.generate_voice_clone_streaming(
                    text=texto, language="Portuguese", ref_audio=str(ref), ref_text=ref_texto, chunk_size=QWEN_PEDACO):
                conferir_taxa(taxa)
                yield para_pcm16(audio)

    for _ in falar("Pronto."):  # aquece: a 1ª geração real captura/ajusta o que o warmup não cobre
        pass
    return falar


def main():
    garantir_saida()
    logging.basicConfig(filename=LOG, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    modelo = {}

    def desligar():
        pedido = time.monotonic()

        def esperar():
            while not hora_de_desligar(time.monotonic(), pedido, servidor.estado["inicio"], servidor.estado["ativos"]):
                time.sleep(0.5)
            servidor.shutdown()

        threading.Thread(target=esperar, daemon=True).start()

    try:
        # reserva a porta antes de carregar: uma 2ª cópia falha aqui, sem ocupar a placa
        servidor = criar_servidor(lambda texto: modelo["falar"](texto), desligar)
        modelo["falar"] = carregar_qwen()
    except BaseException:
        logging.exception("servidor de voz não subiu")
        raise
    logging.info("voz (%s) pronta em http://%s:%d", MOTOR, HOST, PORTA)
    servidor.serve_forever()
    logging.info("servidor de voz desligado")


if __name__ == "__main__":
    main()
