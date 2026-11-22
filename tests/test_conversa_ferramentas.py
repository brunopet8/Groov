import asyncio
from types import SimpleNamespace

import pytest

pytest.importorskip("pipecat")

from src.conversa import ferramentas
from src.conversa.ajudante import FALHOU
from src.conversa.ferramentas import (
    ESQUEMA,
    criar_ao_briefing,
    criar_ao_cancelar_timer,
    criar_ao_clima,
    criar_ao_coluna,
    criar_ao_janela,
    criar_ao_pc,
    criar_ao_tarefa,
    criar_ao_timer,
    criar_ao_vida,
    criar_entregar,
)
from src.conversa.laco import FRASE_UM_MOMENTO, Desfecho
from src.conversa.regras_pc import PedidoTimer
from src.conversa.sessao import Sessao
from src.conversa.turno import Turno


class TrabalhoFalso:
    def __init__(self, saida="Relatório.\nRESUMO: Pronto, senhor."):
        self.saida, self.rodando, self.cancelado, self.pedidos = saida, False, False, []

    async def executar(self, pedido, pasta):
        self.pedidos.append((pedido, pasta))
        return self.saida


def _rodar_trabalho(trabalho, tmp_path, conversando=True):
    falas = []
    sessao = Sessao()
    if conversando:
        sessao.estado = ferramentas.Estado.CONVERSANDO

    async def entregar(texto):
        falas.append(texto)

    async def main():
        ao = ferramentas.criar_ao_trabalho(sessao, trabalho, entregar, tmp_path, relogio=lambda: 0.0)
        frase = await ao("faz o relatório", tmp_path / "ws")
        await asyncio.gather(*list(ferramentas._tarefas))
        return frase
    return asyncio.run(main()), falas, sessao


def test_escolher_frase_nao_repete():
    for anterior in ferramentas.FRASES_TRABALHO:
        assert ferramentas.escolher_frase(anterior) != anterior
    assert ferramentas.escolher_frase(None, sorteio=lambda xs: xs[0]) == ferramentas.FRASES_TRABALHO[0]


def test_ao_trabalho_entrega_e_salva(tmp_path):
    t = TrabalhoFalso()
    frase, falas, _ = _rodar_trabalho(t, tmp_path)
    assert frase in ferramentas.FRASES_TRABALHO
    assert t.pedidos == [("faz o relatório", tmp_path / "ws")]
    assert falas == ["Pronto, senhor."]
    [arquivo] = (tmp_path / "output").glob("*-faz-o-relatorio.md")
    assert arquivo.read_text(encoding="utf-8") == "Relatório."
    assert "recibo: ferramenta=trabalho resultado=ok" in next((tmp_path / "diario").glob("*.md")).read_text(encoding="utf-8")
    assert t.rodando is False


def test_ao_trabalho_dormindo_guarda_resultado(tmp_path):
    _, falas, sessao = _rodar_trabalho(TrabalhoFalso(), tmp_path, conversando=False)
    assert falas == [] and sessao.resultado_guardado == "Pronto, senhor."


def test_ao_trabalho_falhou(tmp_path):
    _, falas, _ = _rodar_trabalho(TrabalhoFalso(saida=FALHOU), tmp_path)
    assert falas == [ferramentas.FRASE_TRABALHO_FALHOU]
    assert not (tmp_path / "output").exists()


def test_trabalho_ocupado(tmp_path):
    t = TrabalhoFalso()
    t.rodando = True
    frase, _, _ = _rodar_trabalho(t, tmp_path)
    assert frase == ferramentas.FRASE_TRABALHO_OCUPADO and t.pedidos == []


class AjudanteFalso:
    def __init__(self, resultado="Camberra.", espera=0.0, erro=None):
        self.resultado, self.espera, self.erro = resultado, espera, erro
        self.cancelado = False

    async def executar(self, pedido):
        self.cancelado = False
        await asyncio.sleep(self.espera)
        if self.erro:
            raise self.erro
        return self.resultado


def chamada(**argumentos):
    """Params falso: guarda o que o handler devolveu ao LLM."""
    recebido, extras = [], []

    async def result_callback(resultado, **kwargs):
        recebido.append(resultado)
        extras.append(kwargs)

    return SimpleNamespace(arguments=argumentos, result_callback=result_callback, extras=extras), recebido


def acordada():
    s = Sessao()
    s.acordar(0)
    s.pronto(0)
    return s


