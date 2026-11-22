"""Ferramentas que o cérebro pode chamar: clima (src/clima.py), tarefa (pesquisa em segundo plano),
briefing (novidades e o dia, lidos em voz sem passar pelo contexto do cérebro), coluna (não cobrar uma coluna do
Trello; só guarda depois do "sim"), encerrar (dormir, ou desligar depois do "sim"), pc (o laço do controle do PC),
timer, cancelar_timer e vida (consulta livre ao Trello; o resultado volta ao cérebro). `pc` não tem argumentos: o pedido é o turno do usuário, nunca o que o cérebro escreve."""
import asyncio
import logging
import random
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.frames.frames import FunctionCallResultProperties

from src.clima import FALHA_DO_CLIMA, SEM_LOCAL, temperatura_agora
from src.conversa import buscador, vault
from src.conversa.ajudante import CANCELADA, ESTOUROU, FALHOU, VAZIO, Ajudante
from src.conversa.comandos import FRASE_TIMERS
from src.conversa.laco import FRASE_UM_MOMENTO
from src.conversa.paineis import Painel, de_clima, de_pesquisa
from src.conversa.regras_pc import ACOES_JANELA, cita_destino, ler_timer
from src.conversa.sessao import Estado, Sessao
from src.conversa.timers import Timers
from src.conversa.trabalho import separar
from src.conversa.turno import Turno
from src.vida.consulta import CONSULTAS, PERIODOS

log = logging.getLogger("groov.ferramentas")

FRASE_OCUPADO = "Ainda estou na anterior, senhor."
FRASE_SEM_PEDIDO = "Não entendi o pedido, senhor."
# decisão provisória (a revisar): uma só frase para todo timer duvidoso (sem número, ambíguo, outro número que o da
# cérebro, ou sem timer na transcrição). Não há resposta pendente: o usuário repete o pedido inteiro.
FRASE_TIMER_DUVIDA = "Não tenho certeza do tempo, senhor. Diga o timer inteiro de novo."
FRASE_TIMER_NAO_ARMEI = "Não consegui armar o timer, senhor."
LINHA_PC_PARADO = "[pc: parado]"  # quando o laço caiu e não há resumo; o resto vem de Laco.resumo
_SEM_NOVA_INFERENCIA = FunctionCallResultProperties(run_llm=False)

