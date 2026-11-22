import pytest
from src.conversa import regras_pc as r

@pytest.mark.parametrize("url", [
    "https://netflix.com.evil.com/", "https://g1.evil.com/", "https://de.evil.com/",
    "http://evil.com\\@netflix.com/", "https://netflix.com@evil.com/", "http://127.1:7860/",
    "http://2130706433/", "http://0x7f000001/", "http://localhost:7860/", "http://192.168.0.10/",
    "file:///C:/Users/ana/privado/", "chrome://settings", "https://netflix.com:8443/",
    "http://[::1]/", "http://intranet/",
])
def test_url_enganosa_nunca_e_ok(url):
    assert r.avaliar_url(url, "abre a netflix pra mim", frozenset()).tipo in {"recusar", "perguntar"}

def test_raiz_de_site_citado_e_ok():
    assert r.avaliar_url("https://www.netflix.com/", "bota sora no kanata na netflix", frozenset()).tipo == "ok"
    assert r.avaliar_url("https://g1.globo.com", "abre o g1 por favor", frozenset()).tipo == "ok"

def test_caminho_ou_query_fora_de_molde_e_recusado():
    d = r.avaliar_url("https://github.com/atacante/x/issues/new?body=segredo", "abre o github", frozenset())
    assert d.tipo == "recusar"

def test_molde_do_github_e_ok_sem_termo():
    assert r.avaliar_url(r.MOLDES["github_estrelas"], "abre o github e me mostre o repositório com mais estrelas",
                         frozenset()).tipo == "ok"

def test_site_nao_citado_pergunta_falando_o_host():
    # pessoal (mail.google.com) não citado é recusado sem perguntar; ver test_email_sem_citacao_*
    d = r.avaliar_url("https://exemplo.com.br/", "abre o g1", frozenset())
    assert d.tipo == "perguntar" and d.valor == "exemplo.com.br"

def test_palavra_fora_da_tabela_so_casa_ponto_com_exato():
    assert r.avaliar_url("https://padariaze.com.br/", "abre o site padariaze", frozenset()).tipo == "ok"
    assert r.avaliar_url("https://padariaze.evil.com/", "abre o site padariaze", frozenset()).tipo != "ok"

def test_host_ja_alcancado_vale():
    assert r.avaliar_url("https://exemplo.com.br/", "abre o g1", frozenset({"exemplo.com.br"})).tipo == "ok"

def test_email_sem_citacao_e_recusado_mesmo_alcancado():
    assert r.avaliar_url("https://mail.google.com/", "abre o g1", frozenset({"mail.google.com"})).tipo == "recusar"
    assert r.avaliar_url("https://mail.google.com/", "abre meu gmail", frozenset()).tipo == "ok"

def test_navegar_para_outro_host_e_livre():
    assert r.avaliar_navegacao("ge.globo.com", "abre o g1", frozenset({"g1.globo.com"})).tipo == "ok"  # 11/11: navegar é livre

@pytest.mark.parametrize("host", ["nubank.com.br", "www.itau.com.br", "caixa.gov.br", "passwords.google.com",
                                  "pay.google.com", "web.whatsapp.com", "meubanco.com", "corretoraabc.com.br"])
def test_bloqueio_por_host(host):
    assert r.bloqueado(host, "Início")

def test_titulo_com_nome_de_banco_nao_bloqueia_site_da_tabela():
    assert not r.bloqueado("g1.globo.com", "Caixa paga abono a partir de hoje")
    assert not r.bloqueado("g1.globo.com", "Banco Central sobe juros")

def test_extras_ausentes_mantem_a_base(tmp_path):
    assert r.carregar_extras(tmp_path / "nao_existe.txt") == frozenset()
    assert r.bloqueado("nubank.com.br", "x", r.carregar_extras(tmp_path / "nao_existe.txt"))

def test_whisper_separando_o_nome_do_site_ainda_cita():
    assert r.avaliar_url("https://github.com/", "abre o git hub", frozenset()).tipo == "ok"
    assert r.avaliar_url("github.com", "abre o git hub", frozenset()).tipo == "ok"  # sem esquema conta como https

def test_bloqueado_para_o_laco_em_abrir_e_navegar():
    assert r.avaliar_url("https://nubank.com.br/", "abre o nubank", frozenset()).tipo == "parar"
    assert r.avaliar_navegacao("www.itau.com.br", "abre o g1", frozenset({"www.itau.com.br"})).tipo == "parar"

