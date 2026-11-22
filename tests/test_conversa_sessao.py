from src.conversa.sessao import Estado, Sessao


def acordada(t=0.0):
    s = Sessao()
    s.acordar(t)
    s.pronto(t)
    return s


def test_fluxo_dormindo_acordando_conversando():
    s = Sessao()
    assert s.estado is Estado.DORMINDO
    s.acordar(0)
    assert s.estado is Estado.ACORDANDO
    s.pronto(1)
    assert s.estado is Estado.CONVERSANDO


def test_dormir_e_acordar_esquecem_fala_sem_aviso_de_fim():
    s = acordada(0)
    s.comecou_a_falar(1)
    s.dormir(2)
    s.acordar(100)
    s.pronto(100)
    assert s.deve_ociar(120)  # a fala da sessão anterior não segura esta
    s.comecou_a_falar(150)
    s.ociar()
    s.dormir()
    s.pronto(200)
    assert s.deve_ociar(220)


def test_nao_fica_ocioso_enquanto_fala_e_o_silencio_conta_do_fim_dela():
    """Rodada de 09/11: a leitura do G1 passou do tempo e ele dormiu no meio, escondendo a janela."""
    s = acordada(0)
    s.comecou_a_falar(0)
    for t in (45, 600, 5000):
        assert not s.deve_ociar(t)
    s.parou_de_falar(5000)
    assert not s.deve_ociar(5019.9) and s.deve_ociar(5020)


def test_atividade_zera_o_relogio():
    s = acordada(0)
    s.atividade(30)
    assert not s.deve_ociar(49.9) and s.deve_ociar(50)


def test_tarefa_segura_acordado_e_estoura_em_300s():
    s = acordada(0)
    assert s.iniciar_tarefa(10)
    assert not s.deve_ociar(100)
    assert not s.tarefa_estourou(309.9)
    assert s.tarefa_estourou(310)


def test_uma_tarefa_por_vez():
    s = acordada(0)
    assert s.iniciar_tarefa(1)
    assert not s.iniciar_tarefa(2)
    s.concluir_tarefa("ok")
    assert s.iniciar_tarefa(3)


def test_resultado_apos_tchau_fica_guardado_para_o_proximo_hey_jarvis():
    s = acordada(0)
    s.iniciar_tarefa(1)
    s.dormir()
    s.concluir_tarefa("A capital é Camberra.")
    assert s.pegar_resultado_guardado() == "A capital é Camberra."
    assert s.pegar_resultado_guardado() is None


def test_cancelar_tarefa_libera():
    s = acordada(0)
    s.iniciar_tarefa(1)
    s.cancelar_tarefa()
    assert s.iniciar_tarefa(2)


def test_pausa_depois_de_dormir():
    s = Sessao()
    assert s.pode_acordar(0)
    s.dormir(100)
    assert s.estado is Estado.DORMINDO and not s.pode_acordar(104.9) and s.pode_acordar(105)
    s.dormir()  # sono por silêncio ou falha ao acordar: sem pausa nova
    assert s.pode_acordar(105)


def test_relogio_do_laco_pausa_na_espera():
    s = Sessao(teto_tarefa=180)
    s.iniciar_tarefa(0, dono="laco")
    s.pausar_relogio(100)
    s.retomar_relogio(170)
    assert not s.tarefa_estourou(240)  # 170 s de ação
    assert s.tarefa_estourou(251)


def test_relogio_pausado_nao_corre():
    s = Sessao(teto_tarefa=180)
    s.iniciar_tarefa(0, dono="laco")
    s.pausar_relogio(100)
    assert not s.tarefa_estourou(500)  # ainda esperando a resposta do usuário


def test_tarefa_do_hermes_continua_com_relogio_corrido():
    s = Sessao(teto_tarefa=180)
    assert s.iniciar_tarefa(0) and s.dono == "hermes"
    s.pausar_relogio(10)
    s.retomar_relogio(100)
    assert s.tarefa_estourou(180)


def test_dono_da_vaga():
    s = Sessao()
    assert s.dono is None
    assert s.iniciar_tarefa(0, dono="laco") and s.dono == "laco"
    assert not s.iniciar_tarefa(1)  # o Hermes não entra com o laço rodando
    s.cancelar_tarefa()
    assert s.dono is None
    assert s.iniciar_tarefa(2) and s.dono == "hermes"
    s.concluir_tarefa("ok")
    assert s.dono is None


def test_relogio_novo_a_cada_tarefa():
    s = Sessao(teto_tarefa=180)
    s.iniciar_tarefa(0, dono="laco")
    s.pausar_relogio(10)
    s.cancelar_tarefa()
    s.iniciar_tarefa(20, dono="laco")
    assert s.tarefa_estourou(200)  # a pausa da tarefa anterior não vale


