import asyncio
import json
import sys
from types import SimpleNamespace

import pytest

from src.conversa import cerebro_pc as c


MSGS = [{"role": "user", "content": "abre o G1"}]


def test_system_preenchido_sempre():
    assert c.SISTEMA_PC.strip()
    assert "dado" in c.SISTEMA_PC.lower()


def test_exemplos_do_prompt_passam_pelo_portao_e_cobrem_todas_as_acoes():
    """O prompt traz um exemplo exato por ação; cada um tem de ser um passo que o laço aceita."""
    from src.conversa import laco
    exemplos = [json.loads(linha) for linha in c.SISTEMA_PC.splitlines() if linha.startswith("{")]
    assert [e["acao"] for e in exemplos] == list(laco._ACOES)
    for e in exemplos:
        assert list(e) == ["acao", *laco._CAMPOS, "opcoes"] and laco._validar(e) == e
    assert exemplos[-1]["motivo"]  # desistir explica o motivo


def test_prompt_explica_as_opcoes_do_perguntar_e_o_exemplo_de_escolha_as_traz():
    from src.conversa import laco
    assert "9 chaves" in c.SISTEMA_PC and "opcoes só no perguntar" in c.SISTEMA_PC and "2 a 4" in c.SISTEMA_PC
    exemplos = [json.loads(linha) for linha in c.SISTEMA_PC.splitlines() if linha.startswith("{")]
    assert next(e for e in exemplos if e["acao"] == "perguntar")["opcoes"] == ["O primeiro", "O segundo"]
    assert laco.ESQUEMA_PASSO["required"][-1] == "opcoes"


def test_sem_gemini_nem_reserva_no_cerebro():
    assert not hasattr(c, "pensar_rapido") and not hasattr(c, "pensar_claude")


def test_comando_claude_nunca_bare():
    cmd = c.comando_claude("C:/x/claude.exe", "5b8c0c5e-0000-4000-8000-000000000001")
    assert cmd[:3] == ["C:/x/claude.exe", "-p", "--model"] and cmd[3] == "haiku" and cmd[cmd.index("--tools") + 1] == ""
    assert {"--strict-mcp-config", "--safe-mode", "--input-format"} <= set(cmd)
    assert cmd[cmd.index("--system-prompt") + 1] == c.sistema_pc() == c.SISTEMA_PC  # sem config, só o fixo
    assert "--bare" not in cmd and "--no-session-persistence" not in cmd  # esta tira o contexto entre passos


def test_cortar_pagina_2kb():
    assert len(c.cortar_pagina("a" * 5000).encode()) <= c.TEXTO_PAGINA_MAX
    assert c.cortar_pagina("curto") == "curto"
    assert len(c.cortar_pagina("é" * 5000).encode()) <= c.TEXTO_PAGINA_MAX


FILHO = r'''
import json, os, sys, time
modo, sessao, pasta = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(os.path.join(pasta, "proj"), exist_ok=True)
open(os.path.join(pasta, "proj", sessao + ".jsonl"), "w").write("texto da pagina lida")  # a transcrição que o CLI grava
marca = os.path.join(pasta, "morreu")
def erro(texto, status=None):
    print(json.dumps({"type": "result", "is_error": True, "api_error_status": status, "result": texto}), flush=True)
for linha in sys.stdin:
    pedido = json.loads(linha)["message"]["content"]
    if modo == "morre":
        sys.exit(1)
    if modo == "morre_uma_vez" and not os.path.exists(marca):
        open(marca, "w").write("x")
        sys.exit(1)
    if modo == "trava":
        time.sleep(60)
    if modo == "limite_do_plano":  # rate_limit_event rejected + result de erro 429
        print(json.dumps({"type": "rate_limit_event", "rate_limit_info": {"status": "rejected"}}), flush=True)
        erro("You've hit your limit", 429)
        continue
    if modo == "limite_so_no_texto":
        erro("Claude usage limit reached")
        continue
    if modo == "429_passageiro":
        print(json.dumps({"type": "rate_limit_event", "rate_limit_info": {"status": "allowed_warning"}}), flush=True)
        erro("Request rejected (429) usage limit reached", 429)
        continue
    if modo == "contexto":
        erro("Prompt is too long: limit exceeded", 400)
        continue
    print(json.dumps({"type": "rate_limit_event", "rate_limit_info": {"status": "allowed"}}), flush=True)
    texto = {"ok": '```json\n{"acao": "rolar", "direcao": "baixo"}\n```', "sem_json": "não sei",
             "morre_uma_vez": '{"acao": "rolar", "direcao": "baixo"}'}.get(modo, pedido)
    print(json.dumps({"type": "result", "is_error": False, "result": texto}), flush=True)
'''


