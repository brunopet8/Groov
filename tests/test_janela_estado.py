"""Roda os testes do redutor da janela (node:test); sem node, pula."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]


def test_estado_js_no_node():
    node = shutil.which("node")
    if not node:
        pytest.skip("node não está no PATH")
    # glob em vez da pasta: o node 24 trata "tests/janela/" como módulo
    r = subprocess.run([node, "--test", "tests/janela/*.test.js"], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert re.search(r"tests [1-9]", r.stdout + r.stderr), "o node não rodou nenhum teste"
