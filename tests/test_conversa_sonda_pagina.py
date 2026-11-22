"""SondaPagina contra um cliente MCP falso (nunca o Playwright nem a extensão de verdade)."""
import asyncio
import logging

import pytest

from src.conversa import sonda_pagina
from src.conversa.mcp_stdio import ErroFerramenta
from src.conversa.pc import ErroSonda
from src.conversa.regras_pc import Elemento
from src.conversa.sonda_pagina import SondaPagina, SondaPaginaComposta, ler_snapshot

SNAPSHOT = '''### Page
- Page URL: https://www.netflix.com/browse
- Page Title: Netflix
### Snapshot
```yaml
- banner [ref=e2]:
  - link "Netflix" [ref=e3] [cursor=pointer]:
    - /url: /browse
  - searchbox "Buscar títulos" [ref=e4]
- main "Principal" [ref=e5]:
  - heading "Continuar assistindo" [level=2] [ref=e6]
  - link "Stranger Things" [ref=e7] [cursor=pointer]:
    - /url: https://www.netflix.com/watch/81
    - img "Capa"
    - text: 3 temporadas
  - link "Saiba mais" [ref=e8]:
    - /url: https://ajuda.exemplo.org/x
  - textbox "Senha" [ref=e9]
  - textbox "Qualquer coisa" [ref=e10]:
    - /placeholder: Digite sua password
  - 'button "Ver: tudo" [ref=e11]'
  - generic [ref=e12]: texto solto
```
'''
TABS = "### Result\n- 0: [Outra](https://exemplo.com/)\n- 1: (current) [Netflix](https://www.netflix.com/browse)\n"


class Falso:
    """Cliente MCP falso: grava as chamadas e devolve respostas fixas por ferramenta."""

    def __init__(self, tabs=TABS, snapshot=SNAPSHOT, evaluate='### Result\n"text"\n'):
        self.respostas = {"browser_tabs": tabs, "browser_snapshot": snapshot, "browser_evaluate": evaluate}
        self.chamadas = []
        self.falha = None
        self.valor = '""'  # valor atual do campo, como o browser_evaluate devolve (JSON)

    async def chamar(self, ferramenta, argumentos=None):
        self.chamadas.append((ferramenta, argumentos or {}))
        if self.falha == ferramenta:
            raise ErroSonda(f"{ferramenta}: erro da ferramenta")
        if ferramenta == "browser_evaluate" and (argumentos or {}).get("function") == sonda_pagina.JS_VALOR_CAMPO:
            return f"### Result\n{self.valor}\n"
        return self.respostas.get(ferramenta, "### Result\nok\n")

    def nomes(self):
        return [c[0] for c in self.chamadas]


def sonda(falso=None, janela="Netflix - Google Chrome - Perfil1", processo="chrome", **k):
    falso = falso or Falso()
    return SondaPagina(falso, titulo_de=lambda h: janela, processo_de=lambda h: processo, **k), falso


def rodar(coro):
    return asyncio.run(coro)


def el(ref="e7", nome="Stranger Things"):
    return Elemento(id=0, nome=nome, tipo="Hyperlink", runtime_id=ref)


def test_snapshot_vira_leitura_com_host_do_link_e_senha():
    l = ler_snapshot(SNAPSHOT, 42)
    assert (l.hwnd, l.endereco, l.titulo, l.cortado) == (42, "https://www.netflix.com/browse", "Netflix", False)
    por_ref = {e.runtime_id: e for e in l.elementos}
    assert [e.id for e in l.elementos] == list(range(len(l.elementos)))
    assert por_ref["e3"].host_do_link == "www.netflix.com"  # link relativo herda o host da página
    assert por_ref["e7"].host_do_link == "www.netflix.com" and por_ref["e8"].host_do_link == "ajuda.exemplo.org"
    assert por_ref["e7"].tipo == "Hyperlink" and "3 temporadas" in por_ref["e7"].texto_interno
    assert por_ref["e4"].tipo == "Edit" and por_ref["e4"].papel == "searchbox" and por_ref["e4"].ancestrais == ()
    assert por_ref["e7"].ancestrais == ("Principal",) and por_ref["e11"].nome == "Ver: tudo"
    assert por_ref["e9"].senha and por_ref["e10"].senha  # pelo rótulo e pelo placeholder
    assert not por_ref["e4"].senha and "e12" not in por_ref and "e6" not in por_ref
    assert "Continuar assistindo" in l.texto and "texto solto" in l.texto