def test_titulo_com_nome_proprio_bloqueia_fora_da_tabela():
    assert r.bloqueado("mail.google.com", "Sua fatura Nubank chegou")
    assert not r.bloqueado("mail.google.com", "Caixa de entrada (3)")

def test_extras_lidos_do_arquivo(tmp_path):
    arquivo = tmp_path / "bloqueio_pc.txt"
    arquivo.write_text("# meus extras\nhttps://Meusite.com.br/\nexemplo.org\n", encoding="utf-8")
    extras = r.carregar_extras(arquivo)
    assert r.bloqueado("www.meusite.com.br", "x", extras) and r.bloqueado("exemplo.org", "x", extras)
    assert not r.bloqueado("exemplo.org", "x")

@pytest.mark.parametrize("url,pedido", [
    ("https://g1.com.br/", "abre o g1 por favor"), ("https://g1.com/", "abre o g1"),
    ("https://github.com.br/", "abre o github"), ("https://netflix.com.br/", "abre a netflix"),
    ("https://git.com.br/", "abre o git hub"), ("https://net.com/", "abre a net flix"),
    ("https://g.com/", "abre o g 1"),
    ("https://de.com/", "abre o site de receitas"), ("https://de.com.br/", "abre o site de receitas"),
    ("https://dormir.com/", "bota kanata na netflix e depois vai dormir"), ("https://email.com/", "entra no meu email"),
])
def test_palavra_da_tabela_ou_comum_nao_vira_ponto_com(url, pedido):
    assert r.avaliar_url(url, pedido, frozenset()).tipo != "ok"

def test_palavra_fora_da_tabela_depois_de_comum_ainda_casa():
    assert r.avaliar_url("https://receitas.com.br/", "abre o site de receitas", frozenset()).tipo == "ok"

@pytest.mark.parametrize("endereco", ["", "chrome://settings", "file:///C:/x", "http://127.0.0.1/"])
def test_endereco_ilegivel_depois_do_clique_faz_parar(endereco):
    assert r.avaliar_navegacao(endereco, "abre o g1", frozenset()).tipo == "parar"

@pytest.mark.parametrize("titulo", ["Banco do Brasil - Autoatendimento", "Caixa Econômica Federal", "C6 - Conta"])
def test_titulo_de_bb_caixa_e_c6_bloqueia(titulo):
    assert r.bloqueado(None, titulo)


# --- Task 2: classificação sem volta, campos e mídia ---
from src.conversa.regras_pc import (Elemento, alvo_nomeado, apps_citados, casa_alvo, classificar_clique,
                                    e_campo_de_busca, e_campo_sensivel, familia, pedido_de_midia)

def el(nome, tipo="Button", **k): return Elemento(id=1, nome=nome, tipo=tipo, **k)

@pytest.mark.parametrize("nome", ["Enviar", "Send", "Concluir cancelamento", "Confirmar pagamento", "Finalizar compra",
                                  "Change to public", "Delete this repository", "Place order", "Submit new issue",
                                  "Permitir", "OK", "Adicionar extensão", "Mandar", "Deletar"])
def test_sem_volta_nunca_e_ok_sem_pedido(nome):
    assert classificar_clique(el(nome), "github.com", "abre o github", "github").tipo == "parar"

def test_enviar_com_pedido_pede_frase_forte():
    assert classificar_clique(el("Enviar"), None, "abre o whatsapp e manda pro joão que chego às 8", "whatsapp").tipo == "forte"

def test_comprar_mesmo_pedido_para_nesta_versao():
    assert classificar_clique(el("Comprar"), "x.com", "compra isso", None).tipo == "parar"

def test_texto_interno_com_verbo_que_o_nome_nao_tem_e_sem_volta():
    assert classificar_clique(el("Ver episódio", texto_interno="Comprar"), "netflix.com", "bota kanata na netflix", "netflix").tipo == "parar"

def test_continuar_assistindo_nao_e_consentimento():
    assert familia("Continuar assistindo") is None

def test_isento_passa_mesmo_sem_casar_o_pedido(monkeypatch):
    monkeypatch.setenv("GROOV_PERFIL_NETFLIX", "Perfil1")
    assert classificar_clique(el("Perfil1"), "netflix.com", "bota sora no kanata na netflix", "netflix").tipo == "ok"

def test_manchete_no_g1_nao_para():
    link = el("Caixa paga abono hoje", tipo="Hyperlink", host_do_link="g1.globo.com")
    assert classificar_clique(link, "g1.globo.com", "abre o g1", "g1").tipo == "ok"