ESQUEMA = ToolsSchema(standard_tools=[
    FunctionSchema(
        name="clima",
        description="Temperatura e condição agora na cidade do usuário.",
        properties={},
        required=[],
    ),
    FunctionSchema(
        name="tarefa",
        description=("Pesquisa na internet (busca do Google). "
                     "Use só para informação atual ou pesquisa sem site nem app no pedido: "
                     "se o pedido citar um site ou app (G1, Netflix, Spotify...), use pc."),
        properties={"pedido": {"type": "string", "description": "O pedido do usuário, completo e autoexplicativo."}},
        required=["pedido"],
    ),
    FunctionSchema(
        name="briefing",
        description=("Lê em voz as novidades (o que mudou nos projetos e rotinas) ou o dia (prazos e compromissos). "
                     "Use quando o usuário pedir novidades, o que tem hoje ou o resumo do dia."),
        properties={"tipo": {"type": "string", "enum": ["novidades", "hoje"]}},
        required=["tipo"],
    ),
    FunctionSchema(
        name="vida",
        description=("Consulta livre ao Trello do usuário (prazos, cartões, mudanças recentes). Use para perguntas sobre "
                     "a vida dele que não são só 'novidades' nem 'o que tenho hoje'. agenda: prazos do período; "
                     "buscar: cartões pelo nome; cartao: detalhes de um cartão; mudancas: o que mudou. "
                     "O resultado volta para você: responda você mesmo, curto."),
        properties={
            "consulta": {"type": "string", "enum": list(CONSULTAS)},
            "periodo": {"type": "string", "enum": list(PERIODOS), "description": "Só para agenda; vazio = hoje."},
            "texto": {"type": "string", "description": "Nome ou parte do nome do cartão (buscar e cartao)."},
        },
        required=["consulta"],
    ),
    FunctionSchema(
        name="coluna",
        description=("Parar de cobrar prazos e atrasos de uma coluna do Trello (ignorar) ou voltar a cobrar (voltar). "
                     "Não guarda nada: pergunta ao usuário e só guarda depois do sim dele."),
        properties={
            "acao": {"type": "string", "enum": ["ignorar", "voltar"]},
            "coluna": {"type": "string", "description": "Nome da coluna como o usuário falou."},
            "quadro": {"type": "string", "description": "Nome do quadro, se o usuário falou."},
        },
        required=["acao", "coluna"],
    ),
    FunctionSchema(
        name="encerrar",
        description=("dormir: o usuário vai voltar depois; desligar: não vai mais usar hoje (libera o PC). "
                     "Use só quando o pedido for para o próprio GROOV."),
        properties={"modo": {"type": "string", "enum": ["dormir", "desligar"]}},
        required=["modo"],
    ),
    FunctionSchema(
        name="pc",
        description=("Controla o PC do usuário: abre site no Chrome ou qualquer app (Spotify, Bloco de Notas...), lê uma página, clica, busca, toca "
                     "série, filme ou música. Sem argumentos: o pedido inteiro é lido da fala do usuário. "
                     "Use para qualquer pedido que mexa no PC e não diga mais nada: ela mesma fala."),
        properties={},
        required=[],
    ),
    FunctionSchema(
        name="janela",
        description=("Fecha ou minimiza uma janela de qualquer app do PC (Chrome, Spotify...), ou fecha a aba ativa do Chrome. "
                     "Use quando o usuário pedir para fechar ou minimizar algo; não diga mais nada: ela mesma fala."),
        properties={
            "acao": {"type": "string", "enum": list(ACOES_JANELA)},
            "alvo": {"type": "string", "description": "nome do app (chrome, spotify, notepad...), se o usuário falou; vazio = a janela da frente."},
        },
        required=["acao"],
    ),
    FunctionSchema(
        name="timer",
        description=("Timer só de tempo, sem site nem app no pedido: simples (avisa em voz) ou de desligar o PC. "
                     "Se o pedido abre site ou app, o PC arma o timer sozinho: não chame."),
        properties={"minutos": {"type": "number", "description": "Minutos que o usuário falou."}},
        required=["minutos"],
    ),
    FunctionSchema(
        name="cancelar_timer",
        description="Cancela o timer armado (simples ou de desligar o PC), quando o usuário pedir.",
        properties={},
        required=[],
    ),
])

# o que o Ajudante e o Buscador devolvem quando não deu resultado: a fala segue, a tela não abre painel
SEM_RESULTADO = frozenset({FALHOU, buscador.FALHOU, ESTOUROU, VAZIO, CANCELADA})

_tarefas: set[asyncio.Task] = set()  # o loop só guarda referência fraca de tasks


async def _mandar_painel(mostrar, painel: Painel) -> None:
    """O painel é enfeite: se não saiu, a ferramenta segue (só o tipo do erro vai ao log)."""
    if mostrar is None:
        return
    try:
        await mostrar(painel)
    except Exception as erro:
        log.warning("painel não saiu: %s", type(erro).__name__)


def criar_ao_clima(mostrar=None):
    async def ao_clima(params) -> None:
        texto = await asyncio.to_thread(temperatura_agora)
        if not texto.startswith(FALHA_DO_CLIMA) and texto != SEM_LOCAL:  # a falha vai ao cérebro, mas não é um resultado para a tela
            await _mandar_painel(mostrar, de_clima(texto))
        await params.result_callback({"clima": texto})

    return ao_clima


def criar_entregar(sessao: Sessao, usuario_falando: Callable[[], bool], falar: Callable[[str], Awaitable[None]],
                   relogio=time.monotonic, espera: float = 0.2):
    """Fala o resultado de uma tarefa quando o usuário para de falar; se a sessão deixou de conversar nesse meio-tempo
    (tchau, ocioso), guarda o resultado para o próximo Hey JARVIS."""
    async def entregar(texto: str) -> None:
        while usuario_falando():
            await asyncio.sleep(espera)
        if sessao.estado is not Estado.CONVERSANDO:
            sessao.concluir_tarefa(texto)
            return
        sessao.atividade(relogio())
        await falar(texto)

    return entregar