def test_campo_de_senha_nao_leva_texto_interno_nem_valor():
    l = ler_snapshot('### Page\n- Page URL: https://github.com/login\n### Snapshot\n```yaml\n- textbox "Password" [ref=e1]: segredo123\n```', 1)
    (e,) = l.elementos
    assert e.senha and e.texto_interno == "" and "segredo123" not in l.texto


def test_valor_de_campo_comum_nao_vira_texto():
    l = ler_snapshot('### Page\n- Page URL: https://github.com/\n### Snapshot\n```yaml\n- searchbox "Buscar" [ref=e1]: o que digitei\n```', 1)
    assert "o que digitei" not in l.texto and l.elementos[0].texto_interno == ""


def test_texto_da_pagina_respeita_o_teto():
    longo = "x" * 20000
    l = ler_snapshot(f'### Page\n- Page URL: https://github.com/\n### Snapshot\n```yaml\n- text: {longo}\n```', 1)
    assert len(l.texto) == sonda_pagina.TEXTO_MAX and l.cortado


def test_sem_secao_de_snapshot_e_erro():
    with pytest.raises(ErroSonda):
        ler_snapshot("### Result\nok\n", 1)


def test_ler_usa_a_aba_atual_sem_selecionar():
    s, f = sonda()
    l = rodar(s.ler(7))
    assert f.nomes() == ["browser_tabs", "browser_snapshot"] and l.endereco.endswith("/browse")


def test_ler_seleciona_a_aba_quando_ela_nao_e_a_atual():
    tabs = "### Result\n- 0: [Netflix](https://www.netflix.com/browse)\n- 1: (current) [Outra](https://exemplo.com/)\n"
    s, f = sonda(Falso(tabs=tabs))
    rodar(s.ler(7))
    assert f.chamadas[1] == ("browser_tabs", {"action": "select", "index": 0})


@pytest.mark.parametrize("kw", [
    {"janela": "Outra coisa - Google Chrome"},  # nenhuma aba casa com o título
    {"processo": "spotify"},  # não é Chrome
    {"janela": "Outra - Google Chrome"},  # a aba "Outra" é de exemplo.com, fora da lista
])
def test_aba_nao_identificada_nao_e_aceita_e_ler_falha(kw):
    s, f = sonda(**kw)
    assert rodar(s.aceita(7)) is False
    with pytest.raises(ErroSonda, match="aba_nao_identificada"):
        rodar(s.ler(7))
    assert "browser_snapshot" not in f.nomes()


def test_duas_abas_com_o_mesmo_titulo_pega_a_ativa_ou_a_mais_recente():
    """11/11 (G1): cada abrir_site abre uma aba nova, então o mesmo título repete e a leitura caía na UIA."""
    tabs = "### Result\n- 0: [Netflix](https://www.netflix.com/a)\n- 1: (current) [Netflix](https://www.netflix.com/b)\n"
    s, _ = sonda(Falso(tabs=tabs))
    assert rodar(s._aba(7)).indice == 1 and rodar(s.aceita(7)) is True
    tabs = "### Result\n- 0: [Netflix](https://www.netflix.com/a)\n- 1: [Netflix](https://www.netflix.com/b)\n- 2: [Outra](https://exemplo.com/)\n"
    s, _ = sonda(Falso(tabs=tabs))
    assert rodar(s._aba(7)).indice == 1  # nenhuma ativa entre as de título igual: a de maior índice


def test_g1_com_duas_abas_de_mesmo_titulo_le_pela_pagina():
    tabs = "### Result\n- 0: [G1](https://g1.globo.com/)\n- 1: (current) [G1](https://g1.globo.com/)\n"
    s, f = sonda(Falso(tabs=tabs), janela="G1 - Google Chrome - Perfil1")
    assert rodar(s.aceita(7)) is True and rodar(s.ler(7)).endereco.endswith("/browse")


def test_falha_do_servidor_nao_aceita_e_o_log_nao_leva_conteudo(caplog):
    f = Falso()
    f.falha = "browser_tabs"
    s, _ = sonda(f)
    with caplog.at_level(logging.INFO):
        assert rodar(s.aceita(7)) is False
    assert "Netflix" not in caplog.text


def test_clicar_usa_a_referencia_na_aba_certa():
    s, f = sonda()
    assert rodar(s.clicar(7, el(), "https://www.netflix.com/browse")) is True
    assert f.chamadas[-1] == ("browser_click", {"target": "e7"})