def test_caixa_de_mensagem_nao_e_busca():
    assert not e_campo_de_busca(el("Digite uma mensagem", tipo="Edit"), "whatsapp")
    assert e_campo_de_busca(el("Pesquisar", tipo="Edit", papel="searchbox"), "netflix")

def test_bota_e_verbo_de_midia():
    assert pedido_de_midia("bota uma música do kaluê pra mim no app do spotify")

def test_link_do_g1_para_outro_host_continua_na_lista():
    link = el("Assine já", tipo="Hyperlink", host_do_link="assinatura.globo.com")
    assert classificar_clique(link, "g1.globo.com", "abre o g1", "g1").tipo == "parar"

PEDIDO1 = "bota sora no kanata aí pra eu assistir na netflix"
@pytest.mark.parametrize("e", [el("Senha", tipo="Edit", senha=True), el("PIN", tipo="Edit"), el("CVV", tipo="Edit"),
                               el("CPF", tipo="Edit"), el("Número do cartão", tipo="Edit"), el("Código de segurança", tipo="Edit")])
def test_campo_sensivel(e):
    assert e_campo_sensivel(e)

# --- extras da Task 2 ---
@pytest.mark.parametrize("nome", ["Aceitar todos", "Permitir sempre", "Sim", "Accept all"])
def test_consentimento_com_complemento_ainda_e_consentimento(nome):
    assert familia(nome) == "consentimento"

@pytest.mark.parametrize("nome", ["Assistir", "Mais informações", "Próxima página", "Sora no Kanata", "Pesquisar"])
def test_controles_comuns_nao_sao_sem_volta(nome):
    assert familia(nome) is None

def test_isento_nao_escapa_de_outra_familia(monkeypatch):
    monkeypatch.setenv("GROOV_PERFIL_NETFLIX", "Perfil1")
    assert classificar_clique(el("Perfil1", texto_interno="Excluir perfil"), "netflix.com", PEDIDO1, "netflix").tipo == "parar"

def test_ancestral_com_verbo_sem_volta_para():
    assert classificar_clique(el("Agora", ancestrais=("Comprar plano",)), "x.com", "abre o x", None).tipo == "parar"

def test_enviar_com_outra_familia_junto_para():
    assert classificar_clique(el("Enviar", texto_interno="Pagar"), None, "manda pro joão que chego", "whatsapp").tipo == "parar"

@pytest.mark.parametrize("host,link", [("accounts.google.com", None), ("github.com", "login.microsoftonline.com"),
                                       ("github.com", "oauth.exemplo.com")])
def test_host_de_login_conta_como_sem_volta(host, link):
    e = el("Entrar com Google", tipo="Hyperlink", host_do_link=link)
    assert classificar_clique(e, host, "abre o github", "github").tipo == "parar"

def test_manchete_fora_de_site_de_leitura_passa_pela_lista():
    link = el("Caixa paga abono hoje", tipo="Hyperlink", host_do_link="github.com")
    assert classificar_clique(link, "github.com", "abre o github", "github").tipo == "parar"

@pytest.mark.parametrize("e,origem", [
    (el("Pesquisar mensagens", tipo="Edit"), "whatsapp"), (el("Responder", tipo="Edit"), None),
    (el("Search", tipo="Button"), None), (el("Senha", tipo="Edit", papel="searchbox", senha=True), None),
    (el("Busca", tipo="Edit", ancestrais=("Enviar comentário",)), None),
])
def test_nao_e_campo_de_busca(e, origem):
    assert not e_campo_de_busca(e, origem)

def test_campo_de_busca_por_nome():
    assert e_campo_de_busca(el("Pesquisar títulos, gente e gêneros", tipo="ComboBox"), "netflix")
    assert e_campo_de_busca(el("Search or jump to...", tipo="Edit"), "github")

def test_campo_comum_nao_e_sensivel():
    assert not e_campo_sensivel(el("Pesquisar", tipo="Edit"))

@pytest.mark.parametrize("pedido", ["abre o g1 por favor e lê a reportagem mais relevante de hoje",
                                    "bota um timer de dez minutos", "toca isso aí", "pesquisa vídeos de gato no youtube"])
def test_nao_e_pedido_de_midia(pedido):
    assert not pedido_de_midia(pedido)