def montar(sessao, ajudante):
    entregues = []

    async def entregar(texto):
        entregues.append(texto)

    return criar_ao_tarefa(sessao, ajudante, entregar), entregues


def test_coluna_so_propoe_fala_a_pergunta_e_nao_roda_o_llm():
    propostas, falados = [], []

    async def propor(acao, coluna, quadro):
        propostas.append((acao, coluna, quadro))
        return "Parar de cobrar? Confirma, senhor?"

    async def falar(texto):
        falados.append(texto)

    params, recebido = chamada(acao="ignorar", coluna=" Vagas recusadas ", quadro="Projeto 2026")
    asyncio.run(criar_ao_coluna(propor, falar)(params))
    assert propostas == [("ignorar", "Vagas recusadas", "Projeto 2026")]
    assert falados == ["Parar de cobrar? Confirma, senhor?"]
    assert recebido == [{"status": "falado ao usuário", "fala": "Parar de cobrar? Confirma, senhor?"}]
    assert params.extras[0]["properties"].run_llm is False


def test_coluna_sem_nome_ou_acao_invalida_nao_propoe():
    propostas, falados = [], []

    async def propor(*args):
        propostas.append(args)
        return "?"

    async def falar(texto):
        falados.append(texto)

    asyncio.run(criar_ao_coluna(propor, falar)(chamada(acao="ignorar", coluna="  ")[0]))
    asyncio.run(criar_ao_coluna(propor, falar)(chamada(acao="apagar", coluna="Vagas")[0]))
    assert propostas == [] and falados == ["Qual coluna, senhor?", "Não entendi o pedido, senhor."]


def test_esquema_tem_as_dez_ferramentas():
    ferramentas_ = {f.name: f for f in ESQUEMA.standard_tools}
    assert set(ferramentas_) == {"clima", "tarefa", "briefing", "coluna", "encerrar", "pc", "janela", "timer",
                                 "cancelar_timer", "vida"}
    assert ferramentas_["janela"].required == ["acao"]
    assert ferramentas_["janela"].properties["acao"]["enum"] == ["fechar", "fechar_aba", "minimizar"]
    assert ferramentas_["pc"].required == [] and ferramentas_["pc"].properties == {}  # o pedido sai da transcrição
    assert ferramentas_["timer"].required == ["minutos"]
    # rodada de 09/11: o cérebro mandou 60.0 e o "integer" a fez recusar a própria chamada 5 vezes; o handler já faz int()
    assert ferramentas_["timer"].properties["minutos"]["type"] == "number"
    assert ferramentas_["cancelar_timer"].required == []
    assert ferramentas_["coluna"].required == ["acao", "coluna"]
    assert ferramentas_["coluna"].properties["acao"]["enum"] == ["ignorar", "voltar"]
    assert ferramentas_["tarefa"].required == ["pedido"]
    assert ferramentas_["briefing"].required == ["tipo"]
    assert ferramentas_["briefing"].properties["tipo"]["enum"] == ["novidades", "hoje"]
    assert ferramentas_["vida"].required == ["consulta"]
    assert ferramentas_["vida"].properties["consulta"]["enum"] == ["agenda", "buscar", "cartao", "mudancas"]
    assert ferramentas_["vida"].properties["periodo"]["enum"] == ["vencidos", "hoje", "amanha", "semana"]


def test_janela_repassa_acao_e_alvo_e_fala_sem_rodar_o_llm():
    pedidos, falados = [], []

    async def ao_janela(acao, alvo):
        pedidos.append((acao, alvo))
        return ["Feito, senhor."]

    async def falar(texto):
        falados.append(texto)

    params, recebido = chamada(acao="fechar", alvo="chrome")
    asyncio.run(criar_ao_janela(ao_janela, falar)(params))
    assert pedidos == [("fechar", "chrome")] and falados == ["Feito, senhor."]
    assert recebido == [{"status": "falado ao usuário"}] and params.extras[0]["properties"].run_llm is False


def test_janela_com_acao_inventada_nao_chama_o_pc():
    pedidos, falados = [], []

    async def ao_janela(acao, alvo):
        pedidos.append(acao)
        return []

    async def falar(texto):
        falados.append(texto)

    params, recebido = chamada(acao="formatar", alvo="chrome")
    asyncio.run(criar_ao_janela(ao_janela, falar)(params))
    assert pedidos == [] and falados == ["Não entendi o pedido, senhor."] and recebido == [{"status": "erro"}]


