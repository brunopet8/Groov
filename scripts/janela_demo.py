"""Sobe a janela do GROOV sem microfone nem placa, para olhar as telas: http://localhost:7861/?demo=1&cena=ocioso
Uso: .venv-conversa/Scripts/python scripts/janela_demo.py  (cenas em src/conversa/janela/demo.js)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import uvicorn  # noqa: E402

from src.conversa.servidor import criar_app  # noqa: E402

PORTA = 7861

if __name__ == "__main__":
    uvicorn.run(criar_app(bot=lambda args: None, porta=PORTA), host="127.0.0.1", port=PORTA)
