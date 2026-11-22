import asyncio

from src.conversa import pergunta as P
from src.conversa.laco import FORTE_MAX_CARACTERES, MARGEM_ECO_LIVRE_S, MARGEM_ECO_S, PERGUNTA_TETO_S, RESPOSTA_S


class Relogio:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def montar(som=False, ao_mudar=None):
    rel, ditas = Relogio(), []

    async def literal(t):
        ditas.append(("literal", t))

    async def livre(t):
        ditas.append(("livre", t))

    async def tocando():
        return som

    return P.Pergunta(literal, livre, tocando, rel, ao_mudar), rel, ditas


async def avancar(rel, s):
    rel.t += s
    await asyncio.sleep(0.2)


def rodar(coro):
    return asyncio.run(coro)


def test_prazo_comeca_no_fim_da_fala():
    async def cena():
        p, rel, _ = montar()
        t = asyncio.ensure_future(p.perguntar("Qual?", "livre"))
        await asyncio.sleep(0.1)
        await avancar(rel, 60)  # a fala demorou: ainda não conta
        assert not t.done()
        p.ao_terminar_fala(rel.t)
        await avancar(rel, RESPOSTA_S - 1)
        assert not t.done()
        await avancar(rel, 2)
        assert await t is None

    rodar(cena())


def test_teto_duro_sem_fim_da_fala():
    async def cena():
        p, rel, _ = montar()
        t = asyncio.ensure_future(p.perguntar("Qual?", "livre"))
        await asyncio.sleep(0.1)
        await avancar(rel, PERGUNTA_TETO_S + 1)
        assert await t is None and not p.ativa()

    rodar(cena())


def test_teto_duro_vale_com_repeticao():
    async def cena():
        p, rel, ditas = montar()
        t = asyncio.ensure_future(p.perguntar("Qual?", "livre"))
        await asyncio.sleep(0.1)
        p.fala_cortada()  # sem ao_terminar_fala: só o teto encerra
        await avancar(rel, PERGUNTA_TETO_S + 1)
        assert await t is None and len(ditas) == 1

    rodar(cena())


def test_fala_cortada_repete_uma_vez():
    async def cena():
        p, rel, ditas = montar()
        t = asyncio.ensure_future(p.perguntar("Qual?", "livre"))
        await asyncio.sleep(0.1)
        p.fala_cortada()
        p.ao_terminar_fala(rel.t)
        await avancar(rel, RESPOSTA_S + 1)
        assert len(ditas) == 2 and not t.done()  # repetiu
        p.ao_terminar_fala(rel.t)
        p.fala_cortada()  # cortada de novo: não repete outra vez
        await avancar(rel, RESPOSTA_S + 1)
        assert await t is None and len(ditas) == 2

    rodar(cena())


def test_eco_antes_da_margem_nao_conta():
    async def cena():
        p, rel, _ = montar()
        t = asyncio.ensure_future(p.perguntar("Qual a cor?", "livre"))
        await asyncio.sleep(0.1)
        fim = rel.t
        p.ao_terminar_fala(fim)
        assert p.oferecer("qual a cor", fim + MARGEM_ECO_LIVRE_S - 0.1) is True  # consumida, mas não é resposta
        await asyncio.sleep(0.1)
        assert not t.done()
        assert p.oferecer("a segunda", fim + MARGEM_ECO_LIVRE_S + 0.1) is True
        assert await t == "a segunda"

    rodar(cena())


def test_resposta_livre_logo_depois_da_pergunta_vale_e_a_forte_continua_com_margem_larga():
    """11/11: o "sim" a menos de 1 s do fim da pergunta livre era engolido (Teste 2)."""
    async def cena():
        p, rel, _ = montar()
        t = asyncio.ensure_future(p.perguntar("Posso abrir?", "livre"))
        await asyncio.sleep(0.1)
        fim = rel.t
        p.ao_terminar_fala(fim)
        assert p.oferecer("sim", fim + 0.5) is True
        assert await t == "sim"
        f = asyncio.ensure_future(p.perguntar("Para confirmar, diga: pode enviar.", "forte"))
        await asyncio.sleep(0.1)
        fim = rel.t
        p.ao_terminar_fala(fim)
        p.oferecer("pode enviar", fim + 0.5)  # na forte a margem larga fica: eco
        await asyncio.sleep(0.1)
        assert not f.done()
        f.cancel()

    rodar(cena())


def test_sem_pergunta_aberta_nao_consome():
    p, _, _ = montar()
    assert p.oferecer("oi", 0) is False and not p.ativa()


