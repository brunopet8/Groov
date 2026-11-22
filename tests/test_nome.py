"""A marca é GROOV; só o jeito de chamar ("Hey JARVIS") e o Hermes parado guardam o nome antigo."""
import re
from pathlib import Path

RAIZ = Path(__file__).parent.parent
PASTAS = ("src", "scripts", "ferramentas", "tests", ".claude")
SOLTOS = ("CLAUDE.md", ".gitignore")
EXTENSOES = {".py", ".ps1", ".js", ".html", ".css", ".md", ".json", ".txt", ".yaml", ".yml"}
FORA = ("node_modules", ".npm-cache", "__pycache__", "worktrees", "council-cache", "vendor", "fixtures",
        "test_plugin_jarvis_voz.py", "test_hermes_config.py", "test_nome.py")
PASTA_DO_PROJETO = re.compile(r"[\\/]JARVIS(?=[\\/\"']|$)")  # a pasta do projeto não muda de nome
MARCA = re.compile(r"(?<![Hh]ey )(?<!HEY )JARVIS")
IDENTIFICADORES = re.compile(r"JARVIS_[A-Z]|getLogger\([\"']jarvis|[\"']jarvis\.|titulo_jarvis|\.jarvis\b|_com_jarvis|jarvis-janela")
LEGADO = "legado:"  # linha que cita o nome antigo de propósito (apagar atalhos velhos)


def _arquivos():
    for pasta in PASTAS:
        for a in (RAIZ / pasta).rglob("*"):
            if a.is_file() and a.suffix in EXTENSOES and not any(f in a.parts or f == a.name for f in FORA):
                yield a
    yield from (RAIZ / s for s in SOLTOS if (RAIZ / s).exists())


def test_so_o_jeito_de_chamar_guarda_o_nome_antigo():
    sobras = []
    for arquivo in _arquivos():
        for n, linha in enumerate(arquivo.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            limpa = PASTA_DO_PROJETO.sub("", linha)
            if LEGADO not in linha and (MARCA.search(limpa) or IDENTIFICADORES.search(limpa)):
                sobras.append(f"{arquivo.relative_to(RAIZ)}:{n}: {linha.strip()[:100]}")
    assert sobras == []
