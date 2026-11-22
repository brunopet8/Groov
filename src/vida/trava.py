"""Trava de arquivo: um coletor só, mesmo com um 2º servidor aberto (teste, medição na porta 7861)."""
import sys
from pathlib import Path
from typing import BinaryIO


def travar(caminho: Path) -> BinaryIO | None:
    """Arquivo aberto e travado (quem chama o mantém vivo; fechar solta a trava), ou None se outro processo já trava."""
    arquivo = open(caminho, "a+b")
    arquivo.seek(0)  # o modo "a" começa no fim: sem isto dois processos travariam bytes diferentes
    try:
        if sys.platform == "win32":
            import msvcrt
            msvcrt.locking(arquivo.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(arquivo, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        arquivo.close()
        return None
    return arquivo