@pytest.mark.parametrize("pedido", ["Hey Jarvis Matamus Kanu tobe Batuam, música no YouTube",  # 14/11: sem verbo, transcrição ruim
                                    "o episódio novo na netflix", "uma playlist de lofi no youtube"])
def test_coisa_de_tocar_sem_verbo_e_midia(pedido):
    assert pedido_de_midia(pedido)

def test_nome_de_app_citado():
    assert r.nome_de_app_citado("bloco de notas", "abre o bloco de notas pra mim")
    assert r.nome_de_app_citado("Visual Studio Code", "abre o visual studio code")
    assert r.nome_de_app_citado("Notepad", "abre o notepad")
    assert r.nome_de_app_citado("git hub", "abre o github desktop")  # o Whisper cola e separa
    assert not r.nome_de_app_citado("calculadora", "abre o g1")  # app que a fala não nomeia
    assert not r.nome_de_app_citado("o", "abre o g1") and not r.nome_de_app_citado("de", "bota um som de rock")
    assert not r.nome_de_app_citado("", "abre o g1")


def test_apps_citados():
    assert apps_citados("bota uma música do kaluê no app do spotify") == frozenset({"spotify"})
    assert apps_citados("abre o g1") == frozenset()

@pytest.mark.parametrize("pedido,alvo", [
    (PEDIDO1 + " e depois bota um timer de desligar de uma hora", "sora no kanata"),
    ("na netflix bota sora no kanata", "sora no kanata"),
    ("bota uma música do kaluê pra mim no app do spotify", None),
    ("abre o g1 por favor e lê a reportagem mais relevante de hoje", None),
    ("abre o github e me mostre o repositório com mais estrelas", None),
])
def test_alvo_nomeado(pedido, alvo):
    assert alvo_nomeado(pedido, "netflix") == alvo

def test_casa_alvo_tolera_erro_do_whisper():
    assert casa_alvo("Sora no Kanata", "bota zora no kanta na netflix") >= r.LIMIAR_ALVO
    assert casa_alvo("Sora no Kanata Rising", PEDIDO1) < r.LIMIAR_ALVO
    assert casa_alvo("Sora no Kanata", "bota uma música do kaluê no spotify") == 0.0


@pytest.mark.parametrize("nome", ["Sora no Kanata: The Fighting!", "Sora no Kanata - Temporada 2",
                                  "Sora no Kanata (Dublado)"])
def test_casa_alvo_pelo_nome_antes_do_subtitulo(nome):
    assert casa_alvo(nome, PEDIDO1) == 1.0
    assert casa_alvo(nome, "bota zora no kanta na netflix") >= r.LIMIAR_ALVO  # com erro do Whisper também




def test_subtitulo_nao_casa_nome_comprido_sem_separador():
    assert casa_alvo("Friends with Benefits", "bota friends na netflix") < r.LIMIAR_ALVO

def test_casa_palavra_uma_letra():
    from src.conversa.regras_pc import _casa_palavra
    assert _casa_palavra("kalui", "kalue") and _casa_palavra("kalue", "kalue")
    assert not _casa_palavra("de", "da")  # palavra curta é exata
    assert not _casa_palavra("kalui", "matao")  # duas letras de diferença


# --- correções da revisão da Task 2 ---
P_MANDA = "abre o whatsapp e manda pro joão que chego às 8"

@pytest.mark.parametrize("nome", ["Enviar pagamento", "Send payment", "Responder e excluir", "Enviar Pix",
                                  "Enviar dinheiro", "Send money"])
def test_enviar_com_outra_familia_no_mesmo_texto_para(nome):
    assert classificar_clique(el(nome), None, P_MANDA, "whatsapp").tipo == "parar"

def test_familia_prefere_a_que_nao_e_enviar():
    assert familia("Enviar pagamento") == "dinheiro"
    assert familia("Enviar") == "enviar"

@pytest.mark.parametrize("pedido", ["coloque sora no kanata na netflix", "toque kaluê no spotify",
                                    "assiste sora no kanata na netflix", "escuta kaluê no spotify",
                                    "bote naruto na netflix", "ouve kaluê no spotify"])
def test_verbos_de_midia_falados(pedido):
    assert pedido_de_midia(pedido)

def test_assiste_separa_o_titulo():
    assert alvo_nomeado("assiste sora no kanata na netflix", "netflix") == "sora no kanata"

@pytest.mark.parametrize("pedido", ["bota um anime na netflix", "bota um desenho na netflix",
                                    "bota um documentário na netflix"])