def test_briefing_fala_e_nao_roda_o_llm():
    falados = []

    async def falar(tipo):
        falados.append(tipo)

    params, recebido = chamada(tipo="hoje")
    asyncio.run(criar_ao_briefing(falar)(params))
    assert falados == ["hoje"] and recebido == [{"status": "lido em voz"}]
    assert params.extras[0]["properties"].run_llm is False


def test_briefing_tipo_invalido_vira_novidades():
    falados = []

    async def falar(tipo):
        falados.append(tipo)

    params, _ = chamada(tipo="xyz")
    asyncio.run(criar_ao_briefing(falar)(params))
    assert falados == ["novidades"]


def test_tarefa_iniciada_e_entregue():
    async def cenario():
        ao_tarefa, entregues = montar(acordada(), AjudanteFalso())
        params, recebido = chamada(pedido="capital da Austrália")
        await ao_tarefa(params)
        await asyncio.sleep(0.05)
        return recebido, entregues

    recebido, entregues = asyncio.run(cenario())
    assert recebido == [{"status": "iniciada", "dizer": "Vou pesquisar, senhor."}]
    assert entregues == ["Camberra."]


def test_tarefa_ocupada():
    async def cenario():
        ao_tarefa, entregues = montar(acordada(), AjudanteFalso(espera=0.2))
        primeira, _ = chamada(pedido="a")
        segunda, recebido = chamada(pedido="b")
        await ao_tarefa(primeira)
        await ao_tarefa(segunda)
        await asyncio.sleep(0.3)
        return recebido, entregues

    recebido, entregues = asyncio.run(cenario())
    assert recebido == [{"status": "ocupado", "dizer": "Ainda estou na anterior, senhor."}]
    assert entregues == ["Camberra."]  # só a 1ª rodou


def test_tarefa_concluida_dormindo_fica_guardada():
    async def cenario():
        sessao = acordada()
        ao_tarefa, entregues = montar(sessao, AjudanteFalso(espera=0.1))
        params, _ = chamada(pedido="a")
        await ao_tarefa(params)
        sessao.dormir()
        await asyncio.sleep(0.2)
        return sessao, entregues

    sessao, entregues = asyncio.run(cenario())
    assert entregues == []
    assert sessao.pegar_resultado_guardado() == "Camberra."


def test_tarefa_cancelada_nao_e_entregue_nem_guardada():
    async def cenario():
        sessao, ajudante = acordada(), AjudanteFalso(espera=0.1)
        ao_tarefa, entregues = montar(sessao, ajudante)
        params, _ = chamada(pedido="a")
        await ao_tarefa(params)
        await asyncio.sleep(0.02)
        ajudante.cancelado = True  # o que Ajudante.cancelar() marca
        sessao.cancelar_tarefa()
        sessao.dormir()
        await asyncio.sleep(0.2)
        return sessao, entregues

    sessao, entregues = asyncio.run(cenario())
    assert entregues == [] and sessao.pegar_resultado_guardado() is None


def test_ajudante_que_explode_libera_a_sessao_e_avisa():
    async def cenario():
        sessao = acordada()
        ao_tarefa, entregues = montar(sessao, AjudanteFalso(erro=FileNotFoundError("hermes")))
        params, _ = chamada(pedido="a")
        await ao_tarefa(params)
        await asyncio.sleep(0.05)
        return sessao, entregues

    sessao, entregues = asyncio.run(cenario())
    assert entregues == [FALHOU]
    assert sessao.iniciar_tarefa(1)  # liberada


def test_clima_usa_src_clima(monkeypatch):
    monkeypatch.setattr(ferramentas, "temperatura_agora", lambda: "22 graus, céu limpo.")
    params, recebido = chamada()
    asyncio.run(criar_ao_clima()(params))
    assert recebido == [{"clima": "22 graus, céu limpo."}]


def test_clima_manda_o_painel_e_devolve_o_mesmo_ao_cerebro(monkeypatch):
    monkeypatch.setattr(ferramentas, "temperatura_agora", lambda: "Recife agora: 24°C, céu limpo.")
    paineis = []

    async def mostrar(p):
        paineis.append(p)

    params, recebido = chamada()
    asyncio.run(criar_ao_clima(mostrar)(params))
    assert recebido == [{"clima": "Recife agora: 24°C, céu limpo."}]
    assert [(p.id, p.valor) for p in paineis] == [("clima", "24")]


def montar_com_painel(sessao, ajudante, mostrar):
    entregues = []

    async def entregar(texto):
        entregues.append(texto)

    return criar_ao_tarefa(sessao, ajudante, entregar, mostrar=mostrar), entregues


