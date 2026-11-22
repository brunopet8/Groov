from datetime import datetime, timedelta, timezone

from src.vida.trello import CAMPOS_CARTAO, LIMITE_NOME, comparar, ler_quadros, parados, prazos

RIO = timezone(timedelta(hours=-3))
ATIVIDADE = "2026-10-27T12:00:00.000Z"


def cartao(nome, lista="A fazer", feito=False, checks=(0, 0), prazo=None, atividade=ATIVIDADE,
           quadro="Projeto 2026", contagem=False):
    return {"quadro": quadro, "lista": lista, "nome": nome, "prazo": prazo, "feito": feito,
            "atividade": atividade, "checks": list(checks), "contagem": contagem}


def cartao_api(id_, nome, due_complete=None, badges=None, atividade=ATIVIDADE, due=None):
    c = {"id": id_, "name": nome, "idList": "l1", "due": due, "closed": False, "dateLastActivity": atividade,
         "badges": {"checkItems": 3, "checkItemsChecked": 1, "dueComplete": False, **(badges or {})}}
    if due_complete is not None:
        c["dueComplete"] = due_complete
    return c


def trello_falso(quadros=None, listas=None):
    """Devolve um `buscar` que responde pela URL e guarda (url, cabecalhos) em .chamadas."""
    quadros = quadros if quadros is not None else [
        {"id": "b1", "name": "Projeto 2026"}, {"id": "b2", "name": "Empresa X — Prospecção"},
        {"id": "b3", "name": "Projeto modular"}]
    listas = listas if listas is not None else {
        "b1": [{"id": "l1", "name": "A fazer", "closed": False, "cards": [cartao_api("c1", "Entrevista X")]},
               {"id": "l2", "name": "Velha", "closed": True, "cards": [cartao_api("c9", "Esquecido")]}],
        "b2": [{"id": "l3", "name": "Novos", "closed": False, "cards": [cartao_api("c2", "Lead Acme")]}]}
    chamadas = []

    def buscar(url, cabecalhos):
        chamadas.append((url, cabecalhos))
        if "/members/me/boards" in url:
            return quadros
        for id_, resposta in listas.items():
            if f"/boards/{id_}/lists" in url:
                return resposta
        raise AssertionError(f"URL inesperada: {url}")

    buscar.chamadas = chamadas
    return buscar


def test_le_so_os_quadros_escolhidos_sem_desc_e_sem_chave_na_url():
    falso = trello_falso()
    itens, faltando = ler_quadros("CHAVE-K", "TOKEN-T", [" projeto 2026 ", "Não existe"], buscar=falso)
    urls = [u for u, _ in falso.chamadas]
    assert all("desc" not in u and "CHAVE-K" not in u and "TOKEN-T" not in u for u in urls)
    assert any(f"card_fields={CAMPOS_CARTAO}" in u for u in urls)
    assert falso.chamadas[0][1] == {"Authorization": 'OAuth oauth_consumer_key="CHAVE-K", oauth_token="TOKEN-T"'}
    assert faltando == ["Não existe"] and itens["c1"]["quadro"] == "Projeto 2026"
    assert not any("b3" in u for u in urls)  # "Projeto modular" não foi pedido


def test_lista_fechada_e_ignorada():
    itens, _ = ler_quadros("K", "T", ["Projeto 2026"], buscar=trello_falso())
    assert set(itens) == {"c1"}


def test_feito_vem_do_cartao_ou_dos_badges():
    listas = {"b1": [{"id": "l1", "name": "A fazer", "closed": False, "cards": [
        cartao_api("c1", "No cartão", due_complete=True),
        cartao_api("c2", "Nos badges", badges={"dueComplete": True}),
        cartao_api("c3", "Em lugar nenhum")]}]}
    itens, _ = ler_quadros("K", "T", ["Projeto 2026"], buscar=trello_falso(listas=listas))
    assert [itens[c]["feito"] for c in ("c1", "c2", "c3")] == [True, True, False]
    assert itens["c1"]["checks"] == [1, 3]


def test_nomes_longos_sao_cortados_em_80():
    longo = "x" * 300
    quadros = [{"id": "b1", "name": longo}]
    listas = {"b1": [{"id": "l1", "name": longo, "closed": False, "cards": [cartao_api("c1", longo)]}]}
    itens, faltando = ler_quadros("K", "T", [longo], buscar=trello_falso(quadros, listas))
    assert faltando == [] and LIMITE_NOME == 80
    assert [len(itens["c1"][campo]) for campo in ("quadro", "lista", "nome")] == [80, 80, 80]