def test_clicar_com_a_aba_em_outro_endereco_nao_age():
    s, f = sonda()
    assert rodar(s.clicar(7, el(), "https://www.netflix.com/title/1")) is False
    assert "browser_click" not in f.nomes()


def test_clicar_sem_referencia_ou_com_erro_nao_agiu():
    s, f = sonda()
    assert rodar(s.clicar(7, el(ref=""), None)) is False
    f.falha = "browser_click"
    assert rodar(s.clicar(7, el(), None)) is False


def test_digitar_confere_o_tipo_e_escreve():
    s, f = sonda()
    assert rodar(s.digitar(7, el("e4", "Buscar"), "matrix", None)) is True
    assert f.nomes()[-2:] == ["browser_evaluate", "browser_type"]
    assert f.chamadas[-1] == ("browser_type", {"target": "e4", "text": "matrix"})


def test_buscar_envia_com_submit():
    s, f = sonda()
    assert rodar(s.buscar(7, el("e4", "Buscar"), "matrix", None)) is True
    assert f.chamadas[-1] == ("browser_type", {"target": "e4", "text": "matrix", "submit": True})


def test_campo_de_senha_real_nunca_recebe_texto():
    s, f = sonda(Falso(evaluate='### Result\n"password"\n'))
    assert rodar(s.digitar(7, el("e10", "Qualquer coisa"), "x", None)) is False
    assert rodar(s.buscar(7, el("e10", "Qualquer coisa"), "x", None)) is False
    assert "browser_type" not in f.nomes()


@pytest.mark.parametrize("resposta", ['### Result\n""\n', "### Result\nundefined\n", "", '### Result\n"button"\n', '### Result\n"PASSWORD"\n'])
def test_resposta_inesperada_do_tipo_nao_deixa_digitar(resposta):
    s, f = sonda(Falso(evaluate=resposta))
    assert rodar(s.digitar(7, el("e4", "Buscar"), "x", None)) is False
    assert rodar(s.buscar(7, el("e4", "Buscar"), "x", None)) is False
    assert "browser_type" not in f.nomes()


@pytest.mark.parametrize("tipo", ["text", "search", "email", "url", "tel", "textarea", "editable"])
def test_tipo_conhecido_deixa_digitar(tipo):
    s, f = sonda(Falso(evaluate=f'### Result\n"{tipo}"\n'))
    assert rodar(s.digitar(7, el("e4", "Buscar"), "x", None)) is True


def test_depois_de_uma_falha_do_servidor_fica_na_atual_pelo_resto_da_sessao(caplog):
    agora = [100.0]
    f = Falso()
    f.falha = "browser_tabs"
    s, _ = sonda(f, relogio=lambda: agora[0])
    a = Atual()
    c = SondaPaginaComposta(a, s)
    assert rodar(c.ler(7)) == "leitura-atual"
    assert f.nomes() == ["browser_tabs"]
    agora[0] += sonda_pagina.PAUSA_FALHA_S * 100
    f.falha = None  # até o servidor "voltar" não adianta: a sessão inteira fica na UIA
    assert rodar(c.ler(7)) == "leitura-atual" and rodar(c.clicar(7, el(), None)) is True
    assert f.nomes() == ["browser_tabs"]  # nem tocou no servidor
    assert sum(1 for x in caplog.records if "desligada nesta sessão" in x.message) == 1


def test_falha_do_snapshot_pausa_e_a_composicao_le_pela_atual():
    agora = [100.0]
    f = Falso()
    f.falha = "browser_snapshot"
    s, _ = sonda(f, relogio=lambda: agora[0])
    c = SondaPaginaComposta(Atual(), s)
    assert rodar(c.ler(7)) == "leitura-atual"
    assert f.nomes().count("browser_snapshot") == 1
    assert rodar(c.ler(7)) == "leitura-atual" and f.nomes().count("browser_snapshot") == 1  # em pausa: nem tentou


def test_rolar_e_voltar():
    s, f = sonda()
    assert rodar(s.rolar(7, "baixo")) and "scrollBy(0, 1 *" in f.chamadas[-1][1]["function"]
    assert rodar(s.rolar(7, "cima")) and "scrollBy(0, -1 *" in f.chamadas[-1][1]["function"]
    assert rodar(s.voltar(7)) and f.chamadas[-1][0] == "browser_navigate_back"


# ---- composição ----