def test_pesquisa_manda_o_painel_com_o_resultado():
    paineis = []

    async def mostrar(p):
        paineis.append(p)

    async def cenario():
        ao_tarefa, entregues = montar_com_painel(acordada(), AjudanteFalso("Camberra."), mostrar)
        params, _ = chamada(pedido="capital da Austrália")
        await ao_tarefa(params)
        await asyncio.sleep(0.05)
        return entregues

    assert asyncio.run(cenario()) == ["Camberra."]
    assert [(p.id, p.titulo, p.corpo) for p in paineis] == [("pesquisa", "capital da Austrália", "Camberra.")]


def test_pesquisa_que_falhou_ou_nao_achou_nao_abre_painel():
    from src.conversa import ajudante, buscador

    for texto in (buscador.FALHOU, ajudante.FALHOU, ajudante.ESTOUROU, ajudante.VAZIO):
        paineis = []

        async def mostrar(p):
            paineis.append(p)

        async def cenario():
            ao_tarefa, entregues = montar_com_painel(acordada(), AjudanteFalso(texto), mostrar)
            params, _ = chamada(pedido="a")
            await ao_tarefa(params)
            await asyncio.sleep(0.05)
            return entregues

        assert asyncio.run(cenario()) == [texto] and paineis == []  # a fala segue; a tela não


def test_pesquisa_que_levanta_nao_abre_painel():
    paineis = []

    async def mostrar(p):
        paineis.append(p)

    async def cenario():
        ao_tarefa, _ = montar_com_painel(acordada(), AjudanteFalso(erro=RuntimeError("x")), mostrar)
        params, _ = chamada(pedido="a")
        await ao_tarefa(params)
        await asyncio.sleep(0.05)

    asyncio.run(cenario())
    assert paineis == []


def test_clima_que_falhou_nao_abre_painel_e_o_cerebro_recebe_o_mesmo(monkeypatch):
    from src import clima

    for nome, valor in (("GROOV_CIDADE", "Recife"), ("GROOV_LAT", "-8.05"), ("GROOV_LON", "-34.9")):
        monkeypatch.setenv(nome, valor)
    falha = clima.temperatura_agora(buscar=lambda url: 1 / 0)
    monkeypatch.setattr(ferramentas, "temperatura_agora", lambda: falha)
    paineis = []

    async def mostrar(p):
        paineis.append(p)

    params, recebido = chamada()
    asyncio.run(criar_ao_clima(mostrar)(params))
    assert paineis == [] and recebido == [{"clima": falha}] and falha.startswith(clima.FALHA_DO_CLIMA)


def test_pesquisa_cancelada_nao_manda_painel():
    paineis = []

    async def mostrar(p):
        paineis.append(p)

    class Cancelavel(AjudanteFalso):
        async def executar(self, pedido):
            await asyncio.sleep(self.espera)
            self.cancelado = True
            return self.resultado

    async def cenario2():
        ao_tarefa, _ = montar_com_painel(acordada(), Cancelavel("x", espera=0.01), mostrar)
        params, _ = chamada(pedido="a")
        await ao_tarefa(params)
        await asyncio.sleep(0.1)

    asyncio.run(cenario2())
    assert paineis == []


def test_painel_que_levanta_nao_impede_a_entrega():
    async def mostrar(p):
        raise RuntimeError("canal fechado")

    async def cenario():
        ao_tarefa, entregues = montar_com_painel(acordada(), AjudanteFalso("Camberra."), mostrar)
        params, _ = chamada(pedido="a")
        await ao_tarefa(params)
        await asyncio.sleep(0.05)
        return entregues

    assert asyncio.run(cenario()) == ["Camberra."]


def test_tarefa_sem_pedido_nao_prende_a_sessao():
    async def cenario():
        sessao = acordada()
        ao_tarefa, entregues = montar(sessao, AjudanteFalso())
        params, recebido = chamada()  # o LLM esqueceu o argumento
        await ao_tarefa(params)
        return sessao, recebido

    sessao, recebido = asyncio.run(cenario())
    assert recebido[0]["status"] == "erro"
    assert sessao.iniciar_tarefa(1)  # continua livre


