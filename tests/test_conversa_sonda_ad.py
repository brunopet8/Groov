"""SondaAD com executável falso: nunca roda o agent-desktop de verdade."""
import asyncio
import sys
import time

import pytest

from src.conversa import sonda_ad
from src.conversa.pc import ErroSonda
from src.conversa.sonda_ad import SondaAD


def rodar(coro):
    return asyncio.run(coro)


def fake(codigo, tmp_path, **k):
    return SondaAD(comando=[sys.executable, "-c", codigo], home=tmp_path / "ad", **k)


def devolve(obj, tmp_path, **k):
    return fake("import sys,json; print(json.dumps(" + repr(obj) + "))", tmp_path, **k)


ECO = ("import sys,json,os\n"
       "print(json.dumps({'version':'2.6','ok':True,'command':'x','data':{'argv':sys.argv[1:],"
       "'home':os.environ.get('AGENT_DESKTOP_HOME'),'tem_chave':'GOOGLE_API_KEY' in os.environ}}))")


def test_chamada_leva_home_argumentos_e_ambiente_sem_chave(tmp_path, monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "nao-vazar")
    d = rodar(fake(ECO, tmp_path)._chamar("click", "@s1:e2"))
    assert d["argv"] == ["click", "@s1:e2"] and d["home"] == str(tmp_path / "ad") and d["tem_chave"] is False


def test_erro_com_codigo_vira_erro_so_com_o_codigo(tmp_path):
    env = {"version": "2.6", "ok": False, "command": "click",
           "error": {"code": "STALE_REF", "message": "Texto da janela: senha 123", "disposition": {}}}
    with pytest.raises(ErroSonda) as e:
        rodar(devolve(env, tmp_path)._chamar("click", "@s1:e2"))
    assert "STALE_REF" in str(e.value) and "senha" not in str(e.value)


def test_erro_sai_com_codigo_1_mas_json_no_stdout(tmp_path):
    cod = "import sys,json; print(json.dumps({'ok':False,'error':{'code':'TIMEOUT','message':'m'}})); sys.exit(1)"
    with pytest.raises(ErroSonda, match="TIMEOUT"):
        rodar(fake(cod, tmp_path)._chamar("snapshot"))


def test_json_ilegivel_e_saida_sem_json(tmp_path):
    with pytest.raises(ErroSonda, match="ilegível"):
        rodar(fake("print('nao e json')", tmp_path)._chamar("snapshot"))
    with pytest.raises(ErroSonda, match="código 3"):
        rodar(fake("import sys; sys.exit(3)", tmp_path)._chamar("snapshot"))


def espiar_matar(monkeypatch):
    mortos = []
    original = sonda_ad._matar

    def espia(proc):
        mortos.append(proc)
        original(proc)
    monkeypatch.setattr(sonda_ad, "_matar", espia)
    return mortos


def test_estoura_o_teto_e_mata(tmp_path, monkeypatch):
    mortos = espiar_matar(monkeypatch)
    t0 = time.monotonic()
    with pytest.raises(ErroSonda, match="teto"):
        rodar(fake("import time; time.sleep(60)", tmp_path, teto=0.5)._chamar("snapshot"))
    assert time.monotonic() - t0 < 10 and len(mortos) == 1 and mortos[0].returncode is not None


def test_cancelar_mata_o_processo(tmp_path, monkeypatch):
    mortos = espiar_matar(monkeypatch)

    async def cena():
        t = asyncio.create_task(fake("import time; time.sleep(60)", tmp_path, teto=30)._chamar("snapshot"))
        await asyncio.sleep(1)
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t
        await asyncio.wait_for(mortos[0].wait(), 5)
    rodar(cena())
    assert len(mortos) == 1 and mortos[0].returncode is not None


def test_log_so_com_o_codigo(tmp_path, caplog):
    env = {"ok": False, "error": {"code": "AMBIGUOUS_TARGET", "message": "Conteúdo Secreto"}}
    with pytest.raises(ErroSonda):
        rodar(devolve(env, tmp_path)._chamar("click", "@s1:e2"))
    assert "Conteúdo Secreto" not in caplog.text