class Atual:
    proibidos = ("consent", "logonui")

    def __init__(self):
        self.visto = []

    async def ler(self, hwnd):
        self.visto.append("ler")
        return "leitura-atual"

    async def clicar(self, hwnd, el, endereco):
        self.visto.append("clicar")
        return True

    async def som_tocando(self):
        return False


def composta(**k):
    s, f = sonda(**k)
    a = Atual()
    return SondaPaginaComposta(a, s), a, f


def test_chrome_em_site_da_lista_vai_para_a_pagina():
    c, a, f = composta()
    assert rodar(c.ler(7)).endereco.endswith("/browse")
    assert rodar(c.clicar(7, el(), None)) is True and a.visto == []
    assert f.chamadas[-1][0] == "browser_click"


def test_outro_app_ou_aba_fora_da_lista_vai_para_a_atual():
    c, a, f = composta(processo="spotify")
    assert rodar(c.ler(7)) == "leitura-atual" and rodar(c.clicar(7, el(), None)) is True
    assert a.visto == ["ler", "clicar"] and f.chamadas == []  # app: nem consulta o servidor
    c, a, _ = composta(janela="Outra - Google Chrome")
    assert rodar(c.ler(7)) == "leitura-atual"


def test_o_resto_cai_na_atual_e_atributos_passam():
    c, a, _ = composta()
    assert rodar(c.som_tocando()) is False and c.proibidos == ("consent", "logonui")


def test_constante_ligada_e_o_padrao_mas_desligar_volta_a_uia(tmp_path):
    atual = Atual()
    servidor = tmp_path / "cli.js"
    servidor.write_text("")
    assert sonda_pagina.SONDA_PAGINA is True
    assert isinstance(sonda_pagina.escolher_sonda_pagina(atual, frozenset(), "tok", procurar=lambda n: "node.exe", servidor=servidor),
                      SondaPaginaComposta)
    assert sonda_pagina.escolher_sonda_pagina(atual, frozenset(), "tok", ligada=False) is atual


def test_padrao_ligado_sem_node_cai_na_atual(tmp_path):
    atual = Atual()
    assert sonda_pagina.escolher_sonda_pagina(atual, frozenset(), "tok", procurar=lambda n: None) is atual


def test_ligada_sem_node_servidor_ou_token_deixa_a_atual_e_avisa(tmp_path, caplog):
    atual = Atual()
    servidor = tmp_path / "cli.js"
    servidor.write_text("")
    with caplog.at_level(logging.WARNING):
        for node, srv, tok in ((None, servidor, "t0k3n"), ("node", tmp_path / "nada.js", "t0k3n"), ("node", servidor, None)):
            caplog.clear()
            r = sonda_pagina.escolher_sonda_pagina(atual, frozenset(), tok, ligada=True, procurar=lambda n, node=node: node, servidor=srv)
            assert r is atual
            assert [x.levelname for x in caplog.records] == ["WARNING"]
            assert "t0k3n" not in caplog.text
    assert "t0k3n" not in caplog.text


def test_ligada_monta_a_composicao_com_o_token_so_no_servidor(tmp_path, monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "g")
    servidor = tmp_path / "cli.js"
    servidor.write_text("")
    r = sonda_pagina.escolher_sonda_pagina(Atual(), frozenset({"GOOGLE_API_KEY"}), "t0k3n", ligada=True,
                                           procurar=lambda n: "node.exe", servidor=servidor)
    assert isinstance(r, SondaPaginaComposta)
    cl = r.pagina.cliente
    assert cl.comando == ["node.exe", str(servidor), "--extension", "--snapshot-mode", "none"]
    assert cl.env[sonda_pagina.TOKEN_EXTENSAO] == "t0k3n" and "GOOGLE_API_KEY" not in cl.env


class AtualAbre(Atual):
    async def abrir_site(self, url):
        self.visto.append(("abrir_site", url))


def abrindo(tabs, **k):
    f = Falso(tabs=tabs)
    s = SondaPagina(f, titulo_de=lambda h: "", processo_de=lambda h: "chrome", **k)
    a = AtualAbre()
    return SondaPaginaComposta(a, s), a, f


CONEXAO = "### Result\n- 0: (current) [Welcome](chrome-extension://abc/connect.html)\n"


def test_abrir_site_reaproveita_a_aba_de_conexao_e_seleciona():
    c, a, f = abrindo(CONEXAO)
    rodar(c.abrir_site("https://www.netflix.com/"))
    assert ("browser_navigate", {"url": "https://www.netflix.com/"}) in f.chamadas
    assert f.chamadas[-1] == ("browser_tabs", {"action": "select", "index": 0})
    assert a.visto == []