def test_entregar_espera_o_usuario_parar_de_falar_e_fala():
    async def cenario():
        sessao, falado, falando = acordada(), [], [True]

        async def falar(texto):
            falado.append(texto)

        entregar = criar_entregar(sessao, lambda: falando[0], falar, espera=0.01)
        tarefa = asyncio.create_task(entregar("Camberra."))
        await asyncio.sleep(0.05)
        antes = list(falado)
        falando[0] = False
        await tarefa
        return antes, falado

    antes, falado = asyncio.run(cenario())
    assert antes == [] and falado == ["Camberra."]


def test_entregar_guarda_o_resultado_se_a_sessao_dormiu_enquanto_esperava():
    """Tchau dito enquanto a pesquisa terminava: ela fica guardada para o próximo Hey JARVIS, não é falada."""
    async def cenario():
        sessao, falado, falando = acordada(), [], [True]

        async def falar(texto):
            falado.append(texto)

        entregar = criar_entregar(sessao, lambda: falando[0], falar, espera=0.01)
        tarefa = asyncio.create_task(entregar("Camberra."))
        await asyncio.sleep(0.03)
        sessao.dormir()
        falando[0] = False
        await tarefa
        return sessao, falado

    sessao, falado = asyncio.run(cenario())
    assert falado == [] and sessao.pegar_resultado_guardado() == "Camberra."


def test_entregar_guarda_o_resultado_com_a_sessao_ociosa():
    async def cenario():
        sessao, falado = acordada(), []
        sessao.ociar()

        async def falar(texto):
            falado.append(texto)

        await criar_entregar(sessao, lambda: False, falar)("Camberra.")
        return sessao, falado

    sessao, falado = asyncio.run(cenario())
    assert falado == [] and sessao.pegar_resultado_guardado() == "Camberra."


def test_tarefa_que_termina_com_a_sessao_ociosa_guarda_e_nao_fala():
    async def cenario():
        sessao = acordada()
        ao_tarefa, entregues = montar(sessao, AjudanteFalso(espera=0.05))
        await ao_tarefa(chamada(pedido="capital da Austrália")[0])
        sessao.ociar()
        await asyncio.sleep(0.15)
        return sessao, entregues

    sessao, entregues = asyncio.run(cenario())
    assert entregues == [] and sessao.pegar_resultado_guardado() == "Camberra."


def test_encerrar_dormir_e_desligar():
    chamadas = []

    async def dormir():
        chamadas.append("dormir")

    async def propor_desligar():
        chamadas.append("propor")

    ao_encerrar = ferramentas.criar_ao_encerrar(dormir, propor_desligar)
    for modo in ("dormir", "desligar", "xyz"):
        params, recebido = chamada(modo=modo)
        asyncio.run(ao_encerrar(params))
        assert params.extras[0]["properties"].run_llm is False
    assert chamadas == ["dormir", "propor"] and recebido == [{"status": "erro"}]


def test_esquema_tem_encerrar():
    encerrar = {f.name: f for f in ESQUEMA.standard_tools}["encerrar"]
    assert encerrar.required == ["modo"] and encerrar.properties["modo"]["enum"] == ["dormir", "desligar"]


# ---- pc, timer e cancelar_timer (Task 11 do controle do PC) ----

class LacoFalso:
    def __init__(self, desfecho=None, espera=0.0, erro=None):
        self.desfecho, self.espera, self.erro = desfecho or Desfecho("respondeu"), espera, erro
        self.pedidos = []

    def resumo(self, desfecho):
        return f"[pc: resumo {desfecho.tipo}]"

    async def executar(self, pedido):
        self.pedidos.append(pedido)
        await asyncio.sleep(self.espera)
        if self.erro:
            raise self.erro
        return self.desfecho


class TimersFalso:
    def __init__(self, cancelar="desligar", armar=True):
        self.armados, self.cancelamentos, self._cancelar, self._armar = [], [], cancelar, armar

    async def armar(self, pedido):
        self.armados.append(pedido)
        return self._armar

    async def cancelar(self, transcricao):
        self.cancelamentos.append(transcricao)
        return self._cancelar


def turno_com(texto):
    t = Turno()
    t.abrir(0)
    t.adicionar(texto, 0)
    t.fechar(1)
    return t


def montar_pc(laco=None, sessao=None, texto="abre o G1 e lê a reportagem"):
    sessao, turno, falados, anotados = sessao or acordada(), turno_com(texto), [], []

    async def falar(t):
        falados.append(t)

    async def anotar(linha):
        anotados.append(linha)

    laco = laco or LacoFalso()
    return criar_ao_pc(sessao, turno, laco, falar, anotar), sessao, turno, laco, falados, anotados