# --- 9.3: leitura ---

ARVORE = {"ok": True, "data": {
    "complete": True, "window": {"id": "w-77", "title": "Spotify Premium"},
    "tree": {"role": "window", "name": "Spotify", "children": [
        {"role": "text", "name": "Tocando agora"},
        {"ref_id": "@s1:e1", "role": "button", "name": "Reproduzir", "children": [{"role": "text", "name": "Play"}]},
        {"ref_id": "@s1:e2", "role": "textfield", "name": "Senha", "states": ["protected"]},
        {"role": "list", "name": "Playlists", "children": [{"ref_id": "@s1:e3", "role": "listitem", "name": "Rock"}]}]}}}
ECO_ARGV = "import sys,json; print(json.dumps({'ok':True,'data':{'complete':True,'argv':sys.argv[1:]}}))"


def leitor(obj, tmp_path, processo="spotify", **k):
    return devolve(obj, tmp_path, processo_de=lambda h: processo, **k)


def test_leitura_vira_a_mesma_estrutura(tmp_path):
    from src.conversa.pc import Leitura
    from src.conversa.regras_pc import Elemento
    r = rodar(leitor(ARVORE, tmp_path).ler(77))
    assert isinstance(r, Leitura) and r.hwnd == 77 and r.endereco is None and r.titulo == "Spotify Premium"
    assert r.texto == "Spotify Tocando agora Play Playlists" and r.cortado is False  # nomes dos nós sem ref_id
    assert all(isinstance(e, Elemento) for e in r.elementos) and [e.nome for e in r.elementos] == ["Reproduzir", "Senha", "Rock"]
    play, _, rock = r.elementos
    assert (play.tipo, play.runtime_id, play.texto_interno, play.ancestrais) == ("Button", "@s1:e1", "Play", ("Spotify",))
    assert rock.tipo == "ListItem" and rock.ancestrais == ("Spotify", "Playlists") and rock.host_do_link is None


def test_campo_de_senha_marcado(tmp_path):
    ed = rodar(leitor(ARVORE, tmp_path).ler(77)).elementos[1]
    assert ed.tipo == "Edit" and ed.senha is True


def test_campo_seguro_nao_vaza_nada(tmp_path):
    seguro = {"ref_id": "@s1:e9", "role": "textfield", "name": "Senha", "value": "hunter2", "states": ["protected"],
              "children": [{"role": "text", "name": "SEGREDO-FILHO"}, {"ref_id": "@s1:e10", "role": "button", "name": "Mostrar"}]}
    solto = {"role": "text", "name": "SEGREDO-SOLTO", "states": ["protected"]}
    arvore = {"ok": True, "data": {"complete": True, "tree": {"role": "window", "name": "Login", "children": [
        {"role": "group", "name": "Form", "children": [seguro, solto,
                                                         {"ref_id": "@s1:e11", "role": "button", "name": "Entrar"}]}]}}}
    r = rodar(leitor(arvore, tmp_path).ler(1))
    resto = " ".join([r.texto, *(e.texto_interno for e in r.elementos), *(a for e in r.elementos for a in e.ancestrais)])
    for tabu in ("hunter2", "SEGREDO", "Senha"):
        assert tabu not in resto
    assert [(e.runtime_id, e.senha) for e in r.elementos] == [("@s1:e9", True), ("@s1:e11", False)]


def test_executavel_ausente_vira_erro_e_nao_agiu(tmp_path):
    s = SondaAD(comando=[str(tmp_path / "nao-existe.exe")], home=tmp_path / "ad", processo_de=lambda h: "spotify")
    with pytest.raises(ErroSonda, match="iniciar"):
        rodar(s._chamar("snapshot"))
    assert rodar(s.clicar(1, elemento(), None)) is False and rodar(s.voltar(1)) is False