def test_abrir_site_com_outras_abas_abre_aba_nova_na_sessao():
    c, a, f = abrindo(TABS)
    rodar(c.abrir_site("https://www.netflix.com/"))
    assert ("browser_tabs", {"action": "new", "url": "https://www.netflix.com/"}) in f.chamadas
    assert "browser_navigate" not in f.nomes() and a.visto == []


def test_abrir_site_fora_da_lista_vai_para_a_atual_sem_tocar_no_servidor():
    c, a, f = abrindo(TABS)
    rodar(c.abrir_site("https://www.exemplo.org/"))
    assert a.visto == [("abrir_site", "https://www.exemplo.org/")] and f.chamadas == []


@pytest.mark.parametrize("onde", ["browser_tabs", "browser_navigate"])
def test_abrir_site_com_erro_cai_na_atual(onde):
    c, a, f = abrindo(CONEXAO)
    f.falha = onde
    rodar(c.abrir_site("https://www.netflix.com/"))
    assert a.visto == [("abrir_site", "https://www.netflix.com/")]


def test_abrir_site_com_disjuntor_aberto_vai_para_a_atual():
    c, a, f = abrindo(TABS, relogio=lambda: 0.0)
    c.pagina._pausa_ate = 100.0
    rodar(c.abrir_site("https://www.netflix.com/"))
    assert a.visto == [("abrir_site", "https://www.netflix.com/")] and f.chamadas == []


def test_abrir_site_falha_depois_de_abrir_nao_abre_de_novo_pela_atual():
    c, a, f = abrindo(CONEXAO)
    contagem = {"n": 0}
    original = f.chamar

    async def chamar(ferramenta, argumentos=None):
        if ferramenta == "browser_tabs":
            contagem["n"] += 1
            if contagem["n"] == 2:  # a segunda listagem (depois de abrir)
                raise ErroSonda("browser_tabs: erro")
        return await original(ferramenta, argumentos)
    f.chamar = chamar
    rodar(c.abrir_site("https://www.netflix.com/"))
    assert ("browser_navigate", {"url": "https://www.netflix.com/"}) in f.chamadas and a.visto == []


def test_abrir_site_falha_no_select_nao_abre_de_novo_pela_atual():
    c, a, f = abrindo(CONEXAO)
    original = f.chamar

    async def chamar(ferramenta, argumentos=None):
        if argumentos and argumentos.get("action") == "select":
            raise ErroSonda("browser_tabs: erro")
        return await original(ferramenta, argumentos)
    f.chamar = chamar
    rodar(c.abrir_site("https://www.netflix.com/"))
    assert a.visto == []


class FalsoQueIntercepta(Falso):
    """O browser_click falha como na Netflix (prévia atrás do modal); o clique pelo evaluate funciona."""

    categoria = "intercepta_ponteiro"

    async def chamar(self, ferramenta, argumentos=None):
        if ferramenta == "browser_click":
            self.chamadas.append((ferramenta, argumentos or {}))
            raise ErroFerramenta(f"browser_click: erro da ferramenta ({self.categoria})", self.categoria)
        return await super().chamar(ferramenta, argumentos)


def test_clique_interceptado_nunca_clica_por_baixo_e_avisa_o_laco():
    """11/11: o JS el.click() por baixo do modal abriu a série errada: sem reserva, só "não agiu" + `coberto`."""
    s, f = sonda(FalsoQueIntercepta())
    assert rodar(s.clicar(7, el(), "https://www.netflix.com/browse")) is False
    assert "browser_evaluate" not in f.nomes() and s.coberto is True
    s.cliente.categoria = "timeout"
    rodar(s.clicar(7, el(), None))
    assert s.coberto is False


@pytest.mark.parametrize("categoria", ["nao_visivel", "desabilitado", "timeout", "instavel", "outra"])
def test_outros_erros_do_clique_tambem_nao_agem_sem_evaluate(categoria):
    f = FalsoQueIntercepta()
    f.categoria = categoria
    s, _ = sonda(f)
    assert rodar(s.clicar(7, el(), None)) is False
    assert "browser_evaluate" not in f.nomes()


