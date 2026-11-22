import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from src.vida.banco import Banco, Evento


def test_itens_trocam_por_fonte(tmp_path):
    b = Banco(tmp_path / "vida.db")
    b.trocar_itens("trello", {"c1": {"nome": "A"}, "c2": {"nome": "B"}})
    b.trocar_itens("trello", {"c2": {"nome": "B2"}})
    assert b.itens("trello") == {"c2": {"nome": "B2"}} and b.itens("outra") == {}


def test_trocar_itens_de_uma_fonte_nao_mexe_na_outra(tmp_path):
    b = Banco(tmp_path / "vida.db")
    b.trocar_itens("trello", {"c1": {"nome": "A"}})
    b.trocar_itens("outra", {"x": {"nome": "X"}})
    b.trocar_itens("trello", {})
    assert b.itens("trello") == {} and b.itens("outra") == {"x": {"nome": "X"}}


def test_eventos_contados_e_persistencia(tmp_path):
    agora = datetime(2026, 10, 27, 9, tzinfo=timezone(timedelta(hours=-3)))
    b = Banco(tmp_path / "vida.db")
    b.adicionar_eventos([Evento("trello", "c1", "novo", "Um."), Evento("trello", "c2", "mudou", "Dois.")], agora)
    um, dois = b.eventos_nao_contados()
    assert (um.texto, dois.texto) == ("Um.", "Dois.") and um.id < dois.id
    assert um.criado_em == agora.isoformat()
    b.marcar_contados([um.id], agora)
    b2 = Banco(tmp_path / "vida.db")
    assert [e.texto for e in b2.eventos_nao_contados()] == ["Dois."]
    assert [e.texto for e in b2.eventos_recentes(5)] == ["Dois.", "Um."]


def test_eventos_recentes_respeita_o_limite(tmp_path):
    agora = datetime(2026, 10, 27, 9, tzinfo=timezone(timedelta(hours=-3)))
    b = Banco(tmp_path / "vida.db")
    b.adicionar_eventos([Evento("trello", f"c{i}", "novo", f"E{i}.") for i in range(5)], agora)
    assert [e.texto for e in b.eventos_recentes(2)] == ["E4.", "E3."]


def test_banco_em_wal(tmp_path):
    b = Banco(tmp_path / "vida.db")
    assert b._con.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


AGORA = datetime(2026, 10, 27, 9, tzinfo=timezone(timedelta(hours=-3)))


def test_registrar_coleta_grava_itens_eventos_e_hora(tmp_path):
    b = Banco(tmp_path / "vida.db")
    assert b.ultima_coleta("trello") is None
    b.registrar_coleta("trello", {"c1": {"nome": "A"}}, [Evento("trello", "c1", "novo", "Um.")], AGORA)
    assert b.itens("trello") == {"c1": {"nome": "A"}}
    assert [e.texto for e in b.eventos_nao_contados()] == ["Um."]
    assert b.ultima_coleta("trello") == AGORA and b.ultima_coleta("outra") is None


def test_colunas_ignoradas_guardam_e_voltam(tmp_path):
    b = Banco(tmp_path / "vida.db")
    assert b.colunas_ignoradas() == set()
    b.ignorar_coluna("Projeto 2026", "Vagas recusadas")
    b.ignorar_coluna("Projeto 2026", "Vagas recusadas")  # repetir não duplica nem quebra
    assert Banco(tmp_path / "vida.db").colunas_ignoradas() == {("Projeto 2026", "Vagas recusadas")}
    b.voltar_coluna("Projeto 2026", "Vagas recusadas")
    assert b.colunas_ignoradas() == set()


def test_registrar_coleta_e_atomica(tmp_path):
    """Falha no meio (banco travado, servidor fechando): nada fica pela metade, senão a próxima rodada repete eventos."""
    b = Banco(tmp_path / "vida.db")
    b.registrar_coleta("trello", {"c1": {"nome": "A"}}, [], AGORA)
    ruim = Evento("trello", "c2", "novo", None)  # viola NOT NULL depois de os itens já terem sido trocados
    with pytest.raises(sqlite3.IntegrityError):
        b.registrar_coleta("trello", {"c2": {"nome": "B"}}, [ruim], AGORA + timedelta(hours=1))
    assert b.itens("trello") == {"c1": {"nome": "A"}} and b.eventos_nao_contados() == []
    assert b.ultima_coleta("trello") == AGORA