def test_pc_responde_na_hora_e_o_laco_leva_o_pedido_inteiro():
    async def cenario():
        ao_pc, sessao, turno, laco, falados, anotados = montar_pc(LacoFalso(espera=0.1))
        params, recebido = chamada()
        await ao_pc(params)
        reservada, restante = sessao.dono, turno.texto()  # consumir(): o próximo turno não junta a este
        await asyncio.sleep(0.02)
        return params, recebido, reservada, restante, laco, falados

    params, recebido, reservada, restante, laco, falados = asyncio.run(cenario())
    assert laco.pedidos == ["abre o G1 e lê a reportagem"] and reservada == "laco" and restante == ""
    assert falados == [FRASE_UM_MOMENTO] and recebido == [{"status": "iniciado"}]
    assert params.extras[0]["properties"].run_llm is False


def test_pc_ocupado_com_hermes():
    async def cenario():
        ao_pc, sessao, turno, laco, falados, anotados = montar_pc()
        sessao.iniciar_tarefa(0)  # o Hermes está pesquisando
        params, recebido = chamada()
        await ao_pc(params)
        await asyncio.sleep(0.02)
        return turno, laco, falados, recebido, sessao

    turno, laco, falados, recebido, sessao = asyncio.run(cenario())
    assert laco.pedidos == [] and falados == ["Ainda estou na anterior, senhor."]
    assert turno.texto() == "abre o G1 e lê a reportagem" and sessao.dono == "hermes"
    assert recebido == [{"status": "ocupado"}]


def test_tarefa_ocupada_com_o_laco_do_pc():
    async def cenario():
        ao_pc, sessao, *_ = montar_pc(LacoFalso(espera=0.2))
        await ao_pc(chamada()[0])
        ao_tarefa, entregues = montar(sessao, AjudanteFalso())
        params, recebido = chamada(pedido="clima")
        await ao_tarefa(params)
        return recebido

    assert asyncio.run(cenario()) == [{"status": "ocupado", "dizer": "Ainda estou na anterior, senhor."}]


@pytest.mark.parametrize("tipo", ["respondeu", "tocou", "parou", "teto", "desistiu", "cancelado"])
def test_contexto_recebe_o_resumo_do_laco(tipo):
    async def cenario():
        ao_pc, sessao, turno, laco, falados, anotados = montar_pc(LacoFalso(Desfecho(tipo, "texto lido da página")))
        await ao_pc(chamada()[0])
        await asyncio.sleep(0.05)
        return anotados

    assert asyncio.run(cenario()) == [f"[pc: resumo {tipo}]"]  # só o que o laço resume, nunca a fala crua


def test_anota_mesmo_dormindo():
    async def cenario():
        ao_pc, sessao, turno, laco, falados, anotados = montar_pc(LacoFalso(Desfecho("tocou"), espera=0.05))
        await ao_pc(chamada()[0])
        sessao.dormir()  # depois do play o laço manda dormir: o pedido mais comum não pode sumir da conversa
        await asyncio.sleep(0.1)
        return anotados, falados

    anotados, falados = asyncio.run(cenario())
    assert anotados == ["[pc: resumo tocou]"] and falados == [FRASE_UM_MOMENTO]  # anotar não fala


def test_laco_que_explode_solta_a_vaga_e_marca_parado():
    async def cenario():
        ao_pc, sessao, turno, laco, falados, anotados = montar_pc(LacoFalso(erro=RuntimeError("laço já em execução")))
        await ao_pc(chamada()[0])
        await asyncio.sleep(0.05)
        return sessao, anotados

    sessao, anotados = asyncio.run(cenario())
    assert anotados == ["[pc: parado]"] and sessao.iniciar_tarefa(1)


def test_pc_sem_pedido_nao_prende_a_vaga():
    async def cenario():
        ao_pc, sessao, turno, laco, falados, anotados = montar_pc(texto="  ")
        params, recebido = chamada()
        await ao_pc(params)
        await asyncio.sleep(0.02)
        return sessao, laco, falados

    sessao, laco, falados = asyncio.run(cenario())
    assert laco.pedidos == [] and falados == ["Não entendi o pedido, senhor."] and sessao.iniciar_tarefa(1)


def montar_timer(texto, sessao=None, timers=None):
    sessao, turno, falados = sessao or acordada(), turno_com(texto), []

    async def falar(t):
        falados.append(t)

    timers = timers or TimersFalso()
    return criar_ao_timer(sessao, turno, timers, falar), sessao, timers, falados


