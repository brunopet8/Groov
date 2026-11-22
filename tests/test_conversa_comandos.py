from datetime import datetime

import pytest

from src.conversa.comandos import comando_local, descartar, frase_hora, normalizar, nucleo, pode_enviar, sim_ou_nao


@pytest.mark.parametrize("fala, esperado", [
    ("Sim.", "sim"), ("Sim, Jarvis.", "sim"), ("Confirmo!", "sim"), ("Pode.", "sim"), ("sim, confirmo", "sim"),
    ("Não.", "nao"), ("Cancela.", "nao"), ("Não, Jarvis.", "nao"),
    ("Sim, mas antes me diz a hora", None), ("Assim não dá", None), ("simples", None), ("o que tenho para hoje", None),
    ("Confirma.", None), ("Confirma, senhor?", None),  # eco da própria pergunta do GROOV não pode confirmar
    # 11/11: resposta natural vale pela 1ª palavra, com só enchimento depois
    ("Sim, senhor.", "sim"), ("Isso.", "sim"), ("Pode abrir.", "sim"), ("Claro.", "sim"), ("Pode sim.", "sim"),
    ("Sim, pode abrir", "sim"), ("Claro que sim", "sim"), ("Não, senhor.", "nao"), ("Deixa.", "nao"), ("Deixa pra lá", "nao"),
    ("Claro que não", None), ("Pode não", None), ("Isso não", None), ("Certo, não", None), ("Ok, não", None), ("Pode cancelar", None),
    ("Isso, mas antes me diz a hora", None), ("Não, mas me diz a hora", None), ("Encerro por hoje, senhor?", None),
])
def test_sim_ou_nao_so_com_a_frase_inteira(fala, esperado):
    """Uma frase maior que só contém "sim" não pode guardar nada."""
    assert sim_ou_nao(fala) == esperado


@pytest.mark.parametrize("fala,esperado", [
    ("Não, você acertou", True), ("Você tinha acertado, pode continuar tocando", True), ("É isso mesmo", True),
    ("Pode continuar", True), ("Isso mesmo, senhor", True), ("Não, é outra", False), ("Não", False), ("Sim", False),
    # revisão 14/11: negação logo antes não é acerto
    ("Não é isso", False), ("Não, não é isso", False), ("Você não acertou", False), ("Não tá certo", False),
])
def test_acertou_so_para_a_pergunta_do_que_tocou(fala, esperado):
    from src.conversa.comandos import acertou
    assert acertou(fala) is esperado


@pytest.mark.parametrize("fala,esperado", [
    ("Tchau, Javis.", "tchau"), ("Tchau Jarvis", "tchau"), ("tchau", "tchau"),
    ("Jarvis, desliga!", "desligar"), ("Jarvis desligar", "desligar"), ("Djarvis, desligar.", "desligar"),
    ("Que horas são?", "hora"), ("Jarvis, que horas são", "hora"),
    ("valeu", None), ("tchau pessoal", None), ("não desliga o jarvis", None),
    ("que horas são em Tóquio?", None),
    ("Jarvis, novidades?", "novidades"), ("Quais as novidades, Jarvis?", "novidades"),
    ("O que tenho pra hoje?", "hoje"), ("Jarvis, o que eu tenho para hoje?", "hoje"),
    ("novidades do Flamengo", None),
])
def test_comando_local_casa_frase_inteira(fala, esperado):
    assert comando_local(fala) == esperado


@pytest.mark.parametrize("fala, esperado", [
    ("Volte daqui a pouco, Jarvis.", "tchau"), ("Vá embora, Jarvis!", "desligar"),
    ("Jarvis, pode desligar agora.", "desligar"), ("Sai do meu PC.", "desligar"), ("Até amanhã, Jarvis.", "desligar"),
    ("Ok Jarvis, pode descansar.", "tchau"), ("Jarvis, me diz as horas.", "hora"), ("Por hoje é só, Jarvis.", "desligar"),
    ("Até daqui a pouco.", "tchau"), ("Jarvis, depois te chamo.", "tchau"),
])
def test_intencao(fala, esperado):
    """O núcleo da frase (sem jarvis, pode, por favor...) decide, não a frase exata."""
    assert comando_local(fala) == esperado


@pytest.mark.parametrize("fala", [
    "Não vá embora, Jarvis.", "Não desliga.", "Desliga a luz.", "A Maria vai embora amanhã.",
    "Como se diz tchau em inglês?", "Tchau pessoal.", "Encerra o card no Trello.", "Boa noite, Jarvis.",
    "Pode.", "Jarvis.", "Não precisa desligar ainda.",
])
def test_armadilhas_nao_disparam(fala):
    assert comando_local(fala) is None


def test_nucleo_tira_o_enchimento():
    assert nucleo("Ok Jarvis, pode desligar agora, por favor!") == "desligar"


def test_normalizar_corrige_jarvis():
    assert normalizar("  Javis,  tudo bem?! ") == "jarvis tudo bem"


def test_groov_e_as_grafias_do_whisper():
    assert comando_local("Groov, que horas são") == "hora"
    assert comando_local("gruv desliga") == "desligar"
    assert normalizar("Groove, tchau") == "groov tchau"


def test_frase_hora():
    assert frase_hora(datetime(2026, 10, 22, 10, 5)) == "São 10 horas e 5 minutos, senhor."
    assert frase_hora(datetime(2026, 10, 22, 13, 0)) == "São 13 horas em ponto, senhor."
    assert frase_hora(datetime(2026, 10, 22, 1, 1)) == "É 1 hora e 1 minuto, senhor."


@pytest.mark.parametrize("fala", ["", "  ", "a", "Obrigado.", "Legendas pela comunidade Amara.org",
                                  "Inscreva-se no canal"])