def test_leitura_parcial_vira_cortado(tmp_path):
    parcial = {"ok": True, "data": {"complete": False, "tree": {"ref_id": "@s1:e1", "role": "button", "name": "X"}}}
    assert rodar(leitor(parcial, tmp_path).ler(1)).cortado is True


def test_ler_chama_snapshot_com_a_janela(tmp_path):
    s = fake(ECO_ARGV, tmp_path, processo_de=lambda h: "spotify")
    chamadas = []
    original = s._chamar

    async def espia(*a, **k):
        chamadas.append(a)
        return await original(*a, **k)
    s._chamar = espia
    assert rodar(s.ler(5)).elementos == ()
    assert chamadas[0][:3] == ("snapshot", "--window-id", "w-5")


def test_chrome_proibido_e_sem_processo_nao_sao_lidos(tmp_path):
    marca = tmp_path / "rodou"
    cod = f"open({str(marca)!r}, 'w').close(); print('{{}}')"
    for proc in ("chrome", "consent", ""):  # Chrome: sem host de link no agent-desktop, só apps; consent é o aviso de UAC
        s = fake(cod, tmp_path, processo_de=lambda h, p=proc: p)
        with pytest.raises(ErroSonda, match="janela_nao_permitida"):
            rodar(s.ler(9))
    assert not marca.exists()


# --- 9.4: ações ---

def elemento(ref="@s1:e1", nome="Reproduzir", tipo="Button"):
    from src.conversa.regras_pc import Elemento
    return Elemento(id=0, nome=nome, tipo=tipo, runtime_id=ref)


def gravador(tmp_path, saida, **k):
    """Executável falso que anota o argv numa linha de `argv.json` e devolve `saida`."""
    cod = ("import sys,json\nopen(" + repr(str(tmp_path / "argv.json")) + ",'a').write(json.dumps(sys.argv[1:])+'\\n')\n"
           "print(json.dumps(" + repr(saida) + "))")
    return fake(cod, tmp_path, processo_de=lambda h: "spotify", **k)


def argvs(tmp_path):
    import json
    return [json.loads(x) for x in (tmp_path / "argv.json").read_text().splitlines()]


def erro(codigo):
    return {"ok": False, "error": {"code": codigo, "message": "texto da janela"}}


def test_clicar_usa_a_referencia(tmp_path):
    s = gravador(tmp_path, {"ok": True, "data": {"action": "click", "disposition": "delivered_verified"}})
    assert rodar(s.clicar(5, elemento(), None)) is True
    assert argvs(tmp_path) == [["click", "@s1:e1"]]


def test_referencia_vencida_nao_agiu(tmp_path):
    assert rodar(gravador(tmp_path, erro("STALE_REF")).clicar(5, elemento(), None)) is False


def test_alvo_ambiguo_nao_agiu(tmp_path):
    assert rodar(gravador(tmp_path, erro("AMBIGUOUS_TARGET")).clicar(5, elemento(), None)) is False


def test_digitar_usa_valor_direto(tmp_path):
    s = gravador(tmp_path, {"ok": True, "data": {}})
    assert rodar(s.digitar(5, elemento("@s1:e2", "Busca", "Edit"), "-rock ç", None, acrescentar=False)) is True
    assert argvs(tmp_path) == [["set-value", "@s1:e2", "--", "-rock ç"]]  # nada de `type` nem --headed


def test_rolar_pede_a_direcao(tmp_path):
    s = gravador(tmp_path, {"ok": True, "data": {}})
    assert rodar(s.rolar(5, "down")) is True
    assert argvs(tmp_path) == [["scroll", "--window-id", "w-5", "--direction", "down"]]


def test_voltar_acha_o_botao_e_clica(tmp_path):
    arvore = {"ok": True, "data": {"complete": True, "tree": [
        {"ref_id": "@s2:e1", "role": "button", "name": "Reproduzir"}, {"ref_id": "@s2:e2", "role": "button", "name": "Voltar"}]}}
    s = gravador(tmp_path, arvore)
    assert rodar(s.voltar(5)) is True
    assert argvs(tmp_path)[-1] == ["click", "@s2:e2"]