def criar_ao_tarefa(sessao: Sessao, ajudante: Ajudante, entregar: Callable[[str], Awaitable[None]],
                    relogio=time.monotonic, turno: Turno | None = None, ao_pc=None, mostrar=None):
    """Com `turno` e `ao_pc`, pedido que cita site ou app vai ao pc (que consome o turno) e a pesquisa nem começa."""
    async def correr(pedido: str) -> None:
        try:
            resultado = await ajudante.executar(pedido)
        except Exception:  # sem isto a sessão ficaria presa na tarefa
            resultado = FALHOU
        if ajudante.cancelado:  # "desligar" ou teto: a sessão já cuidou do aviso
            return
        if resultado not in SEM_RESULTADO:
            await _mandar_painel(mostrar, de_pesquisa(pedido, resultado))  # na tela em qualquer estado da sessão
        sessao.concluir_tarefa(resultado)
        if sessao.estado is Estado.CONVERSANDO:
            await entregar(resultado)

    async def ao_tarefa(params) -> None:
        if ao_pc and turno and cita_destino(turno.texto()):  # o cérebro errou de ferramenta: a pesquisa não tem navegador
            await ao_pc(params)
            return
        pedido = str(params.arguments.get("pedido") or "").strip()
        if not pedido:  # antes de iniciar_tarefa: senão a sessão ficaria presa até o teto de 180 s
            await params.result_callback({"status": "erro", "dizer": "Não entendi o pedido, senhor."})
            return
        if not sessao.iniciar_tarefa(relogio()):
            await params.result_callback({"status": "ocupado", "dizer": "Ainda estou na anterior, senhor."})
            return
        t = asyncio.create_task(correr(pedido))
        _tarefas.add(t)
        t.add_done_callback(_tarefas.discard)
        await params.result_callback({"status": "iniciada", "dizer": "Vou pesquisar, senhor."})

    return ao_tarefa


FRASES_TRABALHO = ("Vou trabalhar nisso, senhor.", "Deixa comigo, senhor.", "Já começo, senhor. Aviso quando terminar.",
                   "Certo, senhor. Vou cuidar disso.", "Pode deixar, senhor. Estou nisso.")
FRASE_TRABALHO_OCUPADO = "Ainda estou num trabalho, senhor. Peça de novo quando eu terminar."
FRASE_TRABALHO_FALHOU = "O trabalho falhou, senhor."


def escolher_frase(anterior: str | None, sorteio=random.choice) -> str:
    return sorteio([f for f in FRASES_TRABALHO if f != anterior])


def criar_ao_trabalho(sessao: Sessao, trabalho, entregar: Callable[[str], Awaitable[None]], raiz_vault: Path,
                      relogio=time.monotonic):
    """Nível 3: dispara o Claude Code em segundo plano e devolve a frase de aviso. Fora da vaga de tarefa da sessão (o
    trabalho dura até 15 min e não segura o GROOV acordado); um trabalho por vez. O resultado vai ao vault e o resumo é
    falado, ou guardado para quando ele acordar."""
    ultima: dict[str, str | None] = {"frase": None}

    async def correr(pedido: str, pasta: Path) -> None:
        inicio = relogio()
        try:
            saida = await trabalho.executar(pedido, pasta)
            ok = saida not in (ESTOUROU, FALHOU, CANCELADA)
            if ok:
                corpo, resumo = separar(saida)
                await asyncio.to_thread(vault.salvar_output, raiz_vault, pedido, corpo or saida)
            else:
                resumo = FRASE_TRABALHO_FALHOU if saida == FALHOU else saida
            await asyncio.to_thread(vault.registrar_recibo, raiz_vault, "trabalho", ok, relogio() - inicio)
        except Exception as erro:  # nunca derruba a conversa
            log.warning("trabalho caiu: %s", type(erro).__name__)
            resumo = FRASE_TRABALHO_FALHOU
        finally:
            trabalho.rodando = False
        if sessao.estado is Estado.CONVERSANDO:
            await entregar(resumo)
        else:
            sessao.resultado_guardado = resumo

    async def ao_trabalho(pedido: str, pasta: Path) -> str:
        if trabalho.rodando:
            return FRASE_TRABALHO_OCUPADO
        trabalho.rodando = True
        t = asyncio.create_task(correr(pedido, pasta))
        _tarefas.add(t)
        t.add_done_callback(_tarefas.discard)
        ultima["frase"] = escolher_frase(ultima["frase"])
        return ultima["frase"]

    return ao_trabalho