def test_timer_de_10_minutos_nao_abre_laco():
    async def cenario():
        ao_timer, sessao, timers, falados = montar_timer("bota um timer de 10 minutos")
        params, recebido = chamada(minutos=10)
        await ao_timer(params)
        return sessao, timers, falados, recebido, params

    sessao, timers, falados, recebido, params = asyncio.run(cenario())
    assert timers.armados == [PedidoTimer(10, False, False)] and sessao.dono is None
    assert falados == ["Timer de 10 minutos armado, senhor."]
    assert params.extras[0]["properties"].run_llm is False and recebido[0]["status"] == "armado"


def test_timer_de_desligar_arma_o_de_desligar():
    async def cenario():
        ao_timer, _, timers, falados = montar_timer("liga um timer de desligar de uma hora")
        await ao_timer(chamada(minutos=60)[0])
        return timers, falados

    timers, falados = asyncio.run(cenario())
    assert timers.armados == [PedidoTimer(60, True, False)]
    assert falados == ["Timer de desligar de 60 minutos armado, senhor."]


@pytest.mark.parametrize("texto", ["bota o Sora no Kanata na Netflix e um timer de uma hora", "abre o G1 e um timer de 5 minutos",
                                   "toca Kaluê no Spotify e um timer de 10 minutos", "entra no GitHub, timer de 5 minutos"])
def test_timer_com_site_ou_app_citado_recusa_em_silencio(texto):
    async def cenario():
        ao_timer, _, timers, falados = montar_timer(texto)
        params, recebido = chamada(minutos=60)
        await ao_timer(params)
        return timers, falados, recebido

    timers, falados, recebido = asyncio.run(cenario())
    assert timers.armados == [] and falados == [] and recebido[0]["status"] != "armado"


def test_pc_e_timer_no_mesmo_lote_nao_arma_antes():
    """Se `pc` rodou primeiro ele já consumiu o turno: o timer não pode achar a transcrição "limpa" e armar antes do play."""
    async def cenario():
        ao_pc, sessao, turno, laco, falados, anotados = montar_pc(
            LacoFalso(espera=0.1), texto="bota Sora no Kanata aí pra eu assistir na Netflix e depois um timer de uma hora")
        timers, faladas_timer = TimersFalso(), []

        async def falar(t):
            faladas_timer.append(t)

        ao_timer = criar_ao_timer(sessao, turno, timers, falar)
        await ao_pc(chamada()[0])
        await ao_timer(chamada(minutos=60)[0])  # o cérebro chamou os dois no mesmo lote; o turno já foi consumido
        return timers, faladas_timer

    timers, faladas_timer = asyncio.run(cenario())
    assert timers.armados == [] and faladas_timer == []


def test_timer_na_conversa_minutos_diferentes_pergunta():
    async def cenario():
        ao_timer, _, timers, falados = montar_timer("bota um timer de 10 minutos")
        await ao_timer(chamada(minutos=20)[0])  # o cérebro entendeu outro número
        return timers, falados

    timers, falados = asyncio.run(cenario())
    assert timers.armados == [] and len(falados) == 1 and "tempo" in falados[0]


@pytest.mark.parametrize("texto", ["bota um timer", "bota um timer de desligar o forno e do pc",
                                   "um timer de 5 minutos, não, de 10 minutos", "isso é só uma conversa",
                                   "não bota timer de 10 minutos"])
def test_timer_na_conversa_sem_numero_pergunta(texto):
    async def cenario():
        ao_timer, _, timers, falados = montar_timer(texto)
        await ao_timer(chamada(minutos=10)[0])
        return timers, falados

    timers, falados = asyncio.run(cenario())
    assert timers.armados == [] and len(falados) == 1


def test_timer_que_o_windows_recusou_avisa():
    async def cenario():
        ao_timer, _, timers, falados = montar_timer("liga um timer de desligar de 5 minutos", timers=TimersFalso(armar=False))
        await ao_timer(chamada(minutos=5)[0])
        return falados

    assert asyncio.run(cenario()) == ["Não consegui armar o timer, senhor."]


def test_cancelar_timer_usa_a_transcricao_e_fala_o_resultado():
    async def cenario():
        falados, timers = [], TimersFalso(cancelar="simples")

        async def falar(t):
            falados.append(t)

        params, recebido = chamada()
        await criar_ao_cancelar_timer(turno_com("tira o timer do forno"), timers, falar)(params)
        return timers, falados, params, recebido

    timers, falados, params, recebido = asyncio.run(cenario())
    assert timers.cancelamentos == ["tira o timer do forno"] and falados == ["Timer cancelado, senhor."]
    assert params.extras[0]["properties"].run_llm is False and recebido[0]["status"] == "falado ao usuário"


