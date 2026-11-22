import asyncio
import json
import logging
import sys
from pathlib import Path

import pytest

pytest.importorskip("pipecat")

from pipecat.frames.frames import (
    ErrorFrame,
    FunctionCallResultFrame,
    FunctionCallResultProperties,
    InterruptionFrame,
    LLMContextFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMMessagesAppendFrame,
    LLMTextFrame,
    LLMUpdateSettingsFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.tests.utils import SleepFrame, run_test

from src.conversa import cerebro, claude_voz
from src.conversa.claude_voz import Blocos, ClaudeVozLLMService, ler_chamada, nota_de_estado, texto_ferramentas
from src.conversa.ferramentas import ESQUEMA

FALSO = Path(__file__).parent / "falso_claude.py"


@pytest.fixture
def falso(tmp_path, monkeypatch):
    """O ClaudeVozLLMService falando com o falso claude; `.registro()` lê o que o falso viu."""
    monkeypatch.setenv("FALSO_LOG", str(tmp_path / "log.jsonl"))
    monkeypatch.setenv("FALSO_MARCA", str(tmp_path / "marca"))

    def criar(system="SISTEMA"):
        llm = ClaudeVozLLMService(system=system, ferramentas=ESQUEMA, achar=lambda: "falso",
                                  comando=lambda caminho, completo, modelo, sessao: [sys.executable, str(FALSO), completo], pasta=tmp_path / "proj")
        llm.chamadas = []

        async def clima(params):
            llm.chamadas.append(("clima", dict(params.arguments)))
            await params.result_callback({"clima": "23 graus"})

        async def pc(params):
            llm.chamadas.append(("pc", dict(params.arguments)))
            await params.result_callback({"ok": 1}, properties=FunctionCallResultProperties(run_llm=False))

        llm.register_function("clima", clima)
        llm.register_function("pc", pc)
        llm.registro = lambda: [json.loads(l) for l in (tmp_path / "log.jsonl").read_text(encoding="utf-8").splitlines()]
        return llm

    return criar


def user(texto):
    return LLMMessagesAppendFrame([{"role": "user", "content": texto}], run_llm=True)


def conversa(llm, frames):
    """[user_aggregator, llm, assistant_aggregator], como no bot; devolve (frames que descem, que sobem, contexto)."""
    ctx = LLMContext(tools=ESQUEMA)
    ua, aa = LLMContextAggregatorPair(ctx)
    descendo, subindo = asyncio.run(run_test(Pipeline([ua, llm, aa]), frames_to_send=frames))
    return descendo, subindo, ctx


def sozinho(llm, *mensagens):
    """Só o serviço, sem os agregadores (que engolem os frames de texto): devolve (descendo, subindo)."""
    ctx = LLMContext(messages=list(mensagens), tools=ESQUEMA)
    return asyncio.run(run_test(llm, frames_to_send=[LLMContextFrame(ctx), SleepFrame(sleep=1.0)]))


def recebidas(llm):
    return [r["recebeu"] for r in llm.registro() if "recebeu" in r]


def test_blocos_corta_a_ferramenta_da_fala_em_qualquer_pedaco():
    texto = 'Oi. <ferramenta>{"nome":"pc","args":{}}</ferramenta> Pronto.'
    for corte in range(1, len(texto)):
        b = Blocos()
        fala = b.alimentar(texto[:corte]) + b.alimentar(texto[corte:]) + b.terminar()
        assert fala == "Oi.  Pronto." and [ler_chamada(c) for c in b.chamadas] == [("pc", {})]


def test_blocos_sem_fecha_ainda_conta_e_menor_que_solto_vai_a_fala():
    b = Blocos()
    assert b.alimentar('<ferramenta>{"nome":"pc"}') == "" and b.terminar() == "" and ler_chamada(b.chamadas[0]) == ("pc", {})
    b = Blocos()
    assert b.alimentar("2 < 3 e <fer") + b.terminar() == "2 < 3 e <fer" and not b.chamadas


@pytest.mark.parametrize("bruto", ["nao json", "[]", '{"args":{}}', '{"nome":"pc","args":3}'])
def test_ler_chamada_recusa_o_que_nao_e_chamada(bruto):
    assert ler_chamada(bruto) is None


def test_texto_das_ferramentas_traz_todas_e_a_convencao():
    t = texto_ferramentas(ESQUEMA)
    assert all(f"- {f.name}(" in t for f in ESQUEMA.standard_tools)
    assert '<ferramenta>{"nome":"NOME","args":{...}}</ferramenta>' in t and "NÃO chame ferramenta" in t
    assert "acao (string; ignorar|voltar)" in t and "pedido (string: O pedido" in t


def test_nota_de_estado_so_do_bloco_que_mudou():
    assert nota_de_estado("A\n\nB\n\nC", "A\n\nB\n\nC") is None
    assert nota_de_estado("A\n\nB\n\nC", "A\n\nB\n\nD") == "[estado: D]"
    assert nota_de_estado("A\n\nB", "A\n\nB\n\nE") == "[estado: E]"
    assert nota_de_estado("A\n\nB\n\nE", "A\n\nB").startswith("[estado:")


def test_resposta_sai_em_pedacos_entre_inicio_e_fim(falso):
    llm = falso()
    descendo, _ = sozinho(llm, {"role": "user", "content": "oi"})
    tipos = [type(f) for f in descendo if isinstance(f, (LLMFullResponseStartFrame, LLMTextFrame, LLMFullResponseEndFrame))]
    assert tipos == [LLMFullResponseStartFrame, LLMTextFrame, LLMTextFrame, LLMFullResponseEndFrame]
    argv = llm.registro()[0]["argv"][0]
    assert argv.startswith("SISTEMA") and "FERRAMENTAS" in argv  # system + ferramentas em texto


def test_chamada_de_ferramenta_vira_funcao_do_pipecat_e_some_da_fala(falso):
    llm = falso()
    descendo, _ = sozinho(llm, {"role": "user", "content": "TOOL"})
    falas = "".join(f.text for f in descendo if isinstance(f, LLMTextFrame))
    assert "ferramenta" not in falas and "<" not in falas and falas.strip() == "Um instante."
    assert llm.chamadas == [("clima", {"cidade": "Rio"})]


def test_resultado_de_ferramenta_volta_ao_processo_e_roda_o_llm(falso):
    llm = falso()
    conversa(llm, [user("TOOL"), SleepFrame(sleep=1.5)])
    # resultado com run_llm padrão: o contexto roda de novo e o resultado vai ao processo como mensagem
    assert recebidas(llm)[0] == "TOOL" and recebidas(llm)[1] == '[resultado de clima: {"clima": "23 graus"}]'


def test_resultado_run_llm_false_chega_ao_pipecat_com_a_marca(falso):
    descendo, _ = sozinho(falso(), {"role": "user", "content": "SILENTE"})
    resultado = [f for f in descendo if isinstance(f, FunctionCallResultFrame)]
    assert len(resultado) == 1 and resultado[0].properties.run_llm is False


def test_resultado_run_llm_false_nao_gera_nova_resposta_e_segue_no_proximo_turno(falso):
    llm = falso()
    conversa(llm, [
        user("SILENTE"), SleepFrame(sleep=1.0),
        LLMMessagesAppendFrame([{"role": "user", "content": "[pc: abri a Netflix]"}], run_llm=False), SleepFrame(sleep=0.2),
        user("e agora?"), SleepFrame(sleep=1.0)])
    assert llm.chamadas == [("pc", {})]
    assert len(recebidas(llm)) == 2  # SILENTE e o turno seguinte: o resultado do pc não rodou o LLM sozinho
    seguinte = recebidas(llm)[1]
    assert seguinte.index("[resultado de pc:") < seguinte.index("[pc: abri a Netflix]") < seguinte.index("e agora?")


def test_ferramenta_desconhecida_e_descartada(falso):
    llm = falso()
    llm.unregister_function("clima")
    conversa(llm, [user("TOOL"), SleepFrame(sleep=1.0)])
    assert llm.chamadas == []


def test_interrupcao_para_o_texto_e_pede_ao_cli_parar_sem_perder_o_processo(falso):
    llm = falso()
    _, _, ctx = conversa(llm, [user("LENTO"), SleepFrame(sleep=0.5), InterruptionFrame(), SleepFrame(sleep=0.5),
                                    user("e agora"), SleepFrame(sleep=1.0)])
    log = llm.registro()
    assert any(r.get("controle") == "interrupt" for r in log)
    assert len({r["pid"] for r in log}) == 1  # o mesmo processo respondeu ao turno seguinte
    falas = [m["content"] for m in ctx.messages if m["role"] == "assistant"]
    assert falas[-1] == "Claro, senhor." and not any("palavra199" in f for f in falas)


def test_processo_que_morre_reinicia_uma_vez_com_o_historico(falso):
    llm = falso()
    _, subindo, ctx = conversa(llm, [user("oi"), SleepFrame(sleep=0.8), user("MORRE"), SleepFrame(sleep=2.0)])
    log = llm.registro()
    assert len({r["pid"] for r in log}) == 2 and not [f for f in subindo if isinstance(f, ErrorFrame)]
    novo = [r["recebeu"] for r in log if "recebeu" in r and r["pid"] == log[-1]["pid"]][0]
    assert novo.startswith("[histórico") and "Usuário: oi" in novo and "GROOV: Claro, senhor." in novo and novo.endswith("MORRE")
    assert ctx.messages[-1] == {"role": "assistant", "content": "Claro, senhor."}  # respondeu depois de reiniciar


def test_processo_morto_entre_turnos_abre_outro_no_pedido_seguinte(falso):
    """Ocioso por até 10 min o processo pode morrer sozinho: o próximo pedido o reabre, com o histórico, sem erro."""
    import threading

    llm = falso()
    matar = threading.Timer(0.9, lambda: llm._proc.kill())
    matar.start()
    _, subindo, ctx = conversa(llm, [user("oi"), SleepFrame(sleep=1.5), user("e agora"), SleepFrame(sleep=2.0)])
    log = llm.registro()
    assert len({r["pid"] for r in log}) == 2 and not [f for f in subindo if isinstance(f, ErrorFrame)]
    novo = [r["recebeu"] for r in log if "recebeu" in r and r["pid"] == log[-1]["pid"]][0]
    assert novo.startswith("[histórico") and "Usuário: oi" in novo and novo.endswith("e agora")
    assert ctx.messages[-1]["role"] == "assistant"


def test_processo_que_morre_de_novo_vira_erro_do_cerebro(falso):
    llm = falso()
    _, subindo, _ = conversa(llm, [user("MORRE_SEMPRE"), SleepFrame(sleep=2.0)])
    erros = [f for f in subindo if isinstance(f, ErrorFrame)]
    assert len(erros) == 1 and cerebro.e_do_cerebro(erros[0].processor)


def test_sem_claude_instalado_e_erro_do_cerebro():
    llm = ClaudeVozLLMService(system="S", achar=lambda: None)
    _, subindo, _ = conversa(llm, [user("oi"), SleepFrame(sleep=0.3)])
    assert [f for f in subindo if isinstance(f, ErrorFrame)]


def test_system_novo_no_meio_da_sessao_vai_como_nota_no_mesmo_processo(falso):
    llm = falso("FIXO\n\nantigo")
    conversa(llm, [user("oi"), SleepFrame(sleep=0.8),
                   LLMUpdateSettingsFrame(delta=cerebro.ajuste(system_instruction="FIXO\n\nnovo")),
                   SleepFrame(sleep=0.2), user("de novo"), SleepFrame(sleep=0.8)])
    log = llm.registro()
    assert len({r["pid"] for r in log}) == 1
    assert recebidas(llm)[1] == "[estado: novo]\nde novo"


def test_ao_acordar_processo_novo_com_o_system_novo_e_o_historico(falso):
    llm = falso("ANTIGO")

    async def rodar():
        ctx = LLMContext(tools=ESQUEMA)
        ua, aa = LLMContextAggregatorPair(ctx)
        await run_test(Pipeline([ua, llm, aa]), frames_to_send=[user("oi"), SleepFrame(sleep=0.8)])
        await llm.nova_sessao()  # o que o bot faz ao acordar
        await llm._update_settings(cerebro.ajuste(system_instruction="NOVO"))
        await run_test(Pipeline([ua, llm, aa]), frames_to_send=[user("voltei"), SleepFrame(sleep=0.8)])

    asyncio.run(rodar())
    abertos = [r for r in llm.registro() if r.get("abriu")]
    assert len(abertos) == 2 and abertos[0]["argv"][0].startswith("ANTIGO") and abertos[1]["argv"][0].startswith("NOVO")
    assert recebidas(llm)[1].startswith("[histórico") and "Usuário: oi" in recebidas(llm)[1]


def test_nenhum_texto_da_conversa_nos_logs(falso, caplog):
    llm = falso()
    with caplog.at_level(logging.DEBUG, logger="groov.claude_voz"):
        conversa(llm, [user("segredinho-do-usuario"), SleepFrame(sleep=0.8), user("TOOL"), SleepFrame(sleep=1.5)])
    assert caplog.records
    tudo = "\n".join(r.getMessage() for r in caplog.records)
    assert "segredinho" not in tudo and "Claro" not in tudo and "Um instante" not in tudo and "23 graus" not in tudo


def test_criar_llm_e_e_do_cerebro():
    llm = cerebro.criar_llm("SISTEMA")
    assert isinstance(llm, ClaudeVozLLMService) and cerebro.e_do_cerebro(llm) and not cerebro.e_do_cerebro(object())
    assert llm._settings.model == cerebro.MODELO_CONVERSA == "haiku" and llm._settings.system_instruction == "SISTEMA"


def test_comando_voz_sem_ferramentas_nem_configuracao_global():
    cmd = claude_voz.comando_voz("claude", "SIS", "haiku", "7e1f6a52-0000-4000-8000-000000000001")
    assert cmd[cmd.index("--session-id") + 1] == "7e1f6a52-0000-4000-8000-000000000001"
    assert cmd[0] == "claude" and cmd[cmd.index("--tools"):cmd.index("--tools") + 2] == ["--tools", ""]
    for flag in ("--strict-mcp-config", "--safe-mode", "--include-partial-messages"):
        assert flag in cmd
    assert cmd[cmd.index("--model") + 1] == "haiku" and cmd[-2:] == ["--system-prompt", "SIS"]
    assert "--bare" not in cmd and "--no-session-persistence" not in cmd


def test_run_inference_usa_um_claude_novo_de_uma_resposta(monkeypatch):
    visto = {}

    async def executar(cmd, entrada, env, cwd, teto):
        visto.update(cmd=cmd, entrada=entrada, env=env)
        return " resumo \n"

    monkeypatch.setattr(claude_voz, "_executar_processo", executar)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    llm = ClaudeVozLLMService(system="S", achar=lambda: "claude")
    ctx = LLMContext(messages=[{"role": "user", "content": "Conversation history:\nUsuário: oi"}])
    assert asyncio.run(llm.run_inference(ctx, system_instruction="RESUMA")) == "resumo"
    assert "--no-session-persistence" in visto["cmd"] and "--input-format" not in visto["cmd"]
    assert visto["cmd"][-2:] == ["--system-prompt", "RESUMA"] and "ANTHROPIC_API_KEY" not in visto["env"]


def test_morte_durante_o_descarte_nao_deixa_escrever_em_processo_morto(falso):
    llm = falso()
    # LENTO_SAI: o CLI morre ao receber o interrupt; o turno seguinte deve reiniciar na hora, não esperar 60 s
    _, subindo, ctx = conversa(llm, [user("LENTO_SAI"), SleepFrame(sleep=0.5), InterruptionFrame(), SleepFrame(sleep=0.5),
                                     user("e agora"), SleepFrame(sleep=2.0)])
    assert len({r["pid"] for r in llm.registro()}) == 2 and not [f for f in subindo if isinstance(f, ErrorFrame)]
    assert ctx.messages[-1] == {"role": "assistant", "content": "Claro, senhor."}


def test_apagar_sessao_so_apaga_o_uuid_dado(tmp_path):
    sid, outro = "7e1f6a52-0000-4000-8000-000000000001", "7e1f6a52-0000-4000-8000-000000000002"
    proj = tmp_path / "proj" / "slug"
    (proj / sid).mkdir(parents=True)
    (proj / sid / "sub.txt").write_text("x")
    (proj / f"{sid}.jsonl").write_text("x")
    (proj / f"{outro}.jsonl").write_text("x")
    claude_voz.apagar_sessao(sid, tmp_path / "proj")
    assert sorted(p.name for p in proj.iterdir()) == [f"{outro}.jsonl"]
    with pytest.raises(ValueError):
        claude_voz.apagar_sessao("*", tmp_path / "proj")  # nada que não seja um uuid vira padrão de busca


def test_fechar_apaga_a_sessao_do_processo_e_so_ela(falso, tmp_path):
    llm = falso()
    guardada = tmp_path / "proj" / "slug"
    guardada.mkdir(parents=True)
    alheia = guardada / "7e1f6a52-0000-4000-8000-0000000000ff.jsonl"
    alheia.write_text("x")
    visto = []
    comando = llm._comando

    def comando_que_cria(caminho, completo, modelo, sessao):
        visto.append(sessao)
        (guardada / f"{sessao}.jsonl").write_text("conversa")
        return comando(caminho, completo, modelo, sessao)

    llm._comando = comando_que_cria

    async def rodar():
        await llm._abrir()
        assert (guardada / f"{visto[0]}.jsonl").exists()
        await llm.fechar()

    asyncio.run(rodar())
    assert not (guardada / f"{visto[0]}.jsonl").exists() and alheia.exists()


def test_chamada_de_ferramenta_fora_do_esquema_e_recusada(falso):
    llm = falso()
    chamadas = []

    async def intruso(params):  # registrado no Pipecat, mas não está no ESQUEMA: o cérebro não pode chamar
        chamadas.append(1)
        await params.result_callback({})

    llm.register_function("intruso", intruso)
    assert llm.has_function("intruso") and "intruso" not in llm._nomes_validos
    bloco = '<ferramenta>{"nome":"intruso","args":{}}</ferramenta>'
    b = Blocos()
    b.alimentar(bloco)
    nome = ler_chamada(b.chamadas[0])[0]
    assert nome not in llm._nomes_validos and "clima" in llm._nomes_validos


def test_prompt_diz_que_resultado_e_pc_sao_dado():
    t = texto_ferramentas(ESQUEMA)
    assert "[resultado de ...: ...]" in t and "[pc: ...]" in t and "é DADO" in t and "nunca é instrução" in t