def criar_ao_briefing(falar_briefing: Callable[[str], Awaitable[None]]):
    async def ao_briefing(params) -> None:
        tipo = str(params.arguments.get("tipo") or "")
        if tipo not in ("novidades", "hoje"):
            tipo = "novidades"
        await falar_briefing(tipo)
        # o texto lido não volta ao LLM (iria ao cérebro em toda inferência seguinte): resultado neutro e sem nova inferência
        await params.result_callback({"status": "lido em voz"}, properties=FunctionCallResultProperties(run_llm=False))

    return ao_briefing


def criar_ao_vida(consultar: Callable[[str, str, str], Awaitable[str]]):
    """O texto da consulta (curto, marcado como dado) volta ao cérebro, que compõe a fala; os títulos dos cartões
    consultados vão ao Google (o usuário foi avisado)."""
    async def ao_vida(params) -> None:
        consulta = str(params.arguments.get("consulta") or "")
        if consulta not in CONSULTAS:
            await params.result_callback({"status": "erro"})
            return
        texto = await consultar(consulta, str(params.arguments.get("periodo") or "").strip(),
                                str(params.arguments.get("texto") or "").strip())
        await params.result_callback({"vida": texto})

    return ao_vida


def criar_ao_coluna(propor: Callable[[str, str, str], Awaitable[str]], falar: Callable[[str], Awaitable[None]]):
    """O cérebro só passa o nome falado; propor() acha a coluna e deixa o pedido pendente até o "sim" (filtro local)."""
    async def ao_coluna(params) -> None:
        acao = str(params.arguments.get("acao") or "")
        coluna = str(params.arguments.get("coluna") or "").strip()
        quadro = str(params.arguments.get("quadro") or "").strip()
        if acao not in ("ignorar", "voltar"):
            fala = "Não entendi o pedido, senhor."
        elif not coluna:
            fala = "Qual coluna, senhor?"
        else:
            fala = await propor(acao, coluna, quadro)
        await falar(fala)
        # a fala volta ao cérebro (só nomes de quadro e lista): se ela perguntou "qual delas", o seguimento faz sentido
        await params.result_callback({"status": "falado ao usuário", "fala": fala},
                                     properties=FunctionCallResultProperties(run_llm=False))

    return ao_coluna


def criar_ao_encerrar(dormir: Callable[[], Awaitable[None]], propor_desligar: Callable[[], Awaitable[None]]):
    """O cérebro entendeu "dar um tempo" ou "encerrar": dormir vale na hora; desligar só pergunta (o "sim" é local)."""
    async def ao_encerrar(params) -> None:
        modo = str(params.arguments.get("modo") or "")
        if modo == "dormir":
            await dormir()
        elif modo == "desligar":
            await propor_desligar()
        resultado = {"status": "feito" if modo in ("dormir", "desligar") else "erro"}
        await params.result_callback(resultado, properties=FunctionCallResultProperties(run_llm=False))

    return ao_encerrar


def criar_ao_pc(sessao: Sessao, turno: Turno, laco, falar: Callable[[str], Awaitable[None]],
                anotar: Callable[[str], Awaitable[None]], relogio=time.monotonic):
    """Reserva a vaga e fala "Um momento"; o laço corre fora do contexto da conversa e, ao fim, só o resumo dele
    (`Laco.resumo`) entra nele, também se a sessão já dormiu (o play manda dormir). `anotar` acrescenta ao contexto sem
    rodar o LLM nem falar."""
    async def correr(pedido: str) -> None:
        try:
            linha = laco.resumo(await laco.executar(pedido))
        except Exception as erro:  # o laço trata os seus erros; isto só pega o que escapou (ex.: já em execução)
            log.warning("pc: laço caiu: %s", type(erro).__name__)
            linha = LINHA_PC_PARADO
            if sessao.dono == "laco":
                sessao.cancelar_tarefa()
        await anotar(linha)

    async def ao_pc(params) -> None:
        if not sessao.iniciar_tarefa(relogio(), "laco"):
            await falar(FRASE_OCUPADO)
            await params.result_callback({"status": "ocupado"}, properties=_SEM_NOVA_INFERENCIA)
            return
        pedido = turno.consumir().strip()  # o objetivo do laço é a transcrição crua do turno, não texto do cérebro
        try:
            await falar(FRASE_UM_MOMENTO if pedido else FRASE_SEM_PEDIDO)
        except BaseException:
            sessao.cancelar_tarefa()  # sem isto a vaga ficaria presa até o teto
            raise
        if not pedido:
            sessao.cancelar_tarefa()
            await params.result_callback({"status": "erro"}, properties=_SEM_NOVA_INFERENCIA)
            return
        t = asyncio.create_task(correr(pedido))
        _tarefas.add(t)
        t.add_done_callback(_tarefas.discard)
        await params.result_callback({"status": "iniciado"}, properties=_SEM_NOVA_INFERENCIA)

    return ao_pc