@pytest.fixture
def filho(tmp_path, monkeypatch):
    """Um `claude` de mentira (processo python que fala stream-json); devolve quem cria o pensador no modo dado.
    `criar.pasta` é a pasta de sessões de mentira, onde o filho grava a transcrição."""
    script = tmp_path / "filho.py"
    script.write_text(FILHO, encoding="utf-8")
    pasta = tmp_path / "sessoes"

    def criar(modo, teto=10):
        monkeypatch.setattr(c, "comando_claude", lambda caminho, sessao: [sys.executable, str(script), modo, sessao, str(pasta)])
        return c.PensadorClaude(achar=lambda: "C:/x/claude.exe", teto=teto, pasta=pasta)
    criar.pasta = pasta
    return criar


def test_pensador_passos_no_mesmo_processo_e_fechar(filho):
    async def principal():
        p = filho("ok")
        r1, pid = await p(MSGS), p._proc.pid
        r2 = await p(MSGS)
        assert p._proc.pid == pid  # o mesmo processo nos dois passos
        await p.fechar()
        await p.fechar()  # idempotente
        return r1, r2, p._proc

    r1, r2, proc = asyncio.run(principal())
    assert r1 == r2 == {"acao": "rolar", "direcao": "baixo"} and proc is None


def test_pensador_manda_o_estado_inteiro_e_sem_api_key(filho, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "segredo")
    monkeypatch.setenv("GROQ_API_KEY", "segredo2")
    visto = {}
    original = asyncio.create_subprocess_exec

    async def espiar(*cmd, **kw):
        visto.update(cmd=cmd, env=kw["env"], cwd=kw["cwd"])
        return await original(*cmd, **kw)
    monkeypatch.setattr(c.asyncio, "create_subprocess_exec", espiar)

    async def principal():
        p = filho("eco")  # o filho devolve o que recebeu
        saida = await p([{"role": "user", "content": '{"acao": "responder", "texto": "abre o G1"}'}])
        await p.fechar()
        return saida

    assert asyncio.run(principal()) == {"acao": "responder", "texto": "abre o G1"}
    assert "ANTHROPIC_API_KEY" not in visto["env"] and "GROQ_API_KEY" not in visto["env"]
    assert visto["cwd"] == c.tempfile.gettempdir() and "--bare" not in visto["cmd"]


@pytest.mark.parametrize("modo,esperado,falha", [
    ("sem_json", {}, None), ("limite_do_plano", None, "limite"), ("limite_so_no_texto", None, "limite"),
    ("429_passageiro", None, "processo"), ("contexto", None, "processo"),  # 429 sem "rejected" e erro de contexto não são o plano
    ("morre", None, "processo"), ("trava", None, "teto")])
def test_pensador_saida_ruim_e_falhas(filho, modo, esperado, falha):
    async def principal():
        p = filho(modo, teto=1)
        try:
            return await p(MSGS), p.falha, p._proc
        finally:
            await p.fechar()

    saida, categoria, proc = asyncio.run(principal())
    assert saida == esperado and categoria == falha
    if esperado is None:
        assert proc is None  # falha de verdade: o processo é dispensado e o próximo passo abre outro