def test_aba_que_o_laco_acabou_de_abrir_vence_a_ativa_e_a_de_maior_indice():
    s, f = sonda(Falso(tabs="### Result\n- 0: (current) [G1](https://g1.globo.com/)\n- 1: [Outra](https://exemplo.com/)\n"),
                 janela="G1 - Google Chrome - Perfil1")
    assert rodar(s.abrir("https://g1.globo.com/")) is True  # lembra (0, url) como a aba aberta pelo laço
    f.respostas["browser_tabs"] = ("### Result\n- 0: [G1](https://g1.globo.com/)\n- 1: [G1](https://g1.globo.com/)\n"
                                   "- 2: (current) [G1](https://g1.globo.com/)\n")
    assert rodar(s._aba(7)).indice == 0

def test_acrescentar_em_campo_com_texto_nao_escreve():
    """11/11: o fill troca o valor inteiro; editor rico (WhatsApp Web, Docs) com texto não pode ser sobrescrito."""
    f = Falso()
    f.valor = '"oi tudo bem"'
    s, f = sonda(f)
    assert rodar(s.digitar(7, el("e4", "Buscar"), "x", None)) is False
    assert "browser_type" not in f.nomes()


@pytest.mark.parametrize("valor", ["undefined", "null", "", "42"])
def test_acrescentar_com_valor_ilegivel_nao_escreve(valor):
    f = Falso()
    f.valor = valor
    s, f = sonda(f)
    assert rodar(s.digitar(7, el("e4", "Buscar"), "x", None)) is False


def test_substituir_escreve_mesmo_com_texto_no_campo():
    f = Falso()
    f.valor = '"antigo"'
    s, f = sonda(f)
    assert rodar(s.digitar(7, el("e4", "Buscar"), "x", None, acrescentar=False)) is True
    assert f.chamadas[-1] == ("browser_type", {"target": "e4", "text": "x"})



SNAPSHOT_MODAL = '''### Page
- Page URL: https://www.netflix.com/browse
- Page Title: Netflix
### Snapshot
```yaml
- main "Principal" [ref=e5]:
  - heading "Manchete da noticia" [level=2]
  - button "Assistir" [ref=e50]
  - link "Outra Serie" [ref=e51]:
    - /url: /watch/9
- dialog "Sora no Kanata" [ref=e60]:
  - button "Assistir" [ref=e61]
  - button "Fechar" [ref=e62]
  - text: Sinopse da serie
```
'''


def test_modal_marcado_ou_dialogo_cheio_limita_os_controles_mas_o_texto_fica_inteiro():
    marcado = SNAPSHOT_MODAL.replace('dialog "Sora no Kanata" [ref=e60]', 'dialog "Sora no Kanata" [ref=e60] [modal]')
    l = ler_snapshot(marcado, 1)
    assert [e.runtime_id for e in l.elementos] == ["e61", "e62"] and [e.id for e in l.elementos] == [0, 1]
    assert "Manchete da noticia" in l.texto and "Sinopse da serie" in l.texto
    extras = "".join(f'  - button "B{i}" [ref=e8{i}]' + chr(10) for i in range(6))
    cheio = SNAPSHOT_MODAL.replace("  - text: Sinopse", extras + "  - text: Sinopse")
    assert [e.runtime_id for e in ler_snapshot(cheio, 1).elementos][:2] == ["e61", "e62"] and len(ler_snapshot(cheio, 1).elementos) == 8


def test_banner_de_cookies_com_role_dialog_nao_esconde_a_pagina():
    banner = SNAPSHOT_MODAL.replace('dialog "Sora no Kanata"', 'dialog "Cookies"')
    l = ler_snapshot(banner, 1)
    assert {"e50", "e51", "e61", "e62"} <= {e.runtime_id for e in l.elementos} and "Manchete da noticia" in l.texto
    noticia = SNAPSHOT_MODAL.replace("Outra Serie", "Governo anuncia pacote").replace("- main", "- article")


def test_dois_dialogos_valem_so_o_ultimo_e_sem_dialogo_a_pagina_toda():
    dois = SNAPSHOT_MODAL.replace(chr(96)*3 + chr(10), '') + '- alertdialog "Aviso":' + chr(10) + '  - button "Ok" [ref=e70]' + chr(10) + chr(96)*3 + chr(10)
    assert ler_snapshot(dois.replace('alertdialog "Aviso"', 'alertdialog "Aviso" [modal]'), 1).elementos[0].runtime_id == "e70"
    assert len(ler_snapshot(SNAPSHOT, 1).elementos) > 5