def test_voltar_sem_botao_nao_agiu(tmp_path):
    s = gravador(tmp_path, {"ok": True, "data": {"complete": True, "tree": []}})
    assert rodar(s.voltar(5)) is False and len(argvs(tmp_path)) == 1  # só a leitura


def test_acao_em_janela_do_chrome_nao_roda(tmp_path):
    s = fake("open(" + repr(str(tmp_path / "rodou")) + ", 'w').close()", tmp_path, processo_de=lambda h: "chrome")
    assert rodar(s.clicar(5, elemento(), None)) is False and not (tmp_path / "rodou").exists()


def test_janela_uwp_da_seguranca_do_windows_e_recusada_pelo_titulo(tmp_path):
    for titulo, ok in (("Segurança do Windows", False), ("Windows Security", False), ("Calculadora", True)):
        s = leitor(ARVORE, tmp_path, processo="applicationframehost", titulo_de=lambda h, t=titulo: t)
        assert s.aceita(1) is ok


def test_outros_navegadores_sao_recusados_na_leitura(tmp_path):
    for proc in ("msedge", "firefox", "opera", "brave", "vivaldi", "iexplore"):
        assert leitor(ARVORE, tmp_path, processo=proc).aceita(1) is False


def test_ref_id_e_estado_protegido_no_json_real(tmp_path):
    """11/11: o 1.2.0 dá `ref_id` (não `ref`) e `states`; senha vem de `states` (palavra provável, não vista no JSON real)."""
    arvore = {"ok": True, "data": {"complete": True, "window": {"id": "w-1", "title": "T"}, "tree": {"role": "window", "children": [
        {"role": "textfield", "name": "Editor", "ref_id": "@s9:e1", "states": ["focused"], "available_actions": ["SetValue"]},
        {"role": "textfield", "name": "Campo", "ref_id": "@s9:e2", "states": ["protected"]}]}}}
    a, b = rodar(leitor(arvore, tmp_path).ler(1)).elementos
    assert (a.tipo, a.runtime_id, a.senha) == ("Edit", "@s9:e1", False) and b.senha is True


def test_app_fora_da_antiga_lista_e_lido(tmp_path):
    s = leitor(ARVORE, tmp_path, processo="notepad")
    assert rodar(s.ler(1)).titulo == "Spotify Premium"


# --- 9.5: composição e constante ---
from src.conversa.pc import Falso
from src.conversa.sonda_ad import SondaComposta, escolher_sonda, executavel


def composta(processo, minimizada=False, leitura="leitura-atual"):
    atual = Falso(leituras=[leitura])
    ad = SondaAD(comando=["nao-roda"], processo_de=lambda h: processo)
    chamadas = []

    async def ler(h):
        chamadas.append("ad")
        return "leitura-ad"
    ad.ler = ler
    return atual, ad, chamadas, SondaComposta(atual, ad, minimizada=lambda h: minimizada)


def test_sem_executavel_usa_a_sonda_atual(caplog):
    atual = Falso()
    assert escolher_sonda(atual, frozenset(), "agent-desktop", procurar=lambda n: None) is atual
    assert "agent-desktop não encontrado" in caplog.text
    assert escolher_sonda(atual, frozenset(), "uia") is atual
    assert isinstance(escolher_sonda(atual, frozenset(), "agent-desktop", procurar=lambda n: "x"), SondaComposta)


def test_cmd_do_npm_vira_o_exe_real(tmp_path):
    cmd = tmp_path / "agent-desktop.CMD"
    cmd.write_text("")
    assert executavel(lambda n: str(cmd)) is None  # .cmd sem o .exe ao lado: não serve
    exe = tmp_path / "node_modules" / "agent-desktop" / "bin" / "agent-desktop-win32-x64.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    assert executavel(lambda n: str(cmd)) == str(exe)
    assert executavel(lambda n: "C:/x/agent-desktop.exe") == "C:/x/agent-desktop.exe"