def test_genero_e_descricao_nao_alvo(pedido):
    assert alvo_nomeado(pedido, "netflix") is None

def test_isento_tira_o_consentimento_so_na_sua_origem(monkeypatch):
    monkeypatch.setitem(r.ISENTOS, "netflix", ("Permitir",))
    assert classificar_clique(el("Permitir"), "netflix.com", PEDIDO1, "netflix").tipo == "ok"
    assert classificar_clique(el("Permitir"), "netflix.com", PEDIDO1, None).tipo == "parar"

def test_campo_com_ispassword_e_sensivel_sem_nome():
    assert e_campo_sensivel(el("Campo", tipo="Edit", senha=True))

# --- Task 3: texto digitado e fala do modelo ---
from src.conversa.regras_pc import fala_permitida

@pytest.mark.parametrize("t", ["Senhor, qual é o código que chegou?", "Me diga a senha do banco",
                               "Para confirmar, diga pode enviar", "Pode enviar agora?",
                               "Posso confirmar agora?", "Pode finalizar compra?",
                               "Pode por favor enviar agora?", "Senhor, pode, por gentileza, mandar?",
                               "Can you please send it?"])
def test_perguntar_recusa_segredos_e_imitacao_de_confirmacao(t):
    assert not fala_permitida(t, "perguntar")

def test_perguntar_aceita_pode_ser_outro_nome():
    assert fala_permitida("Pode ser outro nome, senhor?", "perguntar")

def test_perguntar_aceita_posso_continuar_procurando():
    assert fala_permitida("Posso continuar procurando?", "perguntar")

def test_responder_aceita_noticia_sobre_pix_e_recusa_formatos():
    assert fala_permitida("O Banco Central mudou as regras do Pix.", "responder")
    assert not fala_permitida("O CPF é 123.456.789-09", "responder")
    assert not fala_permitida("O CPF é 123 456 789 09", "responder")
    assert not fala_permitida("CPF 123.456.789.09", "responder")
    assert not fala_permitida("Cartão 4111 1111 1111 1111", "responder")
    assert not fala_permitida("O repositório tem 441234 estrelas", "responder")

# casos de borda além do plano
def test_desistir_recusa_segredo_e_tipo_desconhecido_e_recusado():
    assert not fala_permitida("Não consegui, me passe o token", "desistir")
    assert fala_permitida("Não achei o título, senhor.", "desistir")
    assert not fala_permitida("Olá", "clicar")

def test_cartao_no_meio_de_outros_numeros_e_recusado():
    assert not fala_permitida("Em 2024 4111 1111 1111 1111 foi usado", "responder")
    assert fala_permitida("São 1.234 estrelas desde 2008.", "responder")


@pytest.mark.parametrize("frase,esperado", [
    ("e depois bota um timer de desligar de uma hora", (60, True, False)),
    ("bota um timer pra desligar em 30 minutos", (30, True, False)),
    ("bota um timer pra desligar o forno em 10 minutos", (10, False, False)),
    ("timer de 10 minutos pro macarrão", (10, False, False)),
    ("não quero timer de desligar de uma hora", None),
    ("bota um taimer de desligar de uma hora", (60, True, False)),
    ("desliga o timer daqui a pouco", (None, False, True)),
    ("bota um timer de desligar o pc em uma hora e meia", (90, True, False)),
    ("timer para desligar o computador daqui a 45 minutos", (45, True, False)),
    ("timer de desligar daqui a duas horas", (120, True, False)),
    ("timer de meia hora", (30, False, False)),
    ("timer de vinte e cinco minutos", (25, False, False)),
    ("timer de 1 hora e 15 minutos", (75, False, False)),
    ("bota um timer de desligar", (None, True, False)),
    ("timer de 10", (None, False, False)),
    ("bota sora no kanata na netflix", None),
    ("sem timer de desligar hoje", None),
    # desistência ou correção depois do timer: perguntar, nunca armar
    ("timer de desligar de uma hora, não, melhor não", (None, True, True)),
    ("bota um timer de desligar de uma hora... não, deixa", (None, True, True)),
    ("bota um timer de desligar de uma hora, não, de duas horas", (None, True, True)),
    ("bota um timer de 10 minutos e um timer de desligar de uma hora", (None, True, True)),
    ("bota um timer de desligar, não, deixa", (None, True, True)),
    ("bota um timer pra desligar o forno em 10 minutos, não esquece", (None, False, True)),
])
def test_ler_timer(frase, esperado):
    p = r.ler_timer(frase)
    assert (None if p is None else (p.minutos, p.desligar, p.ambiguo)) == esperado