def test_forte_so_aceita_pode_enviar():
    async def responder(frase):
        p, rel, _ = montar()
        t = asyncio.ensure_future(p.perguntar("Vou enviar", "forte"))
        await asyncio.sleep(0.1)
        p.ao_terminar_fala(rel.t)
        p.oferecer(frase, rel.t + MARGEM_ECO_S + 0.1)
        return await t

    assert rodar(responder("pode enviar")) == "pode enviar"
    for frase in ("sim", "ok", "pode", "sim, pode enviar o resto"):
        assert rodar(responder(frase)) is None


def test_forte_fala_literal_e_livre_fala_normal():
    async def cena():
        p, rel, ditas = montar()
        for tipo in ("forte", "livre"):
            t = asyncio.ensure_future(p.perguntar("X", tipo))
            await asyncio.sleep(0.1)
            p.cancelar()
            await t
        assert [d[0] for d in ditas] == ["literal", "livre"]

    rodar(cena())


def test_som_tocando_recusa_forte():
    async def cena(som):
        p, rel, _ = montar(som)
        t = asyncio.ensure_future(p.perguntar("Vou enviar", "forte"))
        await asyncio.sleep(0.1)
        p.ao_terminar_fala(rel.t)
        p.oferecer("pode enviar", rel.t + MARGEM_ECO_S + 0.1)
        return await t

    assert rodar(cena(True)) is None
    assert rodar(cena(False)) == "pode enviar"


def test_som_que_termina_antes_da_resposta_recusa_forte():
    async def cena():
        estado = {"som": True}
        rel, ditas = Relogio(), []

        async def fala(t):
            ditas.append(t)

        async def tocando():
            return estado["som"]

        p = P.Pergunta(fala, fala, tocando, rel)
        t = asyncio.ensure_future(p.perguntar("Vou enviar", "forte"))
        await asyncio.sleep(0.1)
        p.ao_terminar_fala(rel.t)
        await asyncio.sleep(0.2)  # o som toca durante a espera e acaba antes da transcrição
        estado["som"] = False
        p.oferecer("pode enviar", rel.t + MARGEM_ECO_S + 0.1)
        return await t

    assert rodar(cena()) is None


def test_fala_descartada_devolve_none():
    async def cena():
        async def descarta(t):
            return False

        p = P.Pergunta(descarta, descarta, lambda: False, Relogio())
        assert await p.perguntar("X", "livre") is None and not p.ativa()

    rodar(cena())


def test_cancelar_para_a_pergunta():
    async def cena():
        p, _, _ = montar()
        t = asyncio.ensure_future(p.perguntar("X", "livre"))
        await asyncio.sleep(0.1)
        p.cancelar()
        assert await t is None and not p.ativa()

    rodar(cena())


def test_link_falado_por_extenso():
    f = P.montar_pergunta_envio("Ana", "veja https://evil.com/x?a=1 agora", 0, "")
    assert f == "Vou enviar para Ana: veja link para evil ponto com agora. Para confirmar, diga: pode enviar."
    assert "www" not in P.montar_pergunta_envio("Ana", "www.exemplo.com.br", 0, "")


def test_link_falado_userinfo_pontuacao_e_sem_esquema():
    f = lambda t: P.montar_pergunta_envio("Ana", t, 0, "")
    assert "google ponto com arroba evil ponto com" in f("veja https://google.com@evil.com/x")
    assert "google ponto com dois pontos x arroba evil ponto com" in f("https://google.com:x@evil.com")
    assert "link para evil ponto com." in f("https://Evil.COM.")
    assert "link para bit ponto ly, " in f("veja bit.ly/abc, ok")
    assert "link para evil ponto com" in f("https://evil.com:8080/x")


def test_numeros_com_ponto_e_barra_nao_viram_link():
    for txt in ("custa R$ 1.000/mês", "nota 8.5/10", "dia 07.11/2026"):
        assert P.montar_pergunta_envio("Ana", txt, 0, "") == f"Vou enviar para Ana: {txt}. Para confirmar, diga: pode enviar."


def test_pergunta_de_envio_recusa_longo_anexo_e_cc():
    assert P.montar_pergunta_envio("Ana", "oi", 0, "") is not None
    assert P.montar_pergunta_envio("Ana", "a" * (FORTE_MAX_CARACTERES + 1), 0, "") is None
    assert P.montar_pergunta_envio("Ana", "oi", 1, "") is None
    assert P.montar_pergunta_envio("Ana", "oi", 0, "chefe@x.com") is None


