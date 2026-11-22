import pytest

pytest.importorskip("dotenv")  # o script importa src.conversa: só roda em .venv-conversa

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("medir_pagina", Path(__file__).resolve().parents[1] / "scripts" / "medir_pagina.py")
medir_pagina = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(medir_pagina)


def test_fecha_so_o_excedente_pelo_indice_atual():
    lista = [(0, "Meu e-mail", "https://mail.exemplo/"), (1, "GitHub", "https://github.com/")]
    assert medir_pagina.aba_para_fechar(lista, "GitHub", "https://github.com/", 0) == 1


def test_nunca_fecha_a_que_o_usuario_ja_tinha():
    lista = [(0, "GitHub", "https://github.com/")]
    assert medir_pagina.aba_para_fechar(lista, "GitHub", "https://github.com/", 1) is None
    dupla = [(0, "GitHub", "https://github.com/"), (1, "GitHub", "https://github.com/")]
    assert medir_pagina.aba_para_fechar(dupla, "GitHub", "https://github.com/", 1) == 1
    assert medir_pagina.aba_para_fechar([(0, "Outra", "https://x/")], "GitHub", "https://github.com/", 0) is None