@pytest.mark.parametrize("frase,esperado", [
    ("não desliga o pc", "desligar"),
    ("cancela o timer de desligar", "desligar"),
    ("não desliga o computador", "desligar"),
    ("cancela os dois timers", "ambos"),
    ("tira todos os timers", "ambos"),
    ("cancela o timer", None),
    ("tira o timer", None),
    ("cancela o timer de desligar o forno", "simples"),
    ("desliga o timer", None),  # verbo sobre o timer, não o timer de desligar
])
def test_qual_timer(frase, esperado):
    assert r.qual_timer(frase) == esperado


# --- ajustes da fase 1 (achados das provas, 07/11) ---
@pytest.mark.parametrize("frase,esperado", [
    ("timer de 30 minutos pra desligar o pc", (30, True, False)),
    ("bota um timer de uma hora pra desligar", (60, True, False)),
    ("timer de 10 minutos pra desligar o forno", (10, False, False)),
    ("bota um time de desligar de uma hora", (60, True, False)),  # erro do Whisper
    ("meu time de futebol ganhou", None),  # "time" sozinho continua sendo time
    ("timer do bolo de 20 minutos pra desligar", (None, False, True)),  # duração longe do timer: pergunta
])
def test_ler_timer_ajustes(frase, esperado):
    p = r.ler_timer(frase)
    assert (None if p is None else (p.minutos, p.desligar, p.ambiguo)) == esperado


def test_qual_timer_simples_citado():
    assert r.qual_timer("cancela o timer simples") == "simples"


def test_whatsapp_fora_dos_apps():
    assert r.APPS == ("spotify",)
    assert apps_citados("abre o whatsapp") == frozenset()


@pytest.mark.parametrize("endereco,elementos", [
    ("netflix.com/br/login", ()),
    ("https://github.com/login?return_to=x", ()),
    ("accounts.google.com/", ()),
    ("https://exemplo.com.br/entrar", ()),
    ("netflix.com/browse", (el("Senha", tipo="Edit", senha=True),)),
    (None, (el("Digite sua senha", tipo="Edit"),)),
])
def test_pagina_de_login(endereco, elementos):
    assert r.pagina_de_login(endereco, elementos)


@pytest.mark.parametrize("endereco", ["netflix.com/browse", "https://github.com/authors", "g1.globo.com", None])
def test_pagina_comum_nao_e_login(endereco):
    assert not r.pagina_de_login(endereco, (el("Pesquisar", tipo="Edit"), el("Assistir")))


@pytest.mark.parametrize("nome", ["Salvar Anos Luz na Sua Biblioteca", "Seguir Kaluê", "Seguindo", "Curtir",
                                  "Adicionar à playlist", "Adicionar a Músicas curtidas", "Save", "Follow", "Like"])
def test_mudar_a_conta_e_estado(nome):
    assert familia(nome) == "estado"
    assert classificar_clique(el(nome), None, "bota uma música do kaluê no spotify", "spotify").tipo == "parar"


@pytest.mark.parametrize("nome", ["Músicas Curtidas", "Curta-metragem", "Tocar Anos Luz"])
def test_nomes_comuns_do_spotify_e_da_netflix_nao_sao_estado(nome):
    assert familia(nome) is None


def test_perguntar_aceita_posso_seguir_procurando():
    assert fala_permitida("Posso seguir procurando, senhor?", "perguntar")


def test_valores_das_provas():
    assert r.CAMPOS_BUSCA == {"spotify": ("O que você quer ouvir?",)}
    assert r.ISENTOS == {"netflix": (), "spotify": ("Buscar", "O que você quer ouvir?")}
    assert r.ITENS_DE_MIDIA == {"spotify": ("DataItem/linha", "DataItem/item"), "netflix": ("Hyperlink",)}
    assert r.LIMIAR_ALVO == 0.85
    assert e_campo_de_busca(el("O que você quer ouvir?", tipo="ComboBox"), "spotify")


def test_moldes_tem_descricao():
    assert set(r.DESCRICAO_MOLDES) == set(r.MOLDES) and all(r.DESCRICAO_MOLDES.values())