def test_nome_com_emoji_e_url_passa_inteiro():
    nome = "Entrevista 🚀 https://x.com/a"  # o para_fala tira a URL na hora de falar
    listas = {"b1": [{"id": "l1", "name": "A fazer", "closed": False, "cards": [cartao_api("c1", nome)]}]}
    itens, _ = ler_quadros("K", "T", ["Projeto 2026"], buscar=trello_falso(listas=listas))
    assert itens["c1"]["nome"] == nome


def test_quadro_com_travessao_casa_com_hifen_e_marca_contagem():
    itens, faltando = ler_quadros("K", "T", ["empresa x - prospeccao"], buscar=trello_falso(),
                                  contagem=["Empresa X - Prospeccao"])
    assert faltando == [] and itens["c2"]["quadro"] == "Empresa X — Prospecção" and itens["c2"]["contagem"] is True
    outros, _ = ler_quadros("K", "T", ["Projeto 2026"], buscar=trello_falso())
    assert outros["c1"]["contagem"] is False


def test_primeira_coleta_nao_gera_eventos():
    assert comparar({}, {"c1": cartao("A")}) == []


def test_comparar_textos():
    antes = {"c1": cartao("Entrevista X", lista="A fazer", checks=[1, 3])}
    depois = {"c1": cartao("Entrevista X", lista="Em andamento", feito=True, checks=[2, 3]),
              "c2": cartao("Prova de inglês")}
    assert [e.texto for e in comparar(antes, depois)] == [
        "No Projeto 2026, Entrevista X foi para Em andamento.", "Entrevista X foi concluído.",
        "Entrevista X: 2 de 3 itens feitos.", "Cartão novo no Projeto 2026: Prova de inglês."]


def test_comparar_sem_mudanca_nao_gera_evento():
    itens = {"c1": cartao("A", checks=[1, 3])}
    assert comparar(itens, dict(itens)) == []


def test_comparar_evento_leva_fonte_chave_e_tipo():
    antes = {"c1": cartao("A")}
    depois = {"c1": cartao("A", lista="Feito")}
    (e,) = comparar(antes, depois)
    assert (e.fonte, e.chave, e.tipo) == ("trello", "c1", "mudou")


def prospeccao(nome, lista="Novos"):
    return cartao(nome, lista=lista, quadro="Empresa X — Prospecção", contagem=True)


def test_prospeccao_so_contagem():
    antes = {"p1": prospeccao("L1"), "p2": prospeccao("L2")}
    depois = {"p1": prospeccao("L1", lista="Contatados"), "p2": prospeccao("L2"),
              "p3": prospeccao("L3"), "p4": prospeccao("L4")}
    (e,) = comparar(antes, depois)
    assert e.texto == "Empresa X — Prospecção: 2 leads novos e 1 mudou de etapa." and e.tipo == "prospeccao"
    assert e.chave == "contagem:Empresa X — Prospecção"
    um_novo = comparar(antes, {**antes, "p3": prospeccao("L3")})
    assert [x.texto for x in um_novo] == ["Empresa X — Prospecção: 1 lead novo."]
    movidos = comparar(antes, {"p1": prospeccao("L1", lista="A"), "p2": prospeccao("L2", lista="B")})
    assert [x.texto for x in movidos] == ["Empresa X — Prospecção: 2 mudaram de etapa."]
    assert comparar(antes, dict(antes)) == []


def test_parados_ignora_concluido_aguardando_e_prospeccao():
    agora = datetime(2026, 10, 27, 9, tzinfo=RIO)

    def parado(nome, dias, lista="A fazer", **kw):
        return cartao(nome, lista=lista, atividade=(datetime(2026, 10, 27, 12, tzinfo=timezone.utc)
                                                     - timedelta(days=dias)).isoformat().replace("+00:00", "Z"), **kw)

    itens = {"a": parado("A", 10), "b": parado("B", 8), "c": parado("C", 6), "d": parado("D", 20, "Aguardando resposta"),
             "e": parado("E", 30, quadro="Empresa X — Prospecção", contagem=True), "f": parado("F", 1),
             "g": parado("G", 40, "Concluído"), "h": parado("H", 50, feito=True)}
    assert parados(itens, agora) == [("A", 10), ("B", 8), ("C", 6)]


