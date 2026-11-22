import socket
import subprocess
import sys
from pathlib import Path

import pytest

from src.conversa import abrir_janela as modulo
from src.conversa.tela import Monitor
from src.conversa.abrir_janela import (
    CHROME,
    comando_chrome,
    esconder_quando_existir,
    esperar_porta,
    perfil_da_janela,
)


def relogio_falso():
    t = [0.0]
    return (lambda: t[0]), (lambda s: t.__setitem__(0, t[0] + s))


SECUNDARIO = Monitor((-1366, 0, 0, 768), False)


class Backend:
    def __init__(self, achados):
        self.achados, self.escondidas = list(achados), []

    def achar(self, titulo):
        """Segue a lista e repete o último valor (como o Win32 de verdade: a janela, uma vez criada, continua lá)."""
        if not self.achados:
            return None
        return self.achados.pop(0) if len(self.achados) > 1 else self.achados[0]

    def monitores(self):
        return [Monitor((0, 0, 1920, 1080), True), SECUNDARIO]

    def esconder(self, janela):
        self.escondidas.append(janela)


def test_chrome_nasce_em_tela_cheia_no_monitor_escolhido():
    cmd = comando_chrome(7860, Path("C:/perfil"), (-1366, 0, 0, 768))
    assert cmd[0] == CHROME
    assert "--app=http://localhost:7860/" in cmd
    assert "--start-fullscreen" in cmd and "--window-position=-1366,0" in cmd
    assert f"--user-data-dir={Path('C:/perfil')}" in cmd
    assert "--autoplay-policy=no-user-gesture-required" in cmd


def test_sem_monitor_nao_manda_posicao_e_extras_vao_no_fim():
    cmd = comando_chrome(7861, Path("C:/perfil"), None, extras=["--use-fake-device-for-media-stream"])
    assert not any(a.startswith("--window-position") for a in cmd)
    assert cmd[-1] == "--use-fake-device-for-media-stream" and "--app=http://localhost:7861/" in cmd


def test_perfil_separado_fora_da_porta_padrao():
    base = Path("C:/Users/x/AppData/Local/GROOV")
    assert perfil_da_janela(7860, base) == base / "chrome"  # o do usuário, com a permissão do microfone
    assert perfil_da_janela(7861, base) == base / "chrome-7861"  # senão o Chrome entrega a janela ao processo da real


def test_esconde_assim_que_a_janela_aparece():
    relogio, dormir = relogio_falso()
    b = Backend([None, None, 5])
    assert esconder_quando_existir(b, "GROOV", prazo=15, passo=0.25, relogio=relogio, dormir=dormir) is True
    assert b.escondidas == [5] and relogio() == 0.5


def test_desiste_no_prazo_sem_janela():
    relogio, dormir = relogio_falso()
    b = Backend([])
    assert esconder_quando_existir(b, "GROOV", prazo=1, passo=0.25, relogio=relogio, dormir=dormir) is False
    assert b.escondidas == []


def test_espera_a_porta_abrir():
    with socket.create_server(("127.0.0.1", 0)) as s:
        assert esperar_porta(s.getsockname()[1], prazo=5) is True


def test_porta_fechada_desiste_no_prazo():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        porta = s.getsockname()[1]
    relogio, dormir = relogio_falso()
    assert esperar_porta(porta, prazo=3, passo=1, relogio=relogio, dormir=dormir) is False


def test_abre_o_chrome_no_segundo_monitor_e_esconde(monkeypatch):
    lancados = []
    monkeypatch.setattr(subprocess, "Popen", lambda cmd, **kw: lancados.append((cmd, kw)))
    b = Backend([None, 5])  # não existe ao abrir; aparece na 2ª olhada
    assert modulo.abrir_janela(7860, Path("C:/perfil"), b) is True
    (cmd, kw), = lancados
    assert "--start-fullscreen" in cmd and "--window-position=-1366,0" in cmd and b.escondidas == [5]
    assert kw["stdout"] is subprocess.DEVNULL  # sob pythonw não há console para herdar


def test_janela_ja_aberta_so_e_escondida_sem_abrir_outra(monkeypatch):
    lancados = []
    monkeypatch.setattr(subprocess, "Popen", lambda cmd, **kw: lancados.append(cmd))
    b = Backend([5])
    assert modulo.abrir_janela(7860, Path("C:/perfil"), b) is True
    assert lancados == [] and b.escondidas == [5]


def test_main_usa_a_porta_o_perfil_do_usuario_e_os_extras_da_linha_de_comando(monkeypatch, tmp_path):
    chamadas = []
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.delenv("GROOV_PORTA", raising=False)
    monkeypatch.setattr(sys, "argv", ["abrir_janela", "--use-fake-ui-for-media-stream"])
    monkeypatch.setattr(modulo, "esperar_porta", lambda porta: True)
    monkeypatch.setattr(modulo.tela, "Win32", lambda: "win32")
    monkeypatch.setattr(modulo, "abrir_janela", lambda *args: chamadas.append(args) or True)
    modulo.main()
    assert chamadas == [(7860, tmp_path / "GROOV" / "chrome", "win32", ["--use-fake-ui-for-media-stream"])]


def test_main_desiste_se_o_servidor_nao_responde(monkeypatch):
    monkeypatch.setattr(modulo, "esperar_porta", lambda porta: False)
    with pytest.raises(SystemExit):
        modulo.main()
