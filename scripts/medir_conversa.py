"""Mede a conversa do GROOV ponta a ponta: Chrome headless usa tests/fala.wav como microfone e conversa com
src.conversa.servidor por WebRTC. Latência = fim da fala → 1º áudio do bot (linhas LATENCIA do UserBotLatencyObserver).
Também anota a VRAM antes e com tudo ligado.

Adaptado do projeto REA.
Uso: .venv-conversa/Scripts/python scripts/medir_conversa.py [duração_s]
  (mede com a voz Qwen; o servidor da janela NÃO pode estar na porta 7861; precisa de tests/fala.wav,
   gerado por scripts/gerar_fala.py, e da GOOGLE_API_KEY em privado/.env, que o programa lê sozinho)
"""
import os
import re
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))  # rodado como script, só scripts/ está no caminho
from src.conversa.telemetria import ler_vram  # noqa: E402
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORTA = 7861  # fora da 7860, para não brigar com a janela que o usuário deixa aberta
ARGS = sys.argv[1:]
DURACAO_S = int(ARGS.pop()) if ARGS and ARGS[-1].isdigit() else 120
VOZES = ARGS or ["qwen"]
PYTHON = RAIZ / ".venv-conversa" / "Scripts" / "python.exe"


def esperar_http(url, timeout=120):
    fim = time.time() + timeout
    while time.time() < fim:
        try:
            return urllib.request.urlopen(url, timeout=2).read()
        except OSError:
            time.sleep(1)
    raise TimeoutError(url)


def esperar_voz(timeout=240):
    """O servidor de voz abre a porta antes de carregar o modelo: espera uma resposta HTTP ao GET."""
    fim = time.time() + timeout
    while time.time() < fim:
        try:
            urllib.request.urlopen("http://127.0.0.1:8765/", timeout=2)
        except urllib.error.HTTPError:
            return  # respondeu: está atendendo
        except OSError:
            time.sleep(2)
    raise TimeoutError("servidor de voz não respondeu")


def medir(voz):
    # o servidor de voz já ligado, como no dia a dia (liga com o Windows)
    subprocess.Popen([str(RAIZ / ".venv-qwen" / "Scripts" / "pythonw.exe"), str(RAIZ / "src" / "voz_servidor.py")], cwd=RAIZ)
    esperar_voz()
    base, total = ler_vram()
    log = RAIZ / f"medir_conversa-{voz}.log"
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "GROOV_PORTA": str(PORTA), "GROOV_VOZ": voz, "GROOV_ACORDADO": "1", "GROOV_LOG": "DEBUG"}
    with open(log, "w", encoding="utf-8") as f, tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as perfil:
        servidor = subprocess.Popen([str(PYTHON), "-m", "src.conversa.servidor"], cwd=RAIZ, stdout=f, stderr=subprocess.STDOUT, env=env)
        chrome = None
        try:
            esperar_http(f"http://127.0.0.1:{PORTA}/")
            chrome = subprocess.Popen([
                CHROME, "--headless=new", f"--user-data-dir={perfil}",
                "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
                f"--use-file-for-fake-audio-capture={RAIZ / 'tests' / 'fala.wav'}",
                "--autoplay-policy=no-user-gesture-required", f"http://localhost:{PORTA}/",
            ])
            time.sleep(DURACAO_S * 0.75)  # tudo carregado e conversando
            ligado, _ = ler_vram()
            time.sleep(DURACAO_S * 0.25)
        finally:
            for p in (chrome, servidor):
                if p:
                    p.kill()
            time.sleep(1)

    texto = log.read_text(encoding="utf-8", errors="replace")
    for linha in texto.splitlines():
        if "Transcription:" in linha or "LATENCIA" in linha or "ERROR" in linha or "prompt tokens" in linha:
            print(linha.split(" - ", 1)[-1])
    # Só turnos do usuário; exclui "TOTAL (from client connected)" da saudação.
    totais = [float(x) for x in re.findall(r"LATENCIA\s+([\d.]+)s\s+TOTAL(?! \()", texto)]
    ouviu = re.search(r"Transcription: \[.*Austr", texto) is not None
    resumo = " / ".join(f"{t:.2f}" for t in totais) or "nenhum turno medido"
    mediana = f" (mediana {statistics.median(totais):.2f} s)" if totais else ""
    print(f"== {voz}: fim da fala → 1º áudio: {resumo} s{mediana}; Whisper ouviu a pergunta: {ouviu}")
    print(f"== {voz}: VRAM {base} → {ligado} MiB (+{ligado - base}) de {total}; log: {log}")
    return totais


def main():
    for voz in VOZES:
        medir(voz)


if __name__ == "__main__":
    main()
