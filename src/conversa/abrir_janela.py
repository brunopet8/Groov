"""Abre a janela do GROOV (Chrome --app) em tela cheia no 2º monitor e a oculta na hora: ela só reaparece quando o GROOV
acorda (tela.py). Roda no atalho de início, depois do servidor: pythonw -m src.conversa.abrir_janela. GROOV_PORTA muda a porta."""
import os
import socket
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

from src.conversa import tela

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
LOG = Path(__file__).resolve().parents[2] / "conversa.log"  # o mesmo do servidor (sem console, pythonw)


def perfil_da_janela(porta: int, base: Path) -> Path:
    """Perfil só do GROOV: as opções do Chrome só valem se ele iniciar um processo novo, e a permissão do microfone fica
    guardada aqui. Outra porta (teste) tem perfil próprio, senão o Chrome entrega a janela ao processo da janela de verdade."""
    return base / ("chrome" if porta == tela.PORTA_PADRAO else f"chrome-{porta}")


def comando_chrome(porta: int, perfil: Path, monitor: tela.Retangulo | None, chrome: str = CHROME, extras=()) -> list[str]:
    comando = [chrome, f"--app=http://localhost:{porta}/", f"--user-data-dir={perfil}",
               "--autoplay-policy=no-user-gesture-required", "--start-fullscreen"]
    if monitor:
        comando.append(f"--window-position={monitor[0]},{monitor[1]}")  # o monitor onde a tela cheia nasce
    return [*comando, *extras]


def esperar_porta(porta: int, prazo: float = 90, passo: float = 1, relogio: Callable = time.monotonic,
                  dormir: Callable = time.sleep) -> bool:
    fim = relogio() + prazo
    while True:
        try:
            socket.create_connection(("127.0.0.1", porta), timeout=1).close()
            return True
        except OSError:
            if relogio() >= fim:
                return False
            dormir(passo)


def esconder_quando_existir(backend: tela.Backend, titulo: str, prazo: float = 15, passo: float = 0.25,
                            relogio: Callable = time.monotonic, dormir: Callable = time.sleep) -> bool:
    """O Chrome ignora "iniciar minimizado" em tela cheia: oculta assim que a janela existe (título já carregado)."""
    fim = relogio() + prazo
    while True:
        janela = backend.achar(titulo)
        if janela is not None:
            backend.esconder(janela)
            return True
        if relogio() >= fim:
            return False
        dormir(passo)


def abrir_janela(porta: int, perfil: Path, backend: tela.Backend, extras=()) -> bool:
    """True se a janela ficou oculta. Se já existe uma, só a oculta (uma janela só: a 2ª derrubaria a conexão da 1ª
    e o Chrome entregaria a URL nova ao processo antigo, sem a tela cheia)."""
    titulo = tela.titulo_da_janela(porta)
    if backend.achar(titulo) is None:
        subprocess.Popen(comando_chrome(porta, perfil, tela.escolher_monitor(backend.monitores()), extras=extras),
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return esconder_quando_existir(backend, titulo)


def main():
    if sys.stderr is None:  # pythonw: a falha daqui também precisa deixar rastro, no mesmo log do servidor
        sys.stderr = open(LOG, "a", encoding="utf-8", buffering=1)
    porta = tela.porta()
    if not esperar_porta(porta):
        sys.exit(f"servidor da conversa não respondeu na porta {porta}")
    perfil = perfil_da_janela(porta, Path(os.environ["LOCALAPPDATA"]) / "GROOV")
    if not abrir_janela(porta, perfil, tela.Win32(), sys.argv[1:]):
        sys.exit("a janela do GROOV não apareceu em 15 s (o servidor a esconde quando ela conectar)")


if __name__ == "__main__":
    main()