def _cena_resposta(tipo, falas, trechos, resposta_inicio_depois=True):
    """`falas`: [(início, fim)] do GROOV (a 1ª é a pergunta); `trechos`: [(texto, início do áudio)] na ordem de chegada."""
    from src.conversa.turno import Turno

    async def cena():
        p, rel, _ = montar()
        t = Turno()
        task = asyncio.ensure_future(p.perguntar("Pergunta?", tipo))
        await asyncio.sleep(0.1)
        for _, fim in falas:
            p.ao_terminar_fala(fim)
        for texto, inicio in trechos:
            rel.t = inicio + 1
            t.abrir(inicio)
            t.adicionar(texto, rel.t, inicio)
            p.oferecer(texto, t.inicio_da_voz())
        rel.t = 100 + PERGUNTA_TETO_S + 1  # sem resposta aceita, o teto encerra
        await asyncio.sleep(0.2)
        return await task

    return rodar(cena())


def test_eco_sem_texto_e_depois_sim_e_aceito():
    assert _cena_resposta("livre", [(100, 103)], [("sim", 104)]) == "sim"


def test_eco_transcrito_depois_de_o_usuario_comecar_e_rejeitado():
    # o eco (áudio de 101) chega depois de o usuário começar a falar (104): vale o início do próprio trecho
    assert _cena_resposta("livre", [(100, 103)], [("posso abrir o bloco de notas", 101)]) is None


def test_eco_de_pode_enviar_nao_confirma_sozinho():
    assert _cena_resposta("forte", [(100, 105)], [("pode enviar", 101)]) is None


def test_forte_logo_apos_o_fim_da_fala_ainda_e_eco():
    assert _cena_resposta("forte", [(100, 105)], [("pode enviar", 105.5)]) is None
    assert _cena_resposta("forte", [(100, 105)], [("pode enviar", 106.5)]) == "pode enviar"


def test_usuario_fala_por_cima_do_groov_e_rejeitado():
    assert _cena_resposta("livre", [(100, 110)], [("sim", 105)]) is None


def test_groov_fala_duas_vezes_e_a_resposta_depois_da_segunda_vale():
    assert _cena_resposta("livre", [(100, 103), (105, 108)], [("sim", 109)]) == "sim"
    assert _cena_resposta("livre", [(100, 103), (105, 108)], [("frase de andamento", 106)]) is None


def test_forte_sem_marca_do_stt_e_eco_e_livre_usa_a_chegada():
    async def cena(tipo):
        p, rel, _ = montar()
        task = asyncio.ensure_future(p.perguntar("Pergunta?", tipo))
        await asyncio.sleep(0.1)
        p.ao_terminar_fala(rel.t)
        rel.t += 2
        p.oferecer("pode enviar", None)
        rel.t += RESPOSTA_S + 1
        await asyncio.sleep(0.2)
        return await task

    assert rodar(cena("forte")) is None
    assert rodar(cena("livre")) == "pode enviar"


def test_eco_da_frase_de_andamento_enquanto_ela_fala_e_rejeitado():
    async def cena():
        p, rel, _ = montar()
        task = asyncio.ensure_future(p.perguntar("Pergunta?", "livre"))
        await asyncio.sleep(0.1)
        p.ao_terminar_fala(rel.t)  # fim da pergunta em 100
        rel.t += 5
        p.ao_comecar_a_falar()  # frase de andamento começa em 105 e ainda não acabou
        assert p.oferecer("andamento", 110)  # consumida, mas é eco
        assert not task.done()
        p.ao_terminar_fala(rel.t + 8)  # acaba em 113
        assert p.oferecer("sim", 114.0)
        assert await task == "sim"

    rodar(cena())


def test_fala_interrompida_fixa_o_fim_na_hora_do_corte():
    async def cena():
        p, rel, _ = montar()
        task = asyncio.ensure_future(p.perguntar("Pergunta?", "livre"))
        await asyncio.sleep(0.1)
        p.ao_terminar_fala(rel.t)
        rel.t += 5
        p.ao_comecar_a_falar()
        rel.t += 2
        p.fala_cortada(rel.t)  # cortada em 107: o fim é aqui
        assert p.oferecer("sim", 108.0)
        assert await task == "sim"

    rodar(cena())


# ---- 12/11: resposta livre julgada pelo conteúdo (o VAD juntou o rabo da fala do GROOV com a resposta) ----

def _livre(pergunta, texto, inicio, fim=100.0):
    async def cena():
        p, rel, _ = montar()
        task = asyncio.ensure_future(p.perguntar(pergunta, "livre"))
        await asyncio.sleep(0.1)
        p.ao_terminar_fala(fim)
        rel.t = fim + 1
        assert p.oferecer(texto, inicio) is True
        rel.t = 100 + PERGUNTA_TETO_S + 1
        await asyncio.sleep(0.2)
        return await task

    return rodar(cena())


GLOBO = "Posso abrir oglobo.globo.com?"


def test_trecho_com_o_fim_da_pergunta_colado_na_resposta_vale_o_resto():
    assert _livre(GLOBO, "posso abrir o globo pode abrir", 97.0) == "pode abrir"