def criar_ao_janela(ao_janela: Callable[[str, str], Awaitable[list[str]]], falar: Callable[[str], Awaitable[None]]):
    """Fechar/minimizar que o atalho local não pegou. Ação e alvo vêm do cérebro, mas quem decide é regras_pc (só app da
    lista, nunca o GROOV, abas perguntam); a ferramenta só repassa e fala."""
    async def ao_janela_(params) -> None:
        acao = str(params.arguments.get("acao") or "")
        if acao not in ACOES_JANELA:
            await falar(FRASE_SEM_PEDIDO)
            await params.result_callback({"status": "erro"}, properties=_SEM_NOVA_INFERENCIA)
            return
        for fala in await ao_janela(acao, str(params.arguments.get("alvo") or "")):
            await falar(fala)
        await params.result_callback({"status": "falado ao usuário"}, properties=_SEM_NOVA_INFERENCIA)

    return ao_janela_


def criar_ao_timer(sessao: Sessao, turno: Turno, timers: Timers, falar: Callable[[str], Awaitable[None]]):
    """Timer sem site nem app. Minutos e "desligar" saem da transcrição (ler_timer), nunca do cérebro: se ela mandou outro
    número, ou a transcrição não tem número claro, pergunta e não arma. Com o laço rodando (o `pc` do mesmo lote já
    consumiu o turno) ou site/app citado, recusa em silêncio: o laço arma no fim, depois do play."""
    async def ao_timer(params) -> None:
        texto = turno.texto()
        if sessao.dono == "laco" or cita_destino(texto):
            await params.result_callback({"status": "o PC arma o timer no fim"}, properties=_SEM_NOVA_INFERENCIA)
            return
        try:
            do_cerebro = int(params.arguments.get("minutos"))
        except (TypeError, ValueError, OverflowError):  # "number" no esquema: infinito também chega
            do_cerebro = None
        pedido = ler_timer(texto)
        if pedido is None or pedido.ambiguo or not pedido.minutos or pedido.minutos != do_cerebro:
            fala = FRASE_TIMER_DUVIDA
        else:
            try:
                armou = await timers.armar(pedido)
            except Exception as erro:
                log.warning("timer falhou: %s", type(erro).__name__)
                armou = False
            fala = (f"Timer {'de desligar ' if pedido.desligar else ''}de {pedido.minutos} minutos armado, senhor."
                    if armou else FRASE_TIMER_NAO_ARMEI)
        await falar(fala)
        await params.result_callback({"status": "armado" if fala.startswith("Timer") else "não armado"},
                                     properties=_SEM_NOVA_INFERENCIA)

    return ao_timer


def criar_ao_cancelar_timer(turno: Turno, timers: Timers, falar: Callable[[str], Awaitable[None]]):
    """O atalho local do filtro pega as frases comuns; esta ferramenta é para o resto. `falhou` nunca vira "cancelado"."""
    async def ao_cancelar_timer(params) -> None:
        try:
            resultado = await timers.cancelar(turno.texto())
        except Exception as erro:
            log.warning("cancelar timer falhou: %s", type(erro).__name__)
            resultado = "falhou"
        fala = FRASE_TIMERS[resultado]
        await falar(fala)
        await params.result_callback({"status": "falado ao usuário", "fala": fala}, properties=_SEM_NOVA_INFERENCIA)

    return ao_cancelar_timer
