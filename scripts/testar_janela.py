"""Confere de olho, sem falar: mostra a janela do GROOV em tela cheia no 2º monitor por 4 s e a oculta de novo.
A janela precisa estar aberta (scripts/conversa_no_inicio.ps1 ou python -m src.conversa.abrir_janela). GROOV_PORTA escolhe a porta.
Rode com o GROOV dormindo: este script não fala com o servidor e esconderia a janela no meio de uma conversa.
Uso: .venv-conversa/Scripts/python scripts/testar_janela.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.conversa import tela  # noqa: E402

titulo = tela.titulo_da_janela(tela.porta())
win32 = tela.Win32()
if win32.achar(titulo) is None:
    sys.exit(f"Não achei a janela {titulo!r}: ela está aberta?")
print("monitores:", win32.monitores(), "| escolhido:", tela.escolher_monitor(win32.monitores()))
janela = tela.Tela(titulo, win32)
print("mostrando...")
janela.ao_estado("acordando")
time.sleep(4)
print("escondendo...")
janela.ao_estado("dormindo")
