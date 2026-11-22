from datetime import datetime, timedelta, timezone

from src.vida.banco import Banco
from src.vida.colunas import Confirmacao, Pedido, guardar, propor_coluna

AGORA = datetime(2026, 10, 27, 9, tzinfo=timezone(timedelta(hours=-3)))


def cartao(quadro, lista):
    return {"quadro": quadro, "lista": lista, "nome": "x", "prazo": None, "feito": False, "atividade": None,
            "checks": [0, 0], "contagem": False}


def banco_com(tmp_path, *colunas):
    banco = Banco(tmp_path / "vida.db")
    banco.registrar_coleta("trello", {f"c{i}": cartao(q, l) for i, (q, l) in enumerate(colunas)}, [], AGORA)
    return banco


def test_propor_ignorar_pergunta_sem_guardar(tmp_path):
    banco = banco_com(tmp_path, ("Projeto 2026", "Vagas recusadas"), ("Projeto 2026", "A fazer"))
    fala, pedido = propor_coluna(banco, "ignorar", "vagas recusadas", "")
    assert fala == "Parar de cobrar prazo da coluna Vagas recusadas, do Projeto 2026? Confirma, senhor?"
    assert pedido == Pedido("ignorar", "Projeto 2026", "Vagas recusadas") and banco.colunas_ignoradas() == set()


def test_propor_casa_parte_do_nome_e_o_quadro(tmp_path):
    banco = banco_com(tmp_path, ("Projeto 2026", "Vagas recusadas"), ("Projeto 2025", "Vagas recusadas"))
    fala, pedido = propor_coluna(banco, "ignorar", "recusadas", "projeto 2026")
    assert pedido == Pedido("ignorar", "Projeto 2026", "Vagas recusadas")


def test_propor_ambiguo_pergunta_qual(tmp_path):
    banco = banco_com(tmp_path, ("Projeto 2026", "Vagas recusadas"), ("Projeto 2025", "Vagas recusadas"))
    fala, pedido = propor_coluna(banco, "ignorar", "Vagas recusadas", "")
    assert pedido is None and "Projeto 2026" in fala and "Projeto 2025" in fala and fala.endswith("Qual delas, senhor?")


def test_nome_igual_vence_nome_contido(tmp_path):
    banco = banco_com(tmp_path, ("Projeto 2026", "Vagas"), ("Projeto 2026", "Vagas recusadas"))
    assert propor_coluna(banco, "ignorar", "vagas", "")[1] == Pedido("ignorar", "Projeto 2026", "Vagas")


def test_propor_sem_achar(tmp_path):
    banco = banco_com(tmp_path, ("Projeto 2026", "A fazer"))
    assert propor_coluna(banco, "ignorar", "Vagas recusadas", "") == \
        ("Não achei a coluna Vagas recusadas no seu Trello, senhor.", None)
    assert propor_coluna(banco, "ignorar", "  ", "")[1] is None


def test_prospeccao_nao_e_coluna_para_ignorar(tmp_path):
    banco = Banco(tmp_path / "vida.db")
    lead = cartao("Empresa X — Prospecção", "Novos") | {"contagem": True}
    banco.registrar_coleta("trello", {"c1": lead}, [], AGORA)
    assert propor_coluna(banco, "ignorar", "Novos", "")[1] is None


def test_ja_ignorada_nao_pergunta(tmp_path):
    banco = banco_com(tmp_path, ("Projeto 2026", "Vagas recusadas"))
    banco.ignorar_coluna("Projeto 2026", "Vagas recusadas")
    assert propor_coluna(banco, "ignorar", "vagas recusadas", "") == \
        ("Já não cobro a coluna Vagas recusadas, do Projeto 2026, senhor.", None)


def test_voltar_so_casa_com_as_ignoradas_mesmo_sem_cartao(tmp_path):
    banco = banco_com(tmp_path, ("Projeto 2026", "A fazer"))
    assert propor_coluna(banco, "voltar", "A fazer", "") == ("A coluna A fazer não está ignorada, senhor.", None)
    banco.ignorar_coluna("Projeto 2026", "Vagas recusadas")  # coluna sem cartão na última coleta
    fala, pedido = propor_coluna(banco, "voltar", "vagas recusadas", "")
    assert fala == "Voltar a cobrar a coluna Vagas recusadas, do Projeto 2026? Confirma, senhor?"
    assert pedido == Pedido("voltar", "Projeto 2026", "Vagas recusadas")


def test_guardar_ignora_e_volta(tmp_path):
    banco = Banco(tmp_path / "vida.db")
    assert guardar(banco, Pedido("ignorar", "Projeto 2026", "Vagas recusadas")) == \
        "Pronto, senhor. Não cobro mais a coluna Vagas recusadas, do Projeto 2026."
    assert banco.colunas_ignoradas() == {("Projeto 2026", "Vagas recusadas")}
    assert guardar(banco, Pedido("voltar", "Projeto 2026", "Vagas recusadas")) == \
        "Pronto, senhor. Volto a cobrar a coluna Vagas recusadas, do Projeto 2026."
    assert banco.colunas_ignoradas() == set()


def test_confirmacao_expoe_o_prazo():
    assert Confirmacao(prazo=30).prazo == 30


def test_confirmacao_vale_uma_vez_e_expira():
    c = Confirmacao(prazo=30)
    pedido = Pedido("ignorar", "Q", "L")
    assert c.pegar(0) is None
    c.propor(pedido, 100)
    assert c.pegar(129) == pedido and c.pegar(129) is None  # usada uma vez só
    c.propor(pedido, 100)
    assert c.pegar(131) is None and c.pegar(101) is None  # expirou e foi descartada