def test_coluna_ignorada_nao_conta_como_parada_nem_vencida():
    """Decisão de 28/10: coluna ignorada fica "só sem atraso"; o nome casa sem acento nem maiúscula."""
    agora = datetime(2026, 10, 27, 9, tzinfo=RIO)
    velho = "2026-09-01T12:00:00.000Z"
    itens = {"a": cartao("Vaga X", lista="Vagas recusadas", prazo=velho, atividade=velho),
             "b": cartao("Vaga Y", lista="Vagas recusadas", quadro="Projeto 2025", prazo=velho, atividade=velho)}
    ignoradas = {("projeto 2026", "VAGAS RECUSADAS")}
    assert parados(itens, agora, ignoradas=ignoradas) == [("Vaga Y", 56)]
    assert [n for n, _ in prazos(itens, agora, ignoradas=ignoradas)["vencidos"]] == ["Vaga Y"]


def test_entrar_em_coluna_ignorada_ainda_vira_evento():
    antes = {"a": cartao("Vaga X", lista="Candidatadas")}
    depois = {"a": cartao("Vaga X", lista="Vagas recusadas")}
    assert [e.texto for e in comparar(antes, depois)] == ["No Projeto 2026, Vaga X foi para Vagas recusadas."]


def test_prazo_de_madrugada_em_utc_e_hoje_no_rio():
    agora = datetime(2026, 10, 27, 9, tzinfo=RIO)
    p = prazos({"c1": cartao("Entrevista", prazo="2026-10-28T01:00:00.000Z"),
                "c2": cartao("Relatório", prazo="2026-10-28T15:00:00.000Z"),
                "c3": cartao("Inscrição", prazo="2026-10-26T15:00:00.000Z")}, agora)
    assert [n for n, _ in p["hoje"]] == ["Entrevista"] and p["hoje"][0][1].hour == 22
    assert [n for n, _ in p["amanha"]] == ["Relatório"] and [n for n, _ in p["vencidos"]] == ["Inscrição"]


def test_prazos_ignora_feito_prospeccao_e_longe_e_ordena():
    agora = datetime(2026, 10, 27, 9, tzinfo=RIO)
    p = prazos({"a": cartao("Tarde", prazo="2026-10-27T20:00:00.000Z"),
                "b": cartao("Cedo", prazo="2026-10-27T13:00:00.000Z"),
                "c": cartao("Feito", prazo="2026-10-27T13:00:00.000Z", feito=True),
                "d": cartao("Lead", prazo="2026-10-27T13:00:00.000Z", contagem=True),
                "e": cartao("Longe", prazo="2026-11-20T13:00:00.000Z"),
                "f": cartao("Sem prazo")}, agora)
    assert [n for n, _ in p["hoje"]] == ["Cedo", "Tarde"] and p["amanha"] == [] and p["vencidos"] == []


def test_prazo_vencido_hoje_fica_em_vencidos():
    agora = datetime(2026, 10, 27, 15, tzinfo=RIO)
    p = prazos({"a": cartao("Almoço", prazo="2026-10-27T15:00:00.000Z")}, agora)  # 12 h no Rio
    assert [n for n, _ in p["vencidos"]] == ["Almoço"] and p["hoje"] == []


def test_prazos_ignora_lista_concluida_mas_mantem_aguardando():
    agora = datetime(2026, 10, 27, 9, tzinfo=RIO)
    p = prazos({"a": cartao("Antigo", lista="Concluído", prazo="2026-09-01T12:00:00.000Z"),
                "b": cartao("Arquivado", lista="Arquivo morto", prazo="2026-09-01T12:00:00.000Z"),
                "c": cartao("Espera resposta", lista="Aguardando resposta", prazo="2026-10-27T20:00:00.000Z")}, agora)
    assert p["vencidos"] == [] and [n for n, _ in p["hoje"]] == ["Espera resposta"]


def test_contagem_so_pelo_nome_da_config_nao_pelo_prospec():
    itens, _ = ler_quadros("K", "T", ["Empresa X — Prospecção", "Projeto 2026"], buscar=trello_falso())
    assert itens["c2"]["contagem"] is False and itens["c1"]["contagem"] is False
    itens, _ = ler_quadros("K", "T", ["Empresa X — Prospecção", "Projeto 2026"], buscar=trello_falso(),
                           contagem=["projeto 2026"])
    assert itens["c1"]["contagem"] is True and itens["c2"]["contagem"] is False
