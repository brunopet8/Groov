"""Banco local (privado/vida.db): a última foto de cada coisa vista e os eventos que o GROOV ainda vai contar."""
import json
import sqlite3
import threading
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class Evento:
    fonte: str
    chave: str
    tipo: str
    texto: str


@dataclass(frozen=True)
class EventoGuardado:
    id: int
    fonte: str
    chave: str
    tipo: str
    texto: str
    criado_em: str


_ESQUEMA = """
CREATE TABLE IF NOT EXISTS item (
    fonte TEXT NOT NULL, chave TEXT NOT NULL, dados TEXT NOT NULL, PRIMARY KEY (fonte, chave));
CREATE TABLE IF NOT EXISTS evento (
    id INTEGER PRIMARY KEY AUTOINCREMENT, fonte TEXT NOT NULL, chave TEXT NOT NULL, tipo TEXT NOT NULL,
    texto TEXT NOT NULL, criado_em TEXT NOT NULL, contado_em TEXT);
CREATE TABLE IF NOT EXISTS coleta (fonte TEXT PRIMARY KEY, em TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS coluna_ignorada (quadro TEXT NOT NULL, lista TEXT NOT NULL, PRIMARY KEY (quadro, lista));
"""
_COLUNAS = "id, fonte, chave, tipo, texto, criado_em"


class Banco:
    """Chamado por asyncio.to_thread de tarefas diferentes (coletor e bot): um Lock em volta de cada método."""

    def __init__(self, caminho: Path):
        self._lock = threading.Lock()
        self._con = sqlite3.connect(caminho, check_same_thread=False, timeout=5)
        self._con.execute("PRAGMA journal_mode=WAL")
        self._con.executescript(_ESQUEMA)

    def itens(self, fonte: str) -> dict[str, dict]:
        with self._lock:
            linhas = self._con.execute("SELECT chave, dados FROM item WHERE fonte = ?", (fonte,)).fetchall()
        return {chave: json.loads(dados) for chave, dados in linhas}

    def trocar_itens(self, fonte: str, itens: dict[str, dict]) -> None:
        with self._lock, self._con:
            self._con.execute("DELETE FROM item WHERE fonte = ?", (fonte,))
            self._con.executemany(
                "INSERT INTO item (fonte, chave, dados) VALUES (?, ?, ?)",
                [(fonte, chave, json.dumps(dados, ensure_ascii=False)) for chave, dados in itens.items()])

    def registrar_coleta(self, fonte: str, itens: dict[str, dict], eventos: list[Evento], agora: datetime) -> None:
        """Uma coleta que deu certo, numa transação só: nova foto, eventos dela e a hora. Se parar no meio (servidor
        fechando, banco travado), nada fica pela metade e a próxima rodada não repete eventos."""
        with self._lock, self._con:
            self._con.execute("DELETE FROM item WHERE fonte = ?", (fonte,))
            self._con.executemany(
                "INSERT INTO item (fonte, chave, dados) VALUES (?, ?, ?)",
                [(fonte, chave, json.dumps(dados, ensure_ascii=False)) for chave, dados in itens.items()])
            self._con.executemany(
                "INSERT INTO evento (fonte, chave, tipo, texto, criado_em) VALUES (?, ?, ?, ?, ?)",
                [(e.fonte, e.chave, e.tipo, e.texto, agora.isoformat()) for e in eventos])
            self._con.execute("INSERT OR REPLACE INTO coleta (fonte, em) VALUES (?, ?)", (fonte, agora.isoformat()))

    def ultima_coleta(self, fonte: str) -> datetime | None:
        """Quando a fonte foi lida com sucesso pela última vez; None se nunca (chave errada, 1ª rodada que falhou)."""
        with self._lock:
            linha = self._con.execute("SELECT em FROM coleta WHERE fonte = ?", (fonte,)).fetchone()
        return datetime.fromisoformat(linha[0]) if linha else None

    def adicionar_eventos(self, eventos: list[Evento], agora: datetime) -> None:
        with self._lock, self._con:
            self._con.executemany(
                "INSERT INTO evento (fonte, chave, tipo, texto, criado_em) VALUES (?, ?, ?, ?, ?)",
                [(e.fonte, e.chave, e.tipo, e.texto, agora.isoformat()) for e in eventos])

    def eventos_nao_contados(self) -> list[EventoGuardado]:
        with self._lock:
            linhas = self._con.execute(
                f"SELECT {_COLUNAS} FROM evento WHERE contado_em IS NULL ORDER BY id").fetchall()
        return [EventoGuardado(*linha) for linha in linhas]

    def eventos_recentes(self, limite: int) -> list[EventoGuardado]:
        with self._lock:
            linhas = self._con.execute(f"SELECT {_COLUNAS} FROM evento ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
        return [EventoGuardado(*linha) for linha in linhas]

    def colunas_ignoradas(self) -> set[tuple[str, str]]:
        """(quadro, lista) cujos cartões não contam como atrasados nem parados; o usuário escolhe por voz."""
        with self._lock:
            return set(self._con.execute("SELECT quadro, lista FROM coluna_ignorada").fetchall())

    def ignorar_coluna(self, quadro: str, lista: str) -> None:
        with self._lock, self._con:
            self._con.execute("INSERT OR IGNORE INTO coluna_ignorada (quadro, lista) VALUES (?, ?)", (quadro, lista))

    def voltar_coluna(self, quadro: str, lista: str) -> None:
        with self._lock, self._con:
            self._con.execute("DELETE FROM coluna_ignorada WHERE quadro = ? AND lista = ?", (quadro, lista))

    def marcar_contados(self, ids: Iterable[int], agora: datetime) -> None:
        with self._lock, self._con:
            self._con.executemany("UPDATE evento SET contado_em = ? WHERE id = ?", [(agora.isoformat(), i) for i in ids])