def test_eco_puro_da_pergunta_e_eco_mesmo_depois_do_fim():
    assert _livre(GLOBO, "Posso abrir o globo?", 101.0) is None
    assert _livre(GLOBO, "posso abrir o globo", 97.0) is None


def test_sim_um_pouco_antes_do_fim_da_fala_vale_e_bem_no_meio_nao():
    assert _livre(GLOBO, "sim", 99.5) == "sim"
    assert _livre(GLOBO, "pode abrir", 99.7) == "pode abrir"
    assert _livre(GLOBO, "sim", 95.0) is None  # começou 5 s antes do fim, sem palavra da fala: tempo manda


def test_diagnostico_so_com_numeros(caplog):
    caplog.set_level("INFO", logger="groov.pergunta")
    _livre(GLOBO, "posso abrir o globo pode abrir", 97.0)
    msg = [r.getMessage() for r in caplog.records if "ini=" in r.getMessage()][0]
    assert "aceita" in msg and "pode" not in msg and "globo" not in msg


SIMNAO = "Posso abrir oglobo.globo.com? Diga sim ou não."


def test_sim_ou_nao_com_palavra_da_pergunta_nao_vira_eco():
    assert _livre(SIMNAO, "sim abrir", 101.0) == "sim abrir"
    assert _livre(SIMNAO, "não abrir", 101.0) == "não abrir"


def test_nao_solto_logo_antes_do_fim_e_rabo_da_fala_mas_depois_vale():
    assert _livre(SIMNAO, "não", 99.5) is None
    assert _livre(SIMNAO, "não", 100.5) == "não"


# ---- Tarefa 7: pergunta na tela e resposta direta (clique ou texto) ----

def montar_com_tela(falha=False):
    vistos = []

    async def ao_mudar(d):
        vistos.append(d)
        if falha:
            raise RuntimeError("canal fechado")

    p, rel, ditas = montar(ao_mudar=ao_mudar)
    return p, rel, ditas, vistos


def test_ao_mudar_recebe_a_pergunta_ao_abrir_e_none_ao_fechar():
    async def cena():
        p, rel, _, vistos = montar_com_tela()
        t = asyncio.ensure_future(p.perguntar("Qual?", "livre", ("A", "B")))
        await asyncio.sleep(0.1)
        assert vistos == [{"texto": "Qual?", "opcoes": ["A", "B"], "so_voz": False, "prazo_s": PERGUNTA_TETO_S}]
        await avancar(rel, PERGUNTA_TETO_S + 1)
        assert await t is None and vistos[-1] is None and len(vistos) == 2

    rodar(cena())


def test_forte_abre_so_voz_e_sem_opcoes():
    async def cena():
        p, rel, _, vistos = montar_com_tela()
        t = asyncio.ensure_future(p.perguntar("Vou enviar. Diga: pode enviar.", "forte", ("A", "B")))
        await asyncio.sleep(0.1)
        assert vistos[0]["so_voz"] is True and vistos[0]["opcoes"] == []
        await avancar(rel, PERGUNTA_TETO_S + 1)
        await t

    rodar(cena())


def test_responder_direto_na_livre_resolve_antes_do_fim_da_fala_sem_eco():
    async def cena():
        p, rel, _, vistos = montar_com_tela()
        t = asyncio.ensure_future(p.perguntar("Qual?", "livre", ("A", "B")))
        await asyncio.sleep(0.1)  # a fala nem terminou (ao_terminar_fala não foi chamado)
        assert p.responder_direto("B") is True
        assert await t == "B" and vistos[-1] is None

    rodar(cena())


def test_responder_direto_na_forte_recusa_e_a_pergunta_segue_aberta():
    async def cena():
        p, rel, _, vistos = montar_com_tela()
        t = asyncio.ensure_future(p.perguntar("Diga: pode enviar.", "forte"))
        await asyncio.sleep(0.1)
        assert p.responder_direto("pode enviar") is False
        assert p.ativa() and not t.done()
        p.cancelar()
        assert await t is None

    rodar(cena())


def test_responder_direto_sem_pergunta_aberta_e_falso():
    p, _, _ = montar()
    assert p.responder_direto("sim") is False


def test_falha_do_ao_mudar_nao_quebra_a_pergunta(caplog):
    async def cena():
        p, rel, _, vistos = montar_com_tela(falha=True)
        t = asyncio.ensure_future(p.perguntar("Qual?", "livre"))
        await asyncio.sleep(0.1)
        assert p.responder_direto("sim") is True
        assert await t == "sim" and len(vistos) == 2  # tentou abrir e fechar

    caplog.set_level("INFO", logger="groov.pergunta")
    rodar(cena())
    assert "canal fechado" not in caplog.text and "RuntimeError" in caplog.text