def test_pede_dado_tecnico():
    assert r.pede_dado_tecnico("Qual é o ID do vídeo?") and r.pede_dado_tecnico("Me passa o link ou o endereço.")
    assert r.pede_dado_tecnico("Qual o código?") and r.pede_dado_tecnico("Qual a URL?")
    assert not r.pede_dado_tecnico("Qual notícia o senhor prefere?") and not r.pede_dado_tecnico("Qual vídeo, o primeiro?")


# ---- busca por endereço ----

def test_busca_de_reconhece_moldes():
    assert r.busca_de("https://github.com/search?q=jarvis%20voz&type=repositories") == ("github", "jarvis voz")
    assert r.busca_de("https://www.youtube.com/results?search_query=kalue+bola") == ("youtube", "kalue bola")
    assert r.busca_de("https://www.netflix.com/search?q=sora") == ("netflix", "sora")
    assert r.busca_de("https://www.google.com/search?q=clima") == ("google", "clima")
    assert r.busca_de("https://g1.globo.com/busca/?q=copa") == ("g1", "copa")
    assert r.busca_de("https://github.com/search?type=repositories&q=a+b") == ("github", "a b")  # ordem livre


@pytest.mark.parametrize("url", [
    "http://www.netflix.com/search?q=x",                                  # não é https
    "https://www.netflix.com.evil.com/search?q=x",                        # host diferente
    "https://www.netflix.com/outra?q=x",                                  # caminho diferente
    "https://github.com/search?q=x",                                      # falta o parâmetro fixo
    "https://github.com/search?q=x&type=users",                           # valor fixo diferente
    "https://github.com/search?q=x&type=repositories&extra=1",            # parâmetro a mais
    "https://github.com/search?q=x&q=y&type=repositories",                # parâmetro repetido
    "https://www.netflix.com/search?q=x#frag",                            # fragmento
    "https://www.netflix.com/search?q=%20%20",                            # termo vazio
    "https://www.netflix.com/search?q=",
    "https://user@www.netflix.com/search?q=x",
    "nao e url",
])
def test_busca_de_recusa_host_param_extra_fragmento_e_vazio(url):
    assert r.busca_de(url) is None


def test_cita_destino_em_regras():  # mudou de ferramentas (pipecat) para cá: o laço precisa dela
    assert r.cita_destino("abre o github") and r.cita_destino("bota no spotify")
    assert not r.cita_destino("quanto é dois mais dois")


def test_midia_com_origem_herdada():
    assert not r.pedido_de_midia("toca sora no kanata")
    assert r.pedido_de_midia("toca sora no kanata", origem="netflix")
    assert not r.pedido_de_midia("que horas são", origem="netflix")  # sem verbo de mídia continua não sendo


# --- Janelas e abas (fase 6) ---
PERMITIDOS = ("consent", "LogonUI")  # o nome ficou; é o argumento dos proibidos


def test_fechar_qualquer_app_menos_os_proibidos():
    assert r.decidir_janela("fechar", "Spotify", 0, False, PERMITIDOS).tipo == "ok"
    assert r.decidir_janela("minimizar", "chrome", 1, False, PERMITIDOS).tipo == "ok"
    for processo in ("notepad", "explorer"):  # fora da antiga lista: agora vale
        assert r.decidir_janela("fechar", processo, 0, False, PERMITIDOS).tipo == "ok"
        assert r.decidir_janela("minimizar", processo, 0, False, PERMITIDOS).tipo == "ok"
    for processo in ("consent", "logonui", ""):  # UAC, tela de login ou janela que a sonda não leu
        assert r.decidir_janela("fechar", processo, 0, False, PERMITIDOS).tipo == "recusar"
        assert r.decidir_janela("minimizar", processo, 0, False, PERMITIDOS).tipo == "recusar"
    assert r.decidir_janela("fechar_aba", "Spotify", 0, False, PERMITIDOS).tipo == "recusar"  # aba é do Chrome
    assert r.decidir_janela("formatar", "chrome", 1, False, PERMITIDOS).tipo == "recusar"


def test_nunca_fecha_o_groov():
    for acao in r.ACOES_JANELA:  # a janela do GROOV é do Chrome: o processo está na lista, e mesmo assim recusa
        assert r.decidir_janela(acao, "chrome", 1, True, PERMITIDOS).tipo == "recusar"
        assert r.decidir_janela(acao, "chrome", 3, True, PERMITIDOS, confirmado=True).tipo == "recusar"


