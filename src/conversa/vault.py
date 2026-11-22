"""Vault do GROOV (second brain em markdown, aberto no Obsidian): estrutura e diário da conversa. Só arquivo local."""
import logging
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from src import config

log = logging.getLogger("groov.vault")

RAIZ_PADRAO = Path(__file__).resolve().parents[2] / "vault"  # git-ignored; GROOV_VAULT aponta outra pasta
PASTAS = ("raw", "wiki", "output", "memoria", "diario")
CLAUDE_MD = """# Vault do GROOV

- `raw/`: entra qualquer coisa (artigos, PDFs, pesquisas baixadas), sem organizar.
- `wiki/`: a IA organiza o `raw/` em artigos, uma pasta por assunto, cada uma com `_index.md`; o mapa geral é `wiki/_master-index.md`.
- `output/`: respostas e entregas (relatórios, apresentações, resultados de pesquisa).
- `memoria/`: o que o GROOV sabe sobre o usuário.
- `diario/`: um arquivo por dia com cada turno da conversa e o recibo de cada pedido.

Nunca apague nem reescreva o `diario/`; só acrescente.
"""
INDICE = "# Índice da wiki\n"


def raiz() -> Path:
    pasta = config.valor("GROOV_VAULT").strip()
    return Path(pasta) if pasta else RAIZ_PADRAO


def preparar(raiz: Path) -> bool:
    """Cria o que falta; nunca sobrescreve. False se o disco recusar."""
    try:
        for p in PASTAS:
            (raiz / p).mkdir(parents=True, exist_ok=True)
        for arquivo, texto in ((raiz / "CLAUDE.md", CLAUDE_MD), (raiz / "wiki" / "_master-index.md", INDICE)):
            if not arquivo.exists():
                arquivo.write_text(texto, encoding="utf-8")
        return True
    except OSError as e:
        log.warning("vault não preparado: %s", type(e).__name__)
        return False


def _acrescentar(raiz: Path, agora: datetime, linha: str) -> None:
    try:
        pasta = raiz / "diario"
        pasta.mkdir(parents=True, exist_ok=True)
        arquivo = pasta / f"{agora:%Y-%m-%d}.md"
        novo = not arquivo.exists()
        with open(arquivo, "a", encoding="utf-8") as f:
            f.write((f"# {agora:%Y-%m-%d}\n\n" if novo else "") + f"- {linha}\n")
    except (OSError, ValueError) as e:  # nunca derruba a conversa; o texto não vai ao log
        log.warning("diário não gravado: %s", type(e).__name__)


def _slug(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", sem_acento).strip("-")[:40].rstrip("-") or "trabalho"


def salvar_output(raiz: Path, assunto: str, texto: str, agora: datetime | None = None) -> Path | None:
    """O resultado inteiro de um trabalho em output/; None se o disco recusar."""
    agora = agora or datetime.now()
    try:
        pasta = raiz / "output"
        pasta.mkdir(parents=True, exist_ok=True)
        arquivo = pasta / f"{agora:%Y-%m-%d-%H%M%S}-{_slug(assunto)}.md"
        arquivo.write_text(texto, encoding="utf-8")
        return arquivo
    except (OSError, ValueError) as e:
        log.warning("output não gravado: %s", type(e).__name__)
        return None


def registrar_turno(raiz: Path, quem: str, texto: str, agora: datetime | None = None) -> None:
    agora = agora or datetime.now()
    _acrescentar(raiz, agora, f"**{agora:%H:%M:%S} {quem}:** " + " ".join(texto.split()))


def registrar_recibo(raiz: Path, ferramenta: str, ok: bool, segundos: float | None,
                     agora: datetime | None = None) -> None:
    agora = agora or datetime.now()
    tempo = "-" if segundos is None else f"{segundos:.1f}".replace(".", ",") + "s"
    _acrescentar(raiz, agora, f"{agora:%H:%M:%S} recibo: ferramenta={ferramenta} resultado={'ok' if ok else 'falhou'} tempo={tempo}")