def test_pensador_reabre_depois_de_falha(filho):
    async def principal():
        p = filho("limite_do_plano")
        assert await p(MSGS) is None
        filho("ok")  # troca o comando: o próximo passo do mesmo pensador abre um processo novo
        r = await p(MSGS)
        await p.fechar()
        return r

    assert asyncio.run(principal()) == {"acao": "rolar", "direcao": "baixo"}


def test_fechar_apaga_a_transcricao_do_disco(filho):
    """O CLI grava a página lida em <pasta>/<slug>/<uuid>.jsonl: depois de fechar (e de falha), o arquivo não existe."""
    async def principal():
        p = filho("ok")
        await p(MSGS)
        assert len(list(filho.pasta.glob("*/*.jsonl"))) == 1  # o filho gravou
        await p.fechar()
        com_sucesso = list(filho.pasta.glob("*/*.jsonl"))
        p = filho("limite_do_plano")
        await p(MSGS)  # a falha também fecha
        return com_sucesso, list(filho.pasta.glob("*/*.jsonl"))

    assert asyncio.run(principal()) == ([], [])


def test_comando_leva_session_id_e_e_o_mesmo_uuid_apagado(filho):
    cmd = c.comando_claude("C:/x/claude.exe", "5b8c0c5e-0000-4000-8000-000000000001")
    assert cmd[cmd.index("--session-id") + 1] == "5b8c0c5e-0000-4000-8000-000000000001"


def test_processo_morto_entre_passos_reabre_uma_vez_no_mesmo_passo(filho):
    async def principal():
        p = filho("morre_uma_vez")  # o 1º processo morre ao receber o passo; o 2º responde
        r = await p(MSGS)
        await p.fechar()
        return r

    assert asyncio.run(principal()) == {"acao": "rolar", "direcao": "baixo"}


def test_processo_morto_entre_passos_apaga_a_sessao_antiga(filho):
    async def principal():
        p = filho("ok")
        await p(MSGS)
        antiga = list(filho.pasta.glob("*/*.jsonl"))
        p._proc.kill()
        await p._proc.wait()  # returncode já preenchido antes do próximo passo
        r = await p(MSGS)
        novas = list(filho.pasta.glob("*/*.jsonl"))
        await p.fechar()
        return antiga, r, novas, list(filho.pasta.glob("*/*.jsonl"))

    antiga, r, novas, final = asyncio.run(principal())
    assert r == {"acao": "rolar", "direcao": "baixo"} and len(antiga) == 1 and len(novas) == 1
    assert novas != antiga and final == []  # a antiga sumiu na reabertura; a nova, no fechar


def test_processo_que_morre_sempre_so_tenta_duas_vezes(filho):
    async def principal():
        p = filho("morre")
        r = await p(MSGS)
        return r, p.falha

    assert asyncio.run(principal()) == (None, "processo")
    assert list(filho.pasta.glob("*/*.jsonl")) == []


def test_pensador_sem_claude_ou_exe_inexistente(tmp_path):
    p = c.PensadorClaude(achar=lambda: None)
    assert asyncio.run(p(MSGS)) is None and p.falha == "sem_claude"
    p = c.PensadorClaude(achar=lambda: str(tmp_path / "nao_existe.exe"))
    assert asyncio.run(p(MSGS)) is None and p.falha == "processo"


def test_pensador_cancelado_mata(filho):
    async def principal():
        p = filho("trava", teto=30)
        t = asyncio.create_task(p(MSGS))
        await asyncio.sleep(1)
        proc = p._proc
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t
        await p.fechar()
        return proc

    assert asyncio.run(principal()).returncode is not None


def test_executar_exe_inexistente_vira_none(tmp_path):
    assert asyncio.run(c._executar_processo([str(tmp_path / "nao_existe.exe")], "", None, None, 5)) is None