def test_midia_tocando_desliga_quando_novo_pc_comeca():
    s = acordada(0)
    s.midia_tocando = True
    s.iniciar_tarefa(1)  # pesquisa do Hermes não mexe na mídia
    assert s.midia_tocando
    s.concluir_tarefa("ok")
    s.iniciar_tarefa(2, dono="laco")
    assert not s.midia_tocando


def test_fica_ocioso_apos_20s_sem_trabalho():
    s = acordada(0)
    assert not s.deve_ociar(19.9) and s.deve_ociar(20.0)


def test_nao_fica_ocioso_falando_nem_com_tarefa():
    s = acordada(0); s.comecou_a_falar(1)
    assert not s.deve_ociar(100)
    s.parou_de_falar(100); s.iniciar_tarefa(101, "laco")
    assert not s.deve_ociar(500)


def test_confirmacao_pendente_segura_o_ocioso():
    s = acordada(0); s.segurar(30)
    assert not s.deve_ociar(29.9) and s.deve_ociar(30.0)


def test_fala_captada_com_midia_nao_conta():
    s = acordada(0); s.midia_tocando = True
    s.atividade(15, fala_do_usuario=True)
    assert s.deve_ociar(20.0)


def test_fala_longa_do_usuario_nao_deixa_ficar_ocioso():
    s = acordada(0); s.comecou_a_ouvir(1)
    assert not s.deve_ociar(60)
    s.parou_de_ouvir(60)
    assert not s.deve_ociar(79.9) and s.deve_ociar(80.0)


def test_com_midia_a_fala_captada_nao_segura():
    s = acordada(0); s.midia_tocando = True; s.comecou_a_ouvir(1)
    assert s.deve_ociar(20.0)


def test_fala_dele_no_ocioso_nao_zera_os_10_min():
    s = acordada(0); s.ociar()
    s.comecou_a_falar(300); s.parou_de_falar(305)   # aviso de timer ou despedida
    assert s.estado is Estado.OCIOSO and s.deve_desligar(600.0)


def test_ociar_nao_zera_o_relogio_e_desliga_em_10_min():
    s = acordada(0); s.ociar()
    assert s.estado is Estado.OCIOSO and s.desliga_em() == 600.0
    assert not s.deve_desligar(599.9) and s.deve_desligar(600.0)


def test_so_desliga_sozinho_no_ocioso_e_sem_tarefa():
    s = acordada(0)
    assert not s.deve_desligar(10_000)
    s.iniciar_tarefa(1, "hermes"); s.ociar()
    assert not s.deve_desligar(10_000)


def test_ociar_a_pedido_ensurdece_o_despertador():
    s = acordada(0); s.ociar(100)
    assert not s.pode_acordar(104.9) and s.pode_acordar(105.0)
    t = acordada(0); t.ociar()
    assert t.pode_acordar(0.1)


def test_retomar_volta_a_conversar():
    s = acordada(0); s.ociar(); s.retomar(300)
    assert s.estado is Estado.CONVERSANDO
    assert not s.deve_ociar(319.9) and s.deve_ociar(320.0)


def test_retomar_so_vale_no_ocioso():
    s = Sessao(); s.retomar(1)
    assert s.estado is Estado.DORMINDO


def test_resultado_de_tarefa_fica_guardado_no_ocioso():
    s = acordada(0); s.iniciar_tarefa(1, "hermes"); s.ociar(); s.concluir_tarefa("achei")
    assert s.pegar_resultado_guardado() == "achei"


def test_segurar_de_um_ciclo_nao_vale_no_proximo():
    s = acordada(0); s.segurar(5000)
    s.dormir(); s.acordar(2000); s.pronto(2000)
    assert s.deve_ociar(2020.0)


def test_ociar_so_vale_conversando():
    for preparar in (lambda s: None, lambda s: s.acordar(0)):
        s = Sessao(); preparar(s); s.ociar(5)
        assert s.estado in (Estado.DORMINDO, Estado.ACORDANDO) and s.pode_acordar(5)


def test_nao_desliga_falando_e_desliga_assim_que_a_fala_acaba():
    s = acordada(0); s.ociar()
    s.comecou_a_falar(599)
    assert not s.deve_desligar(601)
    s.parou_de_falar(602)
    assert s.deve_desligar(602)


def test_ociar_devolve_se_mudou():
    assert acordada(0).ociar() is True
    t = Sessao()
    assert t.ociar() is False
    t.acordar(0)
    assert t.ociar() is False