def test_cancelar_timer_que_falhou_avisa():
    async def cenario():
        falados = []

        async def falar(t):
            falados.append(t)

        await criar_ao_cancelar_timer(turno_com("cancela o timer"), TimersFalso(cancelar="falhou"), falar)(chamada()[0])
        return falados

    falados = asyncio.run(cenario())
    assert falados == ["Não consegui cancelar o timer, senhor."] and "cancelado" not in falados[0]


def test_cancelar_timer_com_dois_armados_pergunta_qual():
    async def cenario():
        falados = []

        async def falar(t):
            falados.append(t)

        await criar_ao_cancelar_timer(turno_com("cancela o timer"), TimersFalso(cancelar="qual"), falar)(chamada()[0])
        return falados

    assert "Qual" in asyncio.run(cenario())[0]


# ---- pedido com site ou app vai ao pc, não ao Hermes ----

def tarefa_com_pc(texto):
    entregues, ao_pc_recebido, hermes = [], [], []

    class Ajudante(AjudanteFalso):
        async def executar(self, pedido):
            hermes.append(pedido)
            return await super().executar(pedido)

    async def entregar(t):
        entregues.append(t)

    async def ao_pc(params):
        ao_pc_recebido.append(params)

    ao_tarefa = criar_ao_tarefa(acordada(), Ajudante(), entregar, turno=turno_com(texto), ao_pc=ao_pc)
    return ao_tarefa, ao_pc_recebido, hermes


def test_tarefa_com_site_vai_ao_pc():
    async def cenario():
        ao_tarefa, ao_pc_recebido, hermes = tarefa_com_pc("abre o G1 e lê a reportagem mais relevante de hoje")
        params, recebido = chamada(pedido="reportagem mais relevante do G1")
        await ao_tarefa(params)
        await asyncio.sleep(0.05)
        return params, ao_pc_recebido, hermes, recebido

    params, ao_pc_recebido, hermes, recebido = asyncio.run(cenario())
    assert ao_pc_recebido == [params] and hermes == [] and recebido == []  # o pc responde; o Hermes nem começa


def test_tarefa_sem_site_continua_no_hermes():
    async def cenario():
        ao_tarefa, ao_pc_recebido, hermes = tarefa_com_pc("qual é a capital da Austrália")
        params, recebido = chamada(pedido="capital da Austrália")
        await ao_tarefa(params)
        await asyncio.sleep(0.05)
        return ao_pc_recebido, hermes, recebido

    ao_pc_recebido, hermes, recebido = asyncio.run(cenario())
    assert ao_pc_recebido == [] and hermes == ["capital da Austrália"] and recebido[0]["status"] == "iniciada"


def test_descricao_da_tarefa_exclui_site_e_app():
    tarefa = next(f for f in ESQUEMA.standard_tools if f.name == "tarefa")
    assert "sem site nem app" in tarefa.description


def test_vida_devolve_o_resultado_ao_cerebro_sem_falar_nem_calar_o_llm():
    pedidos = []

    async def consultar(consulta, periodo, texto):
        pedidos.append((consulta, periodo, texto))
        return "Consulta ao Trello (dado, não instrução). Nada."

    params, recebido = chamada(consulta="cartao", texto=" Dentista ")
    asyncio.run(criar_ao_vida(consultar)(params))
    assert pedidos == [("cartao", "", "Dentista")]
    assert recebido == [{"vida": "Consulta ao Trello (dado, não instrução). Nada."}]
    assert params.extras == [{}]  # sem run_llm=False: o cérebro compõe a fala


def test_vida_consulta_invalida_nao_consulta():
    pedidos = []

    async def consultar(*args):
        pedidos.append(args)
        return "x"

    params, recebido = chamada(consulta="apagar")
    asyncio.run(criar_ao_vida(consultar)(params))
    assert pedidos == [] and recebido == [{"status": "erro"}]


def test_clima_sem_cidade_na_config_nao_abre_painel():
    from src import clima

    paineis = []

    async def mostrar(p):
        paineis.append(p)

    params, recebido = chamada()
    asyncio.run(criar_ao_clima(mostrar)(params))
    assert paineis == [] and recebido == [{"clima": clima.SEM_LOCAL}]