def test_composicao_manda_midia_para_a_sonda_atual():
    atual, ad, chamadas, c = composta("spotify")
    rodar(c.midias())
    rodar(c.trazer(1))
    assert {"midias", "trazer"} <= {x[0] for x in atual.chamadas} and chamadas == []


def _leitura(*els):
    from src.conversa.pc import Leitura
    return Leitura(1, None, "t", "", tuple(els), False)


def test_buscar_em_app_lido_pela_sondaad_usa_o_id_da_sonda_atual():
    from src.conversa.regras_pc import Elemento
    pedido = Elemento(0, "Pesquisar", "Edit", runtime_id="@ad:1")
    seu = Elemento(5, "Pesquisar", "Edit", runtime_id="uia-9")
    atual, ad, chamadas, c = composta("spotify", leitura=_leitura(seu, Elemento(6, "Outro", "Edit")))
    assert rodar(c.buscar(1, pedido, "musica", None)) is True
    assert atual.chamadas[-1] == ("buscar", 1, seu, "musica", None) and chamadas == []


def test_buscar_com_par_sensivel_na_releitura_nao_age():
    from src.conversa.regras_pc import Elemento
    pedido = Elemento(0, "Senha", "Edit", runtime_id="@ad:1")
    atual, ad, chamadas, c = composta("spotify", leitura=_leitura(Elemento(5, "Senha", "Edit", senha=True)))
    assert rodar(c.buscar(1, pedido, "x", None)) is False
    assert all(x[0] != "buscar" for x in atual.chamadas)


def test_buscar_ambiguo_ou_sem_par_nao_age():
    from src.conversa.regras_pc import Elemento
    pedido = Elemento(0, "Pesquisar", "Edit", runtime_id="@ad:1")
    dois = _leitura(Elemento(5, "Pesquisar", "Edit"), Elemento(6, "Pesquisar", "Edit"))
    atual, ad, chamadas, c = composta("spotify", leitura=dois)
    assert rodar(c.buscar(1, pedido, "x", None)) is False
    atual, ad, chamadas, c = composta("spotify", leitura=_leitura())
    assert rodar(c.buscar(1, pedido, "x", None)) is False
    assert all(x[0] != "buscar" for x in atual.chamadas)


def test_buscar_no_chrome_passa_o_elemento_como_veio():
    from src.conversa.regras_pc import Elemento
    pedido = Elemento(0, "Pesquisar", "Edit", runtime_id="uia-1")
    atual, ad, chamadas, c = composta("chrome")
    assert rodar(c.buscar(1, pedido, "x", None)) is True
    assert atual.chamadas == [("buscar", 1, pedido, "x", None)]


def test_minimizada_que_nao_traz_cai_na_sonda_atual():
    atual, ad, chamadas, c = composta("spotify", minimizada=True)
    atual.trazer_ok = False
    assert rodar(c.ler(7)) == "leitura-atual" and chamadas == []


def test_janela_do_chrome_na_composicao_nunca_chama_a_sondaad():
    atual, ad, chamadas, c = composta("chrome")
    rodar(c.ler(7))
    assert chamadas == [] and atual.chamadas[0][0] == "ler"


def test_app_permitido_le_pela_sondaad_e_minimizado_traz_antes():
    atual, ad, chamadas, c = composta("spotify", minimizada=True)
    assert rodar(c.ler(7)) == "leitura-ad" and chamadas == ["ad"] and atual.chamadas[0][0] == "trazer"


def test_digitar_acrescentando_le_o_valor_e_mantem_o_que_existe(tmp_path):
    """11/11: o set-value troca o valor inteiro; no modo acrescentar o texto novo vai DEPOIS do atual, em linha nova."""
    s = gravador(tmp_path, {"ok": True, "data": {"value": "oi tudo bem"}})
    assert rodar(s.digitar(5, elemento("@s1:e2", "Editor", "Edit"), "frase", None, acrescentar=True)) is True
    assert argvs(tmp_path) == [["get", "@s1:e2", "--property", "value"], ["get", "@s1:e2", "--property", "text"],
                               ["set-value", "@s1:e2", "--", "oi tudo bem\r\nfrase"]]