def test_descartar_alucinacoes(fala):
    assert descartar(fala)


def test_nao_descarta_fala_real():
    assert not descartar("Como está o clima hoje?")


@pytest.mark.parametrize("fala", ["Pode ir.", "Ok, pode ir então.", "É só isso?", "Até agora?", "Até aí."])
def test_respostas_comuns_nao_viram_despedida(fala):
    """Revisão 28/10: 'pode ir' (vá em frente) e 'é só isso?' no meio da conversa faziam o GROOV dormir."""
    assert comando_local(fala) is None


@pytest.mark.parametrize("fala", ["Sim, desliga.", "Pode encerrar.", "Sim, pode desligar."])
def test_confirmacao_natural_desliga(fala):
    """Com o 'Encerro por hoje?' pendente, 'Sim, desliga' não é um 'sim' puro: o núcleo local tem de desligar."""
    assert comando_local(fala) == "desligar"


@pytest.mark.parametrize("fala", ["Para.", "Jarvis, para!", "Cancela.", "Chega.", "Pode parar."])
def test_parar(fala):
    assert comando_local(fala) == "parar"


@pytest.mark.parametrize("fala", ["Cancela o timer.", "Jarvis, tira o timer.", "Não desliga o PC.",
                                  "Não desligue o computador.", "Cancela o taimer.", "Desliga o timer.",
                                  "Cancela o timer de desligar.", "Tira o timer de desligar."])
def test_cancelar_timer(fala):
    assert comando_local(fala) == "cancelar_timer"


def test_para_nao_cancela_timer():
    """"Para" só para o laço; o timer só cai citando o timer."""
    assert comando_local("Para.") == "parar" and comando_local("Para o timer.") == "cancelar_timer"


@pytest.mark.parametrize("anterior", ["bota um timer de", "Põe um timer para", "um timer pra"])
def test_desligar_depois_de_de_nao_dispara(anterior):
    assert comando_local("desligar", anterior=anterior) is None


def test_desligar_com_turno_aberto_nao_dispara():
    assert comando_local("Desliga.", turno_fechado=False) is None
    assert comando_local("Que horas são?", turno_fechado=False) == "hora"  # só o desligar espera


def test_desligar_sozinho_com_turno_fechado_desliga():
    assert comando_local("Desliga.", anterior="abre o g1", turno_fechado=True) == "desligar"


@pytest.mark.parametrize("t", ["pode enviar", "Pode enviar, Jarvis.", "Jarvis, pode enviar!"])
def test_pode_enviar(t):
    assert pode_enviar(t)


@pytest.mark.parametrize("t", ["sim", "ok", "pode", "pode mandar", "não pode enviar", "pode enviar depois"])
def test_nao_e_frase_forte(t):
    assert not pode_enviar(t)


@pytest.mark.parametrize("fala,comando", [
    ("Pausa.", "midia_pausar"), ("Jarvis, pausa a música", "midia_pausar"), ("Pausa o filme.", "midia_pausar"),
    ("Dá play.", "midia_tocar"), ("Continua.", "midia_tocar"), ("Volta a tocar", "midia_tocar"),
    ("Próxima.", "midia_proxima"), ("Pula essa", "midia_proxima"), ("Passa.", "midia_proxima")])
def test_pausa_e_comando_local(fala, comando):
    assert comando_local(fala) == comando


def test_midia_nao_toca_no_parar():
    assert comando_local("Para.") == "parar" and comando_local("Pausa a música do Kaluê") is None


@pytest.mark.parametrize("fala,comando", [
    ("Fecha essa aba.", "janela_fechar_aba"), ("Jarvis, fecha a aba", "janela_fechar_aba"),
    ("Fecha o Chrome.", "janela_fechar_chrome"), ("Pode fechar o navegador, por favor", "janela_fechar_chrome"),
    ("Fecha a janela.", "janela_fechar"), ("Minimiza.", "janela_minimizar"), ("Jarvis, minimiza a janela", "janela_minimizar"),
    ("Minimiza o Chrome", "janela_minimizar_chrome")])
def test_janela_e_comando_local(fala, comando):
    assert comando_local(fala) == comando


@pytest.mark.parametrize("fala", ["Fecha o Spotify do Kaluê", "Fecha a porta", "Minimiza os gastos", "Fecha a aba de preços do g1"])
def test_janela_so_com_a_frase_inteira(fala):
    assert comando_local(fala) is None


@pytest.mark.parametrize("fala,esperado", [("Groov surdo", "surdo"), ("Gruv, fica surdo.", "surdo"), ("modo surdo", "surdo"),
                                           ("o surdo do bairro", None), ("ele é surdo", None)])
def test_comando_surdo(fala, esperado):
    assert comando_local(fala) == esperado


@pytest.mark.parametrize("fala,esperado", [
    ("Errado", "nao"), ("Tá errado", "nao"), ("Isso não", "nao"), ("Errou", "nao"), ("Pausa", "nao"),
    ("É outra coisa", "nao"), ("Não é isso", "nao"), ("Não", "nao"),
    ("Deixa", "sim"), ("Deixa tocando", "sim"), ("Não, você acertou", "sim"), ("Sim", "sim"), ("Isso mesmo", "sim"),
    ("hmm talvez", None),
])
def test_resposta_do_que_tocou(fala, esperado):
    from src.conversa.comandos import resposta_do_que_tocou
    assert resposta_do_que_tocou(fala) == esperado


@pytest.mark.parametrize("fala", ["Tá surdo?", "Ei, tá surdo, Groov?", "surdo", "Você tá surdo?"])
def test_surdo_irritado_nao_liga(fala):
    """Revisão 14/11: "tá surdo?" é a frase de quem reclama que ele não ouviu."""
    assert comando_local(fala) is None