def test_chrome_com_abas_pergunta():
    d = r.decidir_janela("fechar", "chrome", 3, False, PERMITIDOS)
    assert d.tipo == "perguntar" and d.valor == "3"
    assert r.decidir_janela("fechar", "chrome", 3, False, PERMITIDOS, confirmado=True).tipo == "ok"
    assert r.decidir_janela("fechar", "chrome", 1, False, PERMITIDOS).tipo == "ok"
    assert r.decidir_janela("fechar_aba", "chrome", 3, False, PERMITIDOS).tipo == "ok"  # uma aba só, sem pergunta
    assert r.decidir_janela("minimizar", "chrome", 3, False, PERMITIDOS).tipo == "ok"

# ---- domínio que o usuário disse vale com www. e subdomínio (11/11: "globo.com" parou em www.globo.com) ----

@pytest.mark.parametrize("pedido", ["abre o globo.com", "abre o www.globo.com", "sim, o www.globo.com mesmo", "globo.com",
                                    "Abre o GLOBO.COM, por favor"])
@pytest.mark.parametrize("url", ["https://www.globo.com/", "https://globo.com/", "https://g1.globo.com/"])
def test_dominio_citado_aceita_www_e_subdominio(pedido, url):
    assert r.avaliar_url(url, pedido, frozenset()).tipo == "ok"


@pytest.mark.parametrize("pedido,url", [("abre o g1.globo.com", "https://globo.com/"), ("abre o globo.com", "https://oglobo.com/"),
                                         ("abre o globo.com", "https://globo.com.evil.com/"), ("abre o com.br", "https://qualquer.com.br/"),
                                         ("abre o banco.com", "https://www.banco.com/")])
def test_dominio_citado_nao_vira_licenca_ampla(pedido, url):
    assert r.avaliar_url(url, pedido, frozenset()).tipo != "ok"



# --- visão: teclas e alvo pela tela ---

@pytest.mark.parametrize("tecla,ok", [("espaco", True), ("k", True), ("play_pause", True), ("alt+f4", False),
                                      ("ctrl+w", False), ("win", False), ("", False), ("ESPACO ", False)])
def test_tecla_permitida(tecla, ok):
    assert r.tecla_permitida(tecla) is ok


def test_teclas_que_acionam_o_foco_ficam_fora():
    """Revisão 14/11: enter depois de digitar manda a mensagem; tab+enter aperta o botão focado. Nenhuma das duas existe."""
    assert not r.tecla_permitida("enter") and not r.tecla_permitida("tab")


def test_alvo_visual_usa_regras_do_clique():
    assert r.alvo_visual("Comprar agora", "botão", "www.amazon.com.br", "abre a amazon", None, False).tipo == "parar"
    assert r.alvo_visual("Pular anúncio", "botão Pular anúncio", "www.youtube.com", "toca lofi no youtube", "youtube",
                         True).tipo == "ok"


def test_alvo_visual_confere_tambem_a_descricao():
    assert r.alvo_visual("Pular", "botão de comprar", "www.youtube.com", "toca lofi", "youtube", True).tipo == "parar"


def test_alvo_visual_sem_nome():
    assert r.alvo_visual("", "centro do vídeo", "www.netflix.com", "dá play na série da netflix", "netflix", True).tipo == "ok"
    assert r.alvo_visual("  ", "centro", None, "abre o bloco de notas", None, False).tipo == "parar"


def test_alvo_visual_sem_nome_fora_de_player_para():
    """Revisão 14/11: ícone sem texto (enviar, carrinho, X) num app qualquer não é clicado só porque o pedido é de mídia."""
    assert r.alvo_visual("", "centro do vídeo", None, "abre o discord e toca a playlist", "discord", True).tipo == "parar"


def test_alvo_visual_sem_nome_com_descricao_de_enviar_para():
    assert r.alvo_visual("", "ícone de enviar", "www.youtube.com", "toca lofi no youtube", "youtube", True).tipo == "parar"


def test_perfil_da_netflix_vem_da_config(monkeypatch):
    assert r.isentos("netflix") == () and r.isentos(None) == ()
    # perfil com nome de consentimento: só a config o tira da regra (prova que o isento vem dela)
    assert classificar_clique(el("Permitir"), "netflix.com", PEDIDO1, "netflix").tipo == "parar"
    monkeypatch.setenv("GROOV_PERFIL_NETFLIX", "Permitir")
    assert r.isentos("netflix") == ("Permitir",)
    assert classificar_clique(el("Permitir"), "netflix.com", PEDIDO1, "netflix").tipo == "ok"
    assert r.isentos("spotify") == ("Buscar", "O que você quer ouvir?")