def test_acrescentar_em_campo_vazio_so_escreve(tmp_path):
    s = gravador(tmp_path, {"ok": True, "data": {"value": ""}})
    assert rodar(s.digitar(5, elemento("@s1:e2", "Editor", "Edit"), "frase", None, acrescentar=True)) is True
    assert argvs(tmp_path)[-1] == ["set-value", "@s1:e2", "--", "frase"]


def test_acrescentar_sem_conseguir_ler_o_valor_nao_escreve(tmp_path):
    """Nunca arrisca apagar: sem o valor atual, não age."""
    assert rodar(gravador(tmp_path, erro("AMBIGUOUS_TARGET")).digitar(5, elemento(), "x", None, acrescentar=True)) is False
    assert [a[0] for a in argvs(tmp_path)] == ["get"]

def test_acrescentar_em_documento_grande_ou_leitura_que_difere_nao_escreve(tmp_path):
    """Leitura cortada + set-value apagaria o resto do documento."""
    grande = gravador(tmp_path, {"ok": True, "data": {"value": "x" * 2001}})
    assert rodar(grande.digitar(5, elemento("@s1:e2", "Editor", "Edit"), "y", None, acrescentar=True)) is False
    assert "set-value" not in [a[0] for a in argvs(tmp_path)]
    cod = ("import sys,json" + chr(10) + "p=sys.argv[1:]" + chr(10) + "print(json.dumps({'ok': True, 'data': {'value': 'curto' if 'text' in p else 'curto e mais'}}))")
    dif = fake(cod, tmp_path, processo_de=lambda h: "spotify")
    assert rodar(dif.digitar(5, elemento("@s1:e2", "Editor", "Edit"), "y", None, acrescentar=True)) is False


def test_acrescentar_nao_deixa_linha_em_branco_quando_o_texto_ja_termina_em_quebra(tmp_path):
    s = gravador(tmp_path, {"ok": True, "data": {"value": "oi" + chr(13)}})
    assert rodar(s.digitar(5, elemento("@s1:e2", "Editor", "Edit"), "frase", None, acrescentar=True)) is True
    assert argvs(tmp_path)[-1] == ["set-value", "@s1:e2", "--", "oi" + chr(13) + "frase"]


def _notepad(valor, texto, tmp_path, erro_no_text=False):
    """Executável falso com o formato real medido (11/11): `value` do editor vazio é "", mas `text` devolve o NOME do campo."""
    cod = ("import sys,json" + chr(10) + "p=sys.argv[1:]" + chr(10)
           + "open(" + repr(str(tmp_path / "argv.json")) + ",'a').write(json.dumps(p)+chr(10))" + chr(10)
           + ("if 'text' in p: print(json.dumps({'ok': False, 'error': {'code': 'AMBIGUOUS_TARGET'}})); sys.exit(1)" + chr(10) if erro_no_text else "")
           + "print(json.dumps({'ok': True, 'data': {'property': p[2], 'ref': p[1], 'value': " + repr(texto) + " if 'text' in p else " + repr(valor) + "}}))")
    return fake(cod, tmp_path, processo_de=lambda h: "notepad")


def test_editor_vazio_do_notepad_escreve_mesmo_com_text_devolvendo_o_nome(tmp_path):
    """Causa dos 'leitura_nao_confiavel' de 11/11: value "" != text "Editor de texto" (nome do campo)."""
    s = _notepad("", "Editor de texto", tmp_path)
    assert rodar(s.digitar(5, elemento("@s1:e1", "Editor de texto", "Edit"), "frase", None, acrescentar=True)) is True
    assert argvs(tmp_path)[-1] == ["set-value", "@s1:e1", "--", "frase"]


