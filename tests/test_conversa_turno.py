import pytest

from src.conversa.regras_pc import ler_timer
from src.conversa.turno import CONFIRMACAO_VALE_S, JUNTAR_TURNO_S, Turno


def test_turno_em_dois_trechos_vira_um_pedido():
    t = Turno()
    t.abrir(0)
    t.adicionar("bota sora no kanata aí pra eu assistir na netflix", 1.0)
    t.adicionar("e depois bota um timer de desligar de uma hora", 2.5)
    pedido = ler_timer(t.texto())
    assert pedido.desligar and pedido.minutos == 60 and not pedido.ambiguo
    assert t.inicio() == 0 and t.aberto()


def test_fechar_guarda_o_texto_e_o_proximo_turno_comeca_do_zero():
    t = Turno()
    t.abrir(0)
    t.adicionar("abre o g1", 1)
    t.fechar(1.2)
    assert not t.aberto() and t.texto() == "abre o g1"  # a ferramenta pc lê o texto depois do fim do turno
    t.abrir(10)
    t.adicionar("que horas são", 11)
    assert t.texto() == "que horas são" and t.inicio() == 10


def test_transcricao_antes_do_inicio_do_turno_nao_se_perde():
    """Sem VAD, o pipecat abre o turno pela própria transcrição, que passa pelo filtro antes."""
    t = Turno()
    t.adicionar("abre o github", 5)
    t.abrir(5.1)
    assert t.texto() == "abre o github" and t.inicio() == 5 and t.aberto()


def test_fragmento_tardio_entra_no_laco_ate_3s():
    t = Turno()
    assert t.juntar_ao_laco("e bota um timer de uma hora", 10 + JUNTAR_TURNO_S, inicio_laco=10)
    assert not t.juntar_ao_laco("e bota um timer de uma hora", 10.1 + JUNTAR_TURNO_S, inicio_laco=10)
    assert not t.juntar_ao_laco("e bota um timer", 11, inicio_laco=None)


def test_turno_fechado_e_reaberto_antes_do_pc_nao_perde_a_netflix():
    # o Smart Turn fecha em "...na Netflix" e o usuário volta a falar antes de o cérebro chamar pc
    t = Turno()
    t.abrir(0)
    t.adicionar("bota sora no kanata aí pra eu assistir na netflix", 0.5)
    t.fechar(0.6)
    t.abrir(1.0)
    t.adicionar("e depois bota um timer de desligar de uma hora", 1.2)
    assert ler_timer(t.texto()).desligar and "netflix" in t.texto()
    assert t.inicio() == 0 and t.desde_abrir() == "e depois bota um timer de desligar de uma hora"


def test_reaberto_depois_do_prazo_comeca_do_zero():
    t = Turno()
    t.abrir(0)
    t.adicionar("que horas são", 0.5)
    t.fechar(1)
    t.abrir(1 + JUNTAR_TURNO_S)
    t.adicionar("abre o g1", 4.5)
    assert t.texto() == "abre o g1"


def test_consumir_devolve_o_pedido_e_zera():
    t = Turno()
    t.abrir(0)
    t.adicionar("abre o g1", 0.5)
    t.fechar(0.6)
    assert t.consumir() == "abre o g1"
    assert t.texto() == "" and t.inicio() is None
    t.abrir(1.0)  # dentro do prazo, mas o pedido já foi para o laço: não junta
    t.adicionar("e o tempo amanhã?", 1.2)
    assert t.texto() == "e o tempo amanhã?" and t.inicio() == 1.0


def test_trecho_atrasado_com_o_turno_fechado_junta_ao_pedido():
    t = Turno()
    t.abrir(0)
    t.adicionar("bota sora no kanata na netflix", 0.5)
    t.fechar(0.6)
    t.adicionar("e um timer de desligar de uma hora", 1.0)  # sem abrir: o Whisper entregou depois do fim
    assert "netflix" in t.texto() and ler_timer(t.texto()).desligar


def _turno_nao_consumido(pedido, fim=1.0):
    t = Turno()
    t.abrir(0)
    t.adicionar(pedido, 0.5)
    t.fechar(fim)
    return t


def test_confirmacao_curta_repete_o_pedido_anterior():
    t = _turno_nao_consumido("abre o bloco de notas")
    t.abrir(10)  # o cérebro perguntou "quer que eu abra?" e o usuário respondeu
    t.adicionar("pode sim", 10.5)
    t.fechar(11)
    assert t.consumir(agora=12) == "abre o bloco de notas"
    t.abrir(20)
    t.adicionar("pode", 20.5)
    assert t.consumir(agora=21) == "pode"  # o pedido anterior foi usado uma vez só


def test_confirmacao_depois_da_janela_fica_como_esta():
    t = _turno_nao_consumido("abre o bloco de notas")
    t.abrir(10)
    t.adicionar("pode", 10.5)
    assert t.consumir(agora=1.0 + CONFIRMACAO_VALE_S + 1) == "pode"


def test_pedido_novo_apos_um_nao_consumido_leva_so_o_novo():
    t = _turno_nao_consumido("abre o bloco de notas")
    t.abrir(10)
    t.adicionar("abre o g1", 10.5)
    assert t.consumir(agora=11) == "abre o g1"


def test_palavra_curta_que_nao_e_confirmacao_nao_muda():
    t = _turno_nao_consumido("abre o bloco de notas")
    t.abrir(10)
    t.adicionar("calculadora", 10.5)
    assert t.consumir(agora=11) == "calculadora"


def test_confirmacao_repetida_mantem_o_pedido_original_e_desde_abrir_nao_muda():
    t = _turno_nao_consumido("abre o bloco de notas")
    t.abrir(10)
    t.adicionar("sim", 10.5)
    t.fechar(10.6)
    t.abrir(20)
    t.adicionar("pode", 20.5)
    assert t.desde_abrir() == "pode"
    assert t.consumir(agora=21) == "abre o bloco de notas"


def test_inicio_da_voz_e_o_do_trecho_de_audio_transcrito():
    """11/11: o eco da pergunta abriu um turno; a resposta, em menos de JUNTAR_TURNO_S, junta a ele e `inicio()` ficava velho."""
    t = Turno()
    t.abrir(10.0)
    t.adicionar("posso abrir o site", 10.5, 10.0)
    t.fechar(11.0)
    t.abrir(12.0)
    t.adicionar("sim senhor", 12.6, 12.0)
    assert t.inicio() == 10.0 and t.inicio_da_voz() == 12.0


def test_eco_que_chega_depois_de_o_usuario_comecar_leva_o_inicio_do_proprio_trecho():
    t = Turno()
    t.abrir(10.0)
    t.fechar(10.8)
    t.abrir(11.2)  # o usuário já começou a responder
    t.adicionar("posso abrir o site", 11.5, 10.0)  # a transcrição do eco chega só agora
    assert t.inicio_da_voz() == 10.0
    t.adicionar("sim", 12.0, 11.2)
    assert t.inicio_da_voz() == 11.2


def test_sem_inicio_do_trecho_devolve_none():
    t = Turno()
    t.abrir(10.0)
    t.adicionar("sim", 10.6)
    assert t.inicio_da_voz() is None  # quem julga decide (a forte trata como eco)
