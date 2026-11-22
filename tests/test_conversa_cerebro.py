import pytest

pytest.importorskip("pipecat")

from src.conversa import buscador, cerebro


def test_criar_llm_usa_o_modelo_e_a_instrucao():
    llm = cerebro.criar_llm("SISTEMA")
    assert llm._settings.model == cerebro.MODELO_CONVERSA and llm._settings.system_instruction == "SISTEMA"


def test_ajuste_leva_os_campos():
    assert cerebro.ajuste(system_instruction="NOVO").system_instruction == "NOVO"


def test_e_do_cerebro_so_para_o_servico_de_linguagem():
    assert cerebro.e_do_cerebro(cerebro.criar_llm("s"))
    assert not cerebro.e_do_cerebro(object())


def test_cerebro_e_o_haiku_do_plano_e_o_google_so_pesquisa():
    assert cerebro.MODELO_CONVERSA == "haiku"
    assert buscador.MODELO_BUSCA == "gemini-3.5-flash-lite" and buscador.CHAVE == "GOOGLE_API_KEY"
    assert not hasattr(cerebro, "CHAVE")


def test_nenhum_servico_do_google_no_cerebro():
    import inspect

    from src.conversa import claude_voz
    assert "GoogleLLMService" not in inspect.getsource(cerebro) + inspect.getsource(claude_voz)