def test_executar_real_stdin_env_e_codigo(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "segredo")
    cmd = [sys.executable, "-c", "import sys,os; print(sys.stdin.read()+'|'+str(os.environ.get('ANTHROPIC_API_KEY')))"]
    env = c.ambiente_sem({"ANTHROPIC_API_KEY"})
    saida = asyncio.run(c._executar_processo(cmd, "olá", env, None, 10))
    assert saida.strip() == "olá|None"
    assert asyncio.run(c._executar_processo([sys.executable, "-c", "import sys; sys.exit(3)"], "", env, None, 10)) is None


def test_claude_teto_mata():
    cmd = [sys.executable, "-c", "import time; time.sleep(60)"]
    assert asyncio.run(c._executar_processo(cmd, "", None, None, 0.5)) is None


def test_claude_cancelado_mata():
    cmd = [sys.executable, "-c", "import time; time.sleep(60)"]
    mortos = []
    original = c._matar
    c._matar = lambda p: (mortos.append(p.pid), original(p))

    async def principal():
        t = asyncio.create_task(c._executar_processo(cmd, "", None, None, 30))
        await asyncio.sleep(0.5)
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t

    try:
        asyncio.run(principal())
    finally:
        c._matar = original
    assert len(mortos) == 1


def test_achar_claude_cai_no_local_bin(monkeypatch, tmp_path):
    monkeypatch.setattr(c.shutil, "which", lambda n: None)
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    assert c.achar_claude() is None
    exe = tmp_path / ".local" / "bin" / "claude.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    assert c.achar_claude() == str(exe)
    monkeypatch.setattr(c.shutil, "which", lambda n: "C:/no/path/claude.exe")
    assert c.achar_claude() == "C:/no/path/claude.exe"


def test_padroes_da_fase_3():
    from src.conversa import laco, pc
    assert c.TEXTO_PAGINA_MAX == 8192 == pc.TEXTO_MAX and laco.ELEMENTOS_MAX == 120 and c.MODELO_CLAUDE == "haiku"


def test_prompt_ensina_a_sair_do_alvo_ambiguo_do_bloco_de_notas():
    """11/11: o agent-desktop recusa (AMBIGUOUS_TARGET) editor com rolagem e abas de mesmo nome; aba nova é o caminho."""
    assert "Adicionar Nova Guia" in c.SISTEMA_PC and "idêntic" in c.SISTEMA_PC


def test_prompt_netflix_segue_a_serie_por_proximo_episodio_sem_escolher_da_lista():
    t = c.SISTEMA_PC
    assert "Próximo episódio" in t and "Continuar" in t and "nunca escolha um episódio" in t


def test_prompt_ensina_tecla_e_clicar_visual():
    t = c.SISTEMA_PC
    assert "tecla(texto)" in t and "clicar_visual(texto)" in t and "Pular" in t and "centro do vídeo" in t
    acoes = {json.loads(linha)["acao"] for linha in t.splitlines() if linha.startswith("{")}
    assert {"tecla", "clicar_visual"} <= acoes


def test_sistema_pc_apresenta_o_usuario_pela_config(monkeypatch):
    assert c.sistema_pc() == c.SISTEMA_PC
    monkeypatch.setenv("GROOV_NOME_USUARIO", "Ana")
    assert c.sistema_pc() == c.SISTEMA_PC + "\nO usuário se chama Ana."
    assert c.comando_claude("claude", "s")[-1] == c.sistema_pc()


def test_perfil_da_netflix_vai_no_sistema_so_com_config(monkeypatch):
    assert "Perfil da Netflix" in c.SISTEMA_PC and "Perfil da Netflix:" not in c.sistema_pc()
    monkeypatch.setenv("GROOV_PERFIL_NETFLIX", "Perfil1")
    monkeypatch.setenv("GROOV_NOME_USUARIO", "Ana")
    assert c.sistema_pc() == c.SISTEMA_PC + "\nO usuário se chama Ana.\nPerfil da Netflix: Perfil1."