def test_editor_com_texto_exige_value_igual_a_text_mas_sem_text_escreve(tmp_path):
    s = _notepad("abc", "abc", tmp_path)
    assert rodar(s.digitar(5, elemento("@s1:e1", "Editor de texto", "Edit"), "frase", None, acrescentar=True)) is True
    assert argvs(tmp_path)[-1] == ["set-value", "@s1:e1", "--", "abc\r\nfrase"]
    s = _notepad("abc", "abcdef", tmp_path / "c") if (tmp_path / "c").mkdir() is None else None
    assert rodar(s.digitar(5, elemento("@s1:e1", "Editor de texto", "Edit"), "frase", None, acrescentar=True)) is False


def test_editor_do_notepad_real_nunca_e_bloqueado_vazio_ou_com_texto_ou_arquivo_de_nome_de_login():
    """JSON real do agent-desktop 1.2.0 no Notepad (aba vazia e aba com texto): o editor é textfield 'Editor de texto'."""
    from src.conversa.regras_pc import digitacao_bloqueada, e_campo_sensivel
    def arvore(aba, titulo):
        return {"role": "window", "name": titulo, "children": [
            {"role": "group", "children": [{"role": "textfield", "name": "Editor de texto", "ref_id": "@s1:e1", "states": ["focused"]}]},
            {"role": "group", "children": [{"role": "tablist", "children": [{"role": "listbox", "ref_id": "@s1:e2", "children": [
                {"role": "tab", "name": aba, "ref_id": "@s1:e3", "states": ["selected"], "children": [
                    {"role": "button", "name": "Fechar Guia", "ref_id": "@s1:e4"}]}]},
                {"role": "button", "name": "Adicionar Nova Guia", "ref_id": "@s1:e5"}]}]},
            {"role": "group", "children": [{"role": "menu", "name": "Sistema"}]}]}
    for aba, titulo in (("Sem título. Não modificado.", " Sem título - Bloco de notas"), ("abc. Modificado.", "* abc - Bloco de notas"),
                        ("senha do wifi.txt. Modificado.", "* senha do wifi.txt - Bloco de notas"),
                        ("Entrar no sistema.txt. Não modificado.", "Entrar no sistema.txt - Bloco de notas")):
        elementos, textos = [], []
        sonda_ad._percorrer(arvore(aba, titulo), (), elementos, textos)
        editor = next(e for e in elementos if e.nome == "Editor de texto")
        assert editor.tipo == "Edit" and not e_campo_sensivel(editor)
        assert digitacao_bloqueada(editor, titulo, " ".join(textos), "notepad") is False
    # fora de editor de texto puro (Chrome, app qualquer) a isenção não vale: "Rich text editor" de página de login
    from src.conversa.regras_pc import Elemento
    rico = Elemento(0, "Text editor", "Edit")
    assert digitacao_bloqueada(rico, "Entrar - Site", "", "chrome") and digitacao_bloqueada(rico, "Entrar - Site", "")
    assert not digitacao_bloqueada(rico, "Entrar - Site", "", "notepad")
    assert digitacao_bloqueada(Elemento(0, "Editor de texto", "Edit"), "senha.txt - Bloco de notas", "", "spotify")


def test_editor_vazio_so_escreve_se_text_for_vazio_ou_o_nome_do_campo(tmp_path):
    """Revisão: value "" sem erro em documento com texto apagaria tudo; `text` precisa confirmar (vazio ou o nome)."""
    el = elemento("@s1:e1", "Editor de texto", "Edit")
    for n, (texto, esperado) in enumerate((("", True), ("Editor de texto", True), ("conteudo do documento", False))):
        d = tmp_path / str(n)
        d.mkdir()
        assert rodar(_notepad("", texto, d).digitar(5, el, "x", None, acrescentar=True)) is esperado
    d = tmp_path / "e"
    d.mkdir()
    assert rodar(_notepad("", "", d, erro_no_text=True).digitar(5, el, "x", None, acrescentar=True)) is False  # sem o text: não escreve
    d = tmp_path / "f"
    d.mkdir()
    assert rodar(_notepad("abc", "abc", d, erro_no_text=True).digitar(5, el, "x", None, acrescentar=True)) is False
