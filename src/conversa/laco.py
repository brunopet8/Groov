"""O laço do controle do PC: ler, pedir um passo ao modelo, validar no PC, agir, repetir, falar o resultado.
Sem pipecat (testa nos dois venvs). Tudo o que `pensar` devolve é não confiável: cada passo passa por regras_pc
antes de chegar ao backend, e o pedido é sempre a transcrição do usuário (+ fragmentos tardios de `juntar`), nunca texto lido.
Log: só contagens, tipos e nomes de ação fixos; nunca texto de página, transcrição, URL nem fala."""
import asyncio
import hashlib
import logging
import re
import time
import traceback
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from urllib.parse import quote, urlsplit

from src.conversa import regras_pc as r
from src.conversa.cerebro_pc import cortar_pagina
from src.conversa import gravacao
from src.conversa.comandos import pode_enviar, resposta_do_que_tocou, sim_ou_nao
from src.conversa.pc import Backend, Midia, Olhar, janela_da_aba
from src.conversa.regras_pc import SITES, Site
from src.conversa.sessao import Sessao
from src.conversa.visao import Alvo
from src.conversa.timers import FRASE_DEU_O_TEMPO, Timers  # noqa: F401  (FRASE_DEU_O_TEMPO: reexportado, mora em timers)
from src.conversa.turno import JUNTAR_TURNO_S  # noqa: F401  (reexportado, mora em turno)
from src.conversa.log_turno import RESULTADO_ACEITO, RESULTADO_INVALIDO, RESULTADO_RECUSADO, linha_passo

log = logging.getLogger("groov.laco")

# Tetos do plano
PASSOS_MAX = 15
ACAO_MAX_S = 300  # passos de ~10 s do Claude do plano: 180 s não cabia
LER_ESTAVEL_S = 10
RESPOSTA_S = 30
PERGUNTA_TETO_S = 90
OPCOES_MAX = 4  # botões de resposta na tela, quando a pergunta do laço é de escolha (o mínimo é 2)
OPCAO_MAX_CARACTERES = 40
MARGEM_ECO_S = 1.0  # frase forte: a margem larga fica
MARGEM_ECO_LIVRE_S = 0.3  # pergunta livre: só o rabo da fala no alto-falante; "sim" logo depois da pergunta vale (11/11)
FORTE_MAX_CARACTERES = 300
CONTINUACAO_S = 120  # o pedido seguinte, sem citar outro destino, continua na mesma janela por este tempo
AGIU_LEITURAS = 2  # leituras aceitas depois de uma ação em que a troca de host ainda é dela (navegação lenta)

FRASE_UM_MOMENTO = "Um momento, senhor."
FRASE_ANDAMENTO = "Ainda estou nisso, senhor."
FRASE_ERRO = "Não consegui concluir o pedido porque deu um erro interno, senhor."
FRASE_SEM_SINAL = "Não consegui confirmar que tocou porque não vi sinal de reprodução, senhor."
# Todo fim sem sucesso fala "Não consegui <o que> porque <motivo>, senhor." (~20 palavras no máximo; nunca vai ao log)
O_QUE_PADRAO = "concluir o pedido"
O_QUE = {"abrir_site": "abrir o site", "abrir_app": "abrir o app", "clicar": "clicar na página", "buscar": "fazer a busca",
         "digitar": "digitar o texto", "rolar": "rolar a página", "perguntar": "fazer a pergunta",
         "tecla": "apertar a tecla", "clicar_visual": "clicar na tela", "focar": "voltar para a janela"}  # pela ação em curso
MOTIVO_PADRAO = "não achei como seguir"  # desistir sem motivo aproveitável
MOTIVO_SEM_MUDANCA = "a tela não mudou depois de duas tentativas"
MOTIVO_NAO_AGIU = "o clique ou a digitação não funcionou duas vezes"
MOTIVO_INVALIDO = "o Claude respondeu fora do formato duas vezes"
MOTIVO_DO_CEREBRO = {"sem_claude": "não achei o Claude neste PC", "limite": "o limite do plano do Claude acabou",
                     "teto": "o Claude demorou demais", "processo": "o Claude parou de responder"}  # categorias de PensadorClaude.falha
PALAVRAS_O_QUE_MAX = 8  # do `texto` do desistir
PALAVRAS_MOTIVO_MAX = 12  # do `motivo` do desistir

# decisão provisória (a revisar): números do laço que o plano não fixou
LEITURA_CURTA = 80  # caracteres: leitura menor que isto, sem controles, é página ainda carregando
ESPERA_LER_S = 0.5  # entre releituras enquanto a página estabiliza
PLAY_ESPERA_S = 6.0  # espera pelo sinal de play depois de clicar em item de mídia ou em "tocar"
PLAY_PASSO_S = 0.5
TITULO_ESPERA_S = 8.0  # player (Netflix): o título da sessão de mídia demora a carregar; só depois de tanto "tocou outra coisa"
# palavras de título que não identificam a série: o site, o episódio ("T1:E30", "Episódio 30", "Temporada 1")
_SEM_SERIE = re.compile(r"netflix|assistindo|watching|ep(?:isodio|isode)?\d*|temporada|season|[te]\d+|\d+")
PERGUNTAS_MAX = 2  # perguntas do modelo por pedido; as confirmações do próprio laço não contam
ANDAMENTO_S = 20  # a cada tanto de espera por um passo, uma frase curta de andamento
ANDAMENTO_LIGADO = True
RESUMO_MAX = 300  # caracteres da linha "[pc: ...]" que o laço deixa na conversa (sem a fala)
RESUMO_COM_FALA = True  # False: o texto do `responder` não entra no contexto do cérebro
RESUMO_ITEM_MAX = 60  # caracteres do nome do item na linha
RESUMO_FALA_MAX = 300  # caracteres do texto falado no `responder` que entram na linha, entre marcas de dado
_VERBOS = {"abrir_site": "abriu", "abrir_app": "abriu", "clicar": "clicou", "buscar": "buscou", "digitar": "digitou",
           "rolar": "rolou", "perguntei": "perguntou", "tecla": "apertou tecla", "clicar_visual": "clicou", "focar": "voltou à janela"}
JEV_PASSO_LIGADO = True  # o Jev escolhe um clique simples antes de chamar o Claude
LIMIAR_JEV_PASSO = 0.85
JEV_PASSOS_MAX = 3  # cliques do Jev por pedido; responder e desistir são só do Claude
JEV_CANDIDATOS = 8
LIMIAR_JEV_TOCOU = 0.7  # o Jev diz que o título que tocou é o pedido
_DIZ_QUE_TOCA = re.compile(r"\b(tocando|reproduzindo|rodando|em reproducao|dei play|deu play)\b")  # roda sobre _norm
_MUSICA = re.compile(r"\b(musicas?|som|playlist|lofi|lo fi|beats?|mix|cancao|album|radio)\b")  # YouTube sem tela cheia (roda sobre _norm)
CLICAVEIS = ("Button", "Hyperlink", "ListItem", "TabItem", "MenuItem")
INSTRUCAO_JEV = "Qual controle clicar agora para avançar o pedido?"
DICA_RECUPERACAO ="a tela não mudou: tente tecla (espaco ou k para play e pausa) ou clicar_visual descrevendo o alvo"
NOTA_NAO_ACHEI = "não achei isso na tela"
TECLAS_DE_PLAY = ("espaco", "k", "play_pause")  # em pedido de mídia, depois delas espera o sinal de play
NOTA_COBERTO = "outro elemento cobre esse botão; procure o botão na janela/camada que está por cima"
ELEMENTOS_MAX = 120  # controles por passo no texto enviado ao modelo
VOLTAS_MAX = PASSOS_MAX * 3  # voltas do laço (inclui recusas e releituras), para nunca girar sem fim
_PLAY = re.compile(r"\b(tocar|play|assistir|reproduzir|reproduza|continuar|proximo episodio)\b")  # "Continuar" do modal da Netflix; "Próximo episódio" depois de um episódio
_ACOES = ("abrir_site", "abrir_app", "focar", "clicar", "buscar", "digitar", "rolar", "tecla", "clicar_visual", "perguntar",
          "responder", "desistir")
_CAMPOS = ("url", "app", "id", "texto", "direcao", "motivo", "modo")  # motivo: só o desistir usa (por que não deu); modo: só o digitar
MODOS_DIGITAR = ("acrescentar", "substituir")
# Só frase explícita de trocar o texto: verbo colado (até 2 palavras) em texto/conteúdo/escrito/documento, "substitui ... por", "reescreve", "do zero"; "tudo", "isso" e "nota" sozinhos não valem ("apaga a luz e escreve nota"). Roda sobre _norm.
_PEDE_SUBSTITUIR = re.compile(
    r"\b(?:(?:apag\w*|limp\w*|troc\w*|zer\w*|sobrescrev\w*)(?: \w+){0,3}? (?:texto|conteudo|escrito|documento)"
    r"|substitu\w*(?: \w+){0,4}? por|reescrev\w*|do zero)\b")
_OBRIGATORIOS = {"abrir_site": ("url",), "abrir_app": ("app",), "clicar": ("id",), "buscar": ("id", "texto"),
                 "digitar": ("id", "texto"), "rolar": ("direcao",), "perguntar": ("texto",), "responder": ("texto",),
                 "desistir": (), "tecla": ("texto",), "clicar_visual": ("texto",), "focar": ("texto",)}

# Todos os campos obrigatórios e anuláveis: é o formato do esquema estrito.
ESQUEMA_PASSO: dict = {
    "type": "object",
    "properties": {
        "acao": {"type": "string", "enum": list(_ACOES)},
        "url": {"type": ["string", "null"]},
        "app": {"type": ["string", "null"]},
        "id": {"type": ["integer", "null"]},
        "texto": {"type": ["string", "null"]},
        "direcao": {"type": ["string", "null"]},
        "motivo": {"type": ["string", "null"]},
        "modo": {"type": ["string", "null"]},
        "opcoes": {"type": ["array", "null"], "items": {"type": "string"}},
    },
    "required": ["acao", *_CAMPOS, "opcoes"],
    "additionalProperties": False,
}


@dataclass
class Desfecho:
    tipo: str  # "respondeu", "desistiu", "tocou", "parou", "teto" ou "cancelado"
    fala: str = ""


Pensar = Callable[[list[dict]], Awaitable[dict | None]]
Falar = Callable[[str], Awaitable[object]]


def _norm(texto: str) -> str:
    return " ".join(r._palavras(texto))


def _dado(texto: str) -> str:
    """Texto lido vai entre <pagina> e </pagina>: a página não fecha a marca sozinha."""
    return texto.replace("</pagina>", "< /pagina>").replace("<pagina>", "< pagina>")


def _validar(bruto) -> dict | None:
    """Passo bem formado (campos do tipo certo e os obrigatórios da ação) ou None."""
    if not isinstance(bruto, dict) or bruto.get("acao") not in _ACOES:
        return None
    for campo in _CAMPOS:
        v = bruto.get(campo)
        if v is not None and (isinstance(v, bool) or not isinstance(v, int if campo == "id" else str)):
            return None
    if any(bruto.get(c) is None for c in _OBRIGATORIOS[bruto["acao"]]):
        return None
    if bruto.get("modo") not in (None, *MODOS_DIGITAR):
        return None
    if bruto["acao"] in ("perguntar", "responder") and not bruto["texto"].strip():
        return None  # fala vazia: volta ao modelo como recusa
    opcoes = bruto.get("opcoes")  # .get: passo gravado antes das opções não tem a chave
    if not (isinstance(opcoes, list) and all(isinstance(o, str) for o in opcoes)):
        opcoes = None
    return {**{c: bruto.get(c) for c in ("acao", *_CAMPOS)}, "opcoes": opcoes}


_FALHA = object()  # o cérebro não respondeu (sem Claude, erro, teto, limite do plano); diferente de resposta inválida


class Laco:
    """Um laço por pedido. `executar` solta a vaga da sessão no `finally`, em qualquer saída; `cancelar()` cancela o que
    estiver esperando (pensar, sonda, Claude, pergunta) e nenhuma ação sai depois disso."""

    def __init__(self, backend: Backend, pensar: Pensar,
                 perguntar: Callable[[str, str], Awaitable[str | None]], falar: Falar,
                 dormir: Callable[[], Awaitable[object]], timers: Timers, sessao: Sessao,
                 relogio: Callable[[], float] = time.monotonic, sites: dict[str, Site] = SITES,
                 extras: frozenset[str] = frozenset(), esperar=asyncio.sleep, achar_janela=janela_da_aba, montar_envio=None,
                 esperar_andamento=asyncio.sleep, gravacoes: gravacao.Gravacoes | None = None,
                 ao_passo: Callable[[str, dict], None] | None = None,
                 ao_desfecho: Callable[[str, Desfecho], None] | None = None,
                 visao: Callable[[str, Olhar], Awaitable[Alvo | None]] | None = None,
                 escolher: Callable[[str, str, list[str]], Awaitable[tuple[int, float] | None]] | None = None):
        # extras (privado/bloqueio_pc.txt, via carregar_extras), esperar, achar_janela e montar_envio: opcionais, só o
        # bot ou o teste os troca. montar_envio None = pergunta.montar_pergunta_envio (Task 10), importado quando preciso.
        self._b, self._pensar = backend, pensar
        self._visao = visao  # None: clicar_visual é recusado (sem visão)
        self._escolher = escolher  # None: sem chave do Jev, todo passo é do Claude
        self._esperar_andamento, self._gravacoes = esperar_andamento, gravacoes  # gravacoes None: não grava nem repete
        self._ao_passo, self._ao_desfecho = ao_passo, ao_desfecho  # painel da janela: síncronos, opcionais
        self._perguntar_fn, self._falar_fn, self._dormir, self._timers, self._sessao = perguntar, falar, dormir, timers, sessao
        self._relogio, self._sites, self._extras = relogio, sites, extras
        self._esperar, self._achar, self._montar_envio = esperar, achar_janela, montar_envio
        self.cancelado = False
        self.rodando = False
        self.inicio: float | None = None
        self._tarefa: asyncio.Task | None = None
        self.ultimo: tuple[str, float] | None = None  # (site ou app, instante) do último pedido; o bloco de estado da conversa
        self._continuacao: dict | None = None  # fora do _zerar: é o que sobrevive de um pedido ao outro
        self._zerar("")

    def _zerar(self, pedido: str) -> None:
        self._pedido = pedido
        self._respostas: list[str] = []
        self._historico: list[str] = []
        self._notas: list[str] = []
        self._perguntas = self._pediu_dado = 0
        self._passos = self._voltas = self._invalidos = self._sem_mudanca = self._recusas = 0
        self._dica = False  # a dica de recuperação (tecla/clicar_visual) já foi dada neste pedido
        self._jev_passos, self._ultimo_jev = 0, False  # cliques do Jev neste pedido; o último passo foi dele
        self._nao_agiu = 0  # ações seguidas que a sonda disse que não agiram (a página pode mudar sozinha, como a prévia da Netflix)
        self._pausado = 0.0
        self._t_chamada = self._t_leitura = 0.0  # tempos do passo em curso, só para o log
        self._acao_pendente = False
        self._acao_atual = "-"  # ação do passo em curso, só para o log de "laço caiu"
        self._hwnd: int | None = None
        self._chrome = False
        self._aba = False  # a janela é do usuário (aba nova nela): o laço nunca navega a aba dele de volta
        self._origem: str | None = None
        self._repeticao_usada = False  # algum passo gravado foi de fato repetido neste pedido
        self._item: str | None = None  # nome do item de mídia que o PC casou com o pedido e clicou
        self._abertos: set[str] = set()  # endereços já abertos neste pedido: abrir de novo seria outra aba igual
        self._alcancados: set[str] = set()
        self._janelas: frozenset[int] = frozenset()
        self._base_midias: tuple[Midia, ...] = ()
        self._aprovados: set[str] = set()  # nomes de título que o usuário aprovou ou escolheu
        self._chave: str | None = None  # chave da gravação (pedido + origem no começo do laço)
        self._repeticao: list[dict] | None = None  # passos gravados ainda por repetir; None = laço normal
        self._gravando: list[dict] = []  # passos aceitos deste pedido, pelos campos do Elemento
        self._anterior: str | None = None  # pedido herdado da continuação
        self._herdada: str | None = None  # site ou app herdado: conta como citado para mídia e abrir_app
        self._travou = False  # parou por bloqueio, login ou "a aba mudou": a janela não é herdada
        self._novo_hwnd()

    def _novo_hwnd(self) -> None:
        self._agiu = 0  # leituras que ainda contam como efeito da última ação real (clicar, buscar, digitar, rolar)
        self._dele = False  # janela/aba que já era do usuário e o laço só focou (focar)
        self._endereco: str | None = None
        self._hash: str | None = None
        self._elementos: dict[int, r.Elemento] = {}
        self._ultima = None

    # ---- interface pública ----

    def juntar(self, texto: str) -> None:
        """Fragmento tardio do mesmo turno (o VAD corta a fala): entra no pedido."""
        self._pedido = f"{self._pedido} {texto}".strip()

    def cancelar(self) -> None:
        self.cancelado = True
        if self._tarefa is not None and not self._tarefa.done():
            self._tarefa.cancel()

    async def executar(self, transcricao: str) -> Desfecho:
        if self.rodando:
            raise RuntimeError("laço já em execução")
        self._zerar(transcricao)
        self.rodando, self.cancelado, self.inicio = True, False, self._relogio()
        self._tarefa = asyncio.ensure_future(self._corpo())
        try:
            desfecho = await self._tarefa
        except asyncio.CancelledError:
            if not self.cancelado:  # cancelaram quem chamou (conexão caiu): sobe
                raise
            desfecho = Desfecho("cancelado")
        except Exception as erro:
            onde = traceback.extract_tb(erro.__traceback__)[-1]  # só o tipo, a função e a linha: nunca o texto do erro
            log.warning("laço caiu: %s em %s:%s (passo %s)", type(erro).__name__, onde.name, onde.lineno, self._acao_atual)
            desfecho = Desfecho("parou", FRASE_ERRO)
            await self._falar(FRASE_ERRO)
        finally:
            self.rodando, self.inicio, self._tarefa = False, None, None
            if fechar := getattr(self._pensar, "fechar", None):  # o Claude persistente morre com o laço, em qualquer saída
                try:
                    await fechar()
                except Exception as erro:
                    log.warning("fechar o cérebro falhou: %s", type(erro).__name__)
            if self._sessao.dono == "laco":  # não usa resultado_guardado: concluir_tarefa guardaria a fala dormindo
                self._sessao.cancelar_tarefa()
        self._guardar(desfecho)
        self._avisar(self._ao_desfecho, self._pedido, desfecho)
        log.info("laço terminou: %s, %d passos", desfecho.tipo, self._passos)
        return desfecho

    def resumo(self, desfecho: Desfecho) -> str:
        """Linha para a conversa só com o que o PC controla: site ou app, ações, o item que ele casou e o desfecho. O título
        da janela fica de fora (pode ser de outra aba). O texto falado no `responder` entra marcado como dado."""
        vistas: list[str] = []
        for a in self._historico:
            if (verbo := _VERBOS.get(a)) and (not vistas or vistas[-1] != verbo):
                vistas.append(verbo)
        item = ""
        if self._item:  # nome lido da página: entra marcado como dado, fora do corte dos verbos
            item = f'{"tocou" if desfecho.tipo == "tocou" else "escolheu"} <pagina>{_dado(self._item[:RESUMO_ITEM_MAX])}</pagina>'
        fim = "concluído" if desfecho.tipo in ("respondeu", "tocou") else "parado"
        sobra = RESUMO_MAX - len(f"[pc: {self._origem or ''} |  | {fim}]") - len(item) - 2
        verbos = ", ".join(vistas)[:max(sobra, 0)]
        partes = [self._origem, ", ".join(p for p in (verbos, item) if p), fim]
        if RESUMO_COM_FALA and desfecho.tipo == "respondeu" and desfecho.fala != FRASE_SEM_SINAL:
            partes.append(f"disse: <pagina>{_dado(desfecho.fala[:RESUMO_FALA_MAX])}</pagina>")
        return "[pc: " + " | ".join(p for p in partes if p) + "]"

    def _avisar(self, funcao, *args) -> None:
        if funcao is None:
            return
        try:
            funcao(*args)
        except Exception as erro:  # o painel é enfeite: nunca derruba o laço
            log.warning("aviso do painel falhou: %s", type(erro).__name__)

    def _registrar_passo(self, quem: str, resultado: str) -> None:
        log.info(linha_passo(self._voltas, quem, getattr(self._b, "nome", type(self._b).__name__),
                             self._t_chamada, self._t_leitura, resultado))
        self._t_leitura = 0.0

    # ---- o laço ----

    def _gasto(self) -> float:
        return self._relogio() - (self.inicio or 0.0) - self._pausado

    def _guardar(self, desfecho: Desfecho) -> None:
        if self._origem:
            self.ultimo = (self._origem, self._relogio())
        ok = desfecho.tipo != "cancelado" and self._hwnd is not None and not self._travou
        self._fechar_gravacao(desfecho)
        self._continuacao = None if not ok else {
            "hwnd": self._hwnd, "chrome": self._chrome, "aba": self._aba, "origem": self._origem,
            "alcancados": frozenset(self._alcancados), "pedido": self._pedido, "expira": self._relogio() + CONTINUACAO_S,
            "endereco": self._endereco, "agiu": self._agiu, "dele": self._dele}  # o endereço deixa a 1ª leitura herdada ver a troca de aba

    async def _herdar(self) -> None:
        """Pedido sem destino próprio, dentro do prazo e com a janela ainda aberta: continua nela. Sempre consome o contexto.
        Nunca herda respostas, títulos aprovados nem a frase forte."""
        c, self._continuacao = self._continuacao, None
        if c is None or self._relogio() >= c["expira"] or r.cita_destino(self._pedido):
            return
        atuais = await self._b.janelas()
        if c["hwnd"] not in atuais:
            return
        self._hwnd, self._chrome, self._aba, self._origem = c["hwnd"], c["chrome"], c["aba"], c["origem"]
        self._alcancados, self._janelas = set(c["alcancados"]), atuais  # janelas do usuário abertas nesse meio tempo não contam
        self._anterior, self._herdada = c["pedido"], c["origem"]
        self._endereco, self._agiu, self._dele = c["endereco"], c["agiu"], c.get("dele", False)

    async def _corpo(self) -> Desfecho:
        await self._herdar()
        if r.pedido_de_midia(self._pedido, self._herdada):
            self._base_midias = await self._b.midias()
        self._abrir_gravacao()
        while True:
            if self.cancelado:
                return Desfecho("cancelado")
            if self._passos >= PASSOS_MAX or self._voltas >= VOLTAS_MAX or self._gasto() >= ACAO_MAX_S:
                return await self._teto()
            self._voltas += 1
            if self._hwnd is not None:
                if desfecho := await self._ler():
                    return desfecho
            passo = await self._proximo_passo()
            if isinstance(passo, Desfecho):
                return passo
            recusas = self._historico.count("recusado")
            notas = len(self._notas)
            self._avisar(self._ao_passo, self._pedido, passo[0])
            desfecho = await self._executar_passo(*passo)
            recusado = self._historico.count("recusado") > recusas
            self._registrar_passo(passo[1], RESULTADO_RECUSADO if recusado else RESULTADO_ACEITO)
            self._anotar_passo(*passo, recusado or "a ação não agiu" in self._notas[notas:])
            if desfecho:
                return desfecho

    async def _falar(self, texto: str) -> None:
        if self.cancelado or not texto:
            return
        try:
            await self._falar_fn(texto)
        except Exception as erro:  # falar falhar não derruba o laço
            log.warning("falar falhou: %s", type(erro).__name__)

    def _o_que(self) -> str:
        """O objetivo do pedido ("pôr sora no kanata") quando é mídia com título; senão a ação em curso."""
        if r.pedido_de_midia(self._pedido, self._origem):
            if alvo := r.alvo_nomeado(self._pedido, self._origem or ""):
                return f"pôr {alvo}"
        return O_QUE.get(self._acao_atual, O_QUE_PADRAO)

    def _fala_de_falha(self, o_que: str, motivo: str) -> str:
        return f"Não consegui {o_que} porque {motivo}, senhor."

    async def _parou(self, motivo: str) -> Desfecho:
        if self.cancelado:
            return Desfecho("cancelado")
        fala = self._fala_de_falha(self._o_que(), motivo)
        await self._falar(fala)
        return Desfecho("parou", fala)

    def fala_do_teto(self) -> str:
        return f"Não consegui {O_QUE_PADRAO} porque o pedido passou do limite, senhor. Fiz {self._passos} passos."

    async def _teto(self) -> Desfecho:
        fala = self.fala_do_teto()
        await self._falar(fala)
        return Desfecho("teto", fala)

    async def _nao_consegui(self, motivo: str, o_que: str | None = None) -> Desfecho:
        if self.cancelado:
            return Desfecho("cancelado")
        fala = self._fala_de_falha(o_que or self._o_que(), motivo)
        await self._falar(fala)
        return Desfecho("desistiu", fala)

    async def _desistiu(self, passo: dict) -> Desfecho:
        """O `desistir` do modelo: o que e por que são dele, mas é texto não confiável que vai à voz: curto e pelo mesmo filtro."""
        def curto(texto: str | None, palavras: int) -> str:
            t = " ".join((texto or "").split()[:palavras]).strip(" .,;:!")
            return t if t and r.fala_permitida(t, "desistir") else ""
        return await self._nao_consegui(curto(passo["motivo"], PALAVRAS_MOTIVO_MAX) or MOTIVO_PADRAO,
                                        curto(passo["texto"], PALAVRAS_O_QUE_MAX) or None)

    async def _perguntar(self, texto: str, tipo: str, opcoes: tuple[str, ...] = ()) -> str | None:
        """O relógio do laço e o da sessão pausam na espera pela resposta."""
        inicio = self._relogio()
        self._sessao.pausar_relogio(inicio)
        try:
            return await (self._perguntar_fn(texto, tipo, opcoes) if opcoes else self._perguntar_fn(texto, tipo))
        finally:
            fim = self._relogio()
            self._pausado += fim - inicio
            self._sessao.retomar_relogio(fim)

    async def _aprovou(self, texto: str) -> bool:
        resposta = await self._perguntar(texto, "livre")
        return resposta is not None and sim_ou_nao(resposta) == "sim"

    # ---- leitura ----

    async def _ler(self) -> Desfecho | None:
        """Espera a página estabilizar (teto de 10 s): leitura curta demais, ou endereço diferente do anterior, relê.
        Confere endereço, bloqueio e site permitido a cada leitura; só para se reprovar. Não conta como passo."""
        fim = self._relogio() + LER_ESTAVEL_S
        anterior = self._endereco
        while True:
            inicio = self._relogio()
            try:
                leitura = await self._b.ler(self._hwnd)
            except Exception as erro:
                self._t_leitura += self._relogio() - inicio
                log.warning("ler falhou: %s", type(erro).__name__)
                if self._relogio() >= fim:  # app recém-aberto ainda carregando falha a leitura (Spotify, 09/11): relê
                    return await self._parou("a janela não pôde ser lida")
                await self._esperar(ESPERA_LER_S)
                continue
            self._t_leitura += self._relogio() - inicio
            if self.cancelado:
                return Desfecho("cancelado")
            veredito = await self._conferir(leitura)
            if isinstance(veredito, Desfecho):
                return veredito
            if veredito == "reler":  # abriu outra janela depois de aprovado: lê a nova
                anterior, fim = None, self._relogio() + LER_ESTAVEL_S
                continue
            curta = len(leitura.texto.strip()) < LEITURA_CURTA and not leitura.elementos
            mudou = self._chrome and anterior is not None and leitura.endereco != anterior
            if (curta or mudou) and self._relogio() < fim:
                anterior = leitura.endereco
                await self._esperar(ESPERA_LER_S)
                continue
            break
        self._aceitar(leitura)
        return None

    def _aceitar(self, leitura) -> None:
        h = hashlib.sha1(f"{leitura.endereco}\n{leitura.texto}".encode()).hexdigest()
        if self._hash is not None and self._acao_pendente:  # "mudou" = texto lido mais endereço
            self._sem_mudanca = self._sem_mudanca + 1 if h == self._hash else 0
        self._hash, self._acao_pendente, self._agiu = h, False, max(0, self._agiu - 1)
        self._endereco, self._ultima = leitura.endereco, leitura
        self._elementos = {e.id: e for e in leitura.elementos}

    async def _conferir(self, leitura) -> Desfecho | str | None:
        """None: pode seguir. "reler": outra janela. Desfecho: parou."""
        if self._chrome:
            host = r.host_de(leitura.endereco) if leitura.endereco else None
            if host is None:
                return await self._parou("o endereço da página não pôde ser lido")
        else:
            host = None
        if r.bloqueado(host, leitura.titulo, self._extras):
            self._travou = True
            return await self._parou("essa página é bloqueada")
        if r.pagina_de_login(leitura.endereco, leitura.elementos):
            self._travou = True
            return await self._parou("a página pede login")
        if self._aba and not self._agiu and host and self._endereco and host != r.host_de(self._endereco):
            self._travou = True
            return await self._parou("a aba mudou")  # o usuário trocou de aba ou a página andou sozinha: não mexe nela
        if host is None or host in self._alcancados:
            return None
        d = r.avaliar_navegacao(host, self._pedido, frozenset(self._alcancados), self._extras)
        if d.tipo == "ok":
            self._alcancados.add(host)
            self._origem = self._origem_de(host) or self._origem
            return None
        if d.tipo == "parar":
            self._travou = True
            return await self._parou("essa página é bloqueada")
        if self._dele:  # aba do usuário que o laço só focou: para sem navegá-la de volta
            self._travou = True
            return await self._parou("essa página não foi pedida")
        await self._b.voltar(self._hwnd)  # a navegação já aconteceu: volta, depois pergunta (ou para)
        if d.tipo == "perguntar" and await self._aprovou(f"A página foi para {d.valor}. Posso abrir esse site, senhor?"):
            return await self._abrir(f"https://{d.valor}/", d.valor) or "reler"
        return await self._parou("a página saiu do que o senhor pediu")

    def _origem_de(self, host: str) -> str | None:
        return next((s.chave for s in self._sites.values() if host == s.dominio or host.endswith("." + s.dominio)), None)

    def _mensagens(self) -> list[dict]:
        partes = [f"Pedido anterior do usuário: {self._anterior}"] if self._anterior else []
        partes.append(f"Pedido do usuário: {self._pedido}")
        if self._respostas:
            partes.append("Respostas do usuário: " + " | ".join(self._respostas))
        if self._historico:
            partes.append("Passos já feitos: " + ", ".join(self._historico[-8:]))
        if self._notas:
            partes.append("Avisos do PC: " + "; ".join(self._notas))
        leitura = self._ultima
        partes.append(self._enderecos_prontos())
        if self._hwnd is None or leitura is None:
            partes.append("Ainda não há janela aberta: abra um site ou um app.")
        else:  # o título da janela nunca vai ao modelo: pode ser de outra aba e só serve ao bloqueio
            controles = "\n".join(f"{e.id}: {e.tipo}: {_dado(e.nome[:80])}" for e in self._mais_parecidos(leitura.elementos))
            aviso = " (texto cortado)" if leitura.cortado else ""
            partes.append(f"Leitura mais recente{aviso}:\n<pagina>\n{_dado(cortar_pagina(leitura.texto))}\n"
                          f"Controles:\n{controles}\n</pagina>")
        return [{"role": "user", "content": "\n\n".join(partes)}]

    def _enderecos_prontos(self) -> str:
        """Endereços que o modelo pode usar em abrir_site, com o que cada um mostra, e as buscas por site."""
        prontos = "Endereços prontos (use em abrir_site): " + "; ".join(
            f"{url} = {r.DESCRICAO_MOLDES[chave]}" for chave, url in r.MOLDES.items())
        buscas = "; ".join(f"{c}: {m.replace('{q}', 'TERMO')}" for c, m in r.BUSCAS.items())
        return f"{prontos}\nBuscas (TERMO só com palavras do usuário): {buscas}"

    def _mais_parecidos(self, elementos) -> list:
        """Até ELEMENTOS_MAX controles; passando disso, os mais parecidos com o pedido vão primeiro (sort estável).
        Os ids não mudam: `_elementos` guarda todos, então um id fora do corte continua válido."""
        if len(elementos) <= ELEMENTOS_MAX:
            return list(elementos)
        quer = r._citados_sem_alvo(self._pedido)

        def semelhanca(e) -> float:
            ficha = quer & set(r._palavras(e.nome))
            return max(r.casa_alvo(e.nome, self._pedido), len(ficha) / len(quer) if quer else 0.0)
        return sorted(elementos, key=semelhanca, reverse=True)[:ELEMENTOS_MAX]

    # ---- cérebro ----

    async def _chamar(self, fn: Pensar) -> dict | None | object:
        """O passo validado; None se a resposta veio mas não vale (inválida); _FALHA se o cérebro não respondeu."""
        inicio = self._relogio()
        try:
            bruto = await self._com_andamento(fn(self._mensagens()))
            return _FALHA if bruto is None else _validar(bruto)
        except Exception as erro:
            log.warning("cérebro falhou: %s", type(erro).__name__)
            return _FALHA
        finally:
            self._t_chamada = self._relogio() - inicio

    async def _com_andamento(self, espera):
        """Espera o passo do modelo; a cada ANDAMENTO_S sem resposta, fala a frase de andamento."""
        tarefa = asyncio.ensure_future(espera)
        try:
            while ANDAMENTO_LIGADO:
                relogio = asyncio.ensure_future(self._esperar_andamento(ANDAMENTO_S))
                try:
                    feitas, _ = await asyncio.wait({tarefa, relogio}, return_when=asyncio.FIRST_COMPLETED)
                finally:
                    relogio.cancel()
                if tarefa in feitas:
                    break
                await self._falar(FRASE_ANDAMENTO)
            return await tarefa
        finally:
            if not tarefa.done():  # cancelar() ou erro: mata o Claude em curso
                tarefa.cancel()

    async def _proximo_passo(self) -> tuple[dict, str] | Desfecho:
        """O Haiku do plano escolhe o passo. Desistir, 2 ações sem mudar nada, 2 respostas inválidas ou cérebro sem resposta
        (`pensar` devolveu None: sem Claude, erro, teto, limite do plano): o laço para."""
        while True:
            if self._repeticao is not None and self._sem_mudanca >= 1:  # passo repetido que não mexeu na tela: o modelo assume
                self._abandonar_repeticao()
            if self._sem_mudanca >= 2:
                return await self._nao_consegui(MOTIVO_SEM_MUDANCA)
            if self._nao_agiu >= 2:
                return await self._nao_consegui(MOTIVO_NAO_AGIU)
            if self._invalidos >= 2:
                return await self._nao_consegui(MOTIVO_INVALIDO)
            if (self._sem_mudanca == 1 or self._nao_agiu == 1) and not self._dica:  # uma vez por pedido
                self._dica = True
                self._notas.append(DICA_RECUPERACAO)
            if gravado := self._passo_gravado():
                self._t_chamada = 0.0  # passo gravado não chamou o cérebro: o log não herda o tempo do passo anterior
                self._ultimo_jev = False
                return gravado, "gravacao"
            if jev := await self._passo_do_jev():
                return jev, "jev"
            self._ultimo_jev = False
            passo = await self._chamar(self._pensar)
            if passo is _FALHA:  # sem resposta (sem Claude, erro, teto, limite do plano): não há outro cérebro
                return await self._nao_consegui(MOTIVO_DO_CEREBRO.get(getattr(self._pensar, "falha", None), MOTIVO_DO_CEREBRO["processo"]))
            if passo is None:
                self._invalidos += 1
                self._registrar_passo("principal", RESULTADO_INVALIDO)
                self._notas.append("resposta inválida: devolva só um passo no esquema")
                continue
            self._invalidos = 0
            self._notas.clear()
            return passo, "principal"

    async def _passo_do_jev(self) -> dict | None:
        """Clique simples escolhido pelo Jev (~0,3 s) entre os controles clicáveis mais parecidos com o pedido; None = o
        Claude decide. Nunca repete depois de um clique dele que não mudou a tela; o clique passa pelas mesmas regras."""
        if not (JEV_PASSO_LIGADO and self._escolher and self._hwnd is not None and self._ultima is not None):
            return None
        if self._jev_passos >= JEV_PASSOS_MAX or (self._ultimo_jev and (self._sem_mudanca or self._nao_agiu)):
            return None
        candidatos = [e for e in self._mais_parecidos(self._ultima.elementos) if e.tipo in CLICAVEIS][:JEV_CANDIDATOS]
        if not candidatos:
            return None
        estado = f"Pedido do usuário: {self._pedido}"
        if self._historico:
            estado += "\nPassos já feitos: " + ", ".join(self._historico[-8:])
        inicio = self._relogio()
        achou = await self._escolher(estado, INSTRUCAO_JEV, [f"{e.tipo}: {e.nome[:60]}" for e in candidatos])
        self._t_chamada = self._relogio() - inicio
        if achou is None or achou[1] < LIMIAR_JEV_PASSO or not 0 <= achou[0] < len(candidatos):
            return None
        self._jev_passos += 1
        self._ultimo_jev = True
        return {"acao": "clicar", **{c: None for c in _CAMPOS}, "id": candidatos[achou[0]].id, "opcoes": None}

    # ---- gravar e repetir (Fase 7) ----

    def _abrir_gravacao(self) -> None:
        self._chave = gravacao.chave(_norm(self._pedido), self._origem)
        if self._gravacoes is not None and gravacao.GRAVACAO_LIGADA:
            self._repeticao = self._gravacoes.buscar(self._chave)
            if self._repeticao:
                log.info("gravação: repetição usada, %d passos", len(self._repeticao))

    def _abandonar_repeticao(self) -> None:
        if self._repeticao is not None:
            log.info("gravação: repetição abandonada no passo %d", len(self._gravando) + 1)
            self._repeticao = None

    def _passo_gravado(self) -> dict | None:
        """Próximo passo gravado, se a leitura atual tem o elemento esperado; senão abandona e o modelo assume. O passo
        sai pelo mesmo _validar e, depois, pelas mesmas regras de qualquer passo do modelo."""
        if self._repeticao is None:
            return None
        if not self._repeticao:  # acabaram os passos e o pedido não terminou
            self._abandonar_repeticao()
            return None
        gravado = self._repeticao[0]
        bruto = {c: gravado.get(c) for c in ("acao", *_CAMPOS)}
        if "elemento" in gravado:
            el = gravacao.achar(gravado["elemento"], self._elementos.values()) if self._hwnd is not None else None
            bruto["id"] = el.id if el else None
        passo = _validar(bruto)
        if passo is None:
            self._abandonar_repeticao()
            return None
        self._repeticao.pop(0)
        self._repeticao_usada = True
        return passo

    def _anotar_passo(self, passo: dict, quem: str, falhou: bool) -> None:
        if falhou:
            if quem == "gravacao":
                self._abandonar_repeticao()
            return
        if passo["acao"] not in gravacao.ACOES_GRAVAVEIS:
            return
        g = {c: passo[c] for c in _CAMPOS if c != "id" and passo[c] is not None}
        g["acao"] = passo["acao"]
        if passo["id"] is not None:
            g["elemento"] = gravacao.ficha(self._elementos[passo["id"]])
        self._gravando.append(g)

    def _fechar_gravacao(self, desfecho: Desfecho) -> None:
        """Só um laço que tocou, sem perguntas ao usuário, vira gravação (regrava no lugar da anterior). Repetição que não
        terminou bem apaga a gravação velha."""
        if self._gravacoes is None or not gravacao.GRAVACAO_LIGADA or self._chave is None:
            return
        if desfecho.tipo == "tocou" and self._gravando and not self._respostas:
            self._gravacoes.guardar(self._chave, self._gravando)
            log.info("gravação: guardada, %d passos", len(self._gravando))
        elif desfecho.tipo not in ("cancelado", "tocou") and self._repeticao_usada and self._gravacoes.buscar(self._chave):
            self._gravacoes.apagar(self._chave)
            log.info("gravação: apagada, o laço terminou em %s", desfecho.tipo)

    # ---- passos ----

    def _agir(self, acao: str, ok: bool) -> None:
        self._passos += 1
        self._historico.append(acao)
        self._acao_pendente = True
        if acao not in ("abrir_site", "abrir_app", "focar"):
            self._agiu = AGIU_LEITURAS
        self._nao_agiu = 0 if ok else self._nao_agiu + 1
        if not ok:
            self._notas.append("a ação não agiu")

    def _recusar(self, nota: str) -> None:
        log.info("laço: recusado (%s): %s", self._acao_atual, nota)  # nota é texto fixo do código, nunca da página
        self._notas.append("recusado: " + nota)
        self._historico.append("recusado")
        self._acao_pendente = True

    async def _executar_passo(self, passo: dict, quem: str) -> Desfecho | None:
        if self.cancelado:  # checado antes de toda ação
            return Desfecho("cancelado")
        acao = passo["acao"]
        self._acao_atual = acao
        log.info("laço: passo %d %s (%s)", self._passos + 1, acao, quem)
        if acao == "abrir_site":
            return await self._passo_abrir_site(passo["url"])
        if acao == "abrir_app":
            return await self._passo_abrir_app(passo["app"])
        if acao == "focar":
            return await self._passo_focar(passo["texto"].strip().lower())
        if acao in ("clicar", "buscar", "digitar"):
            el = self._elementos.get(passo["id"])
            if el is None:
                self._recusar("id fora da leitura atual")
                return None
            if acao == "clicar":
                return await self._passo_clicar(el)
            return await self._passo_texto(acao, el, passo["texto"], passo["modo"])
        if acao == "rolar":
            if self._hwnd is None or passo["direcao"] not in ("cima", "baixo", "up", "down"):
                self._recusar("rolar pede janela aberta e direção cima ou baixo")
                return None
            if self.cancelado:
                return Desfecho("cancelado")
            await self._na_frente()
            self._agir("rolar", await self._b.rolar(self._hwnd, passo["direcao"]))
            return None
        if acao == "tecla":
            return await self._passo_tecla(passo["texto"].strip())
        if acao == "clicar_visual":
            return await self._passo_clicar_visual(passo["texto"].strip())
        if acao == "perguntar":
            return await self._passo_perguntar(passo["texto"], passo.get("opcoes"))
        if acao == "responder":
            return await self._passo_responder(passo["texto"])
        return await self._desistiu(passo)  # desistir: o modelo travou

    async def _passo_abrir_site(self, url: str) -> Desfecho | None:
        achada = r.busca_de(url)
        if achada:
            return await self._passo_busca(*achada)
        d = r.avaliar_url(url, self._pedido, frozenset(self._alcancados), self._sites, self._extras)
        if d.tipo == "recusar":  # rodada de 09/11: o endereço de um repositório parava o pedido em vez de voltar ao modelo
            self._recusar("endereço com caminho fora dos prontos: abra a raiz ou clique no link da página")
            return None
        if d.tipo == "perguntar":
            if not await self._aprovou(f"Posso abrir {d.valor}, senhor?"):
                return await self._parou("o senhor não autorizou abrir esse site")
        elif d.tipo != "ok":
            return await self._parou("esse site não pode ser aberto")
        host = r.host_de(url)
        alvo = url.strip() if url.strip() in r.MOLDES.values() else f"https://{host}/"  # aprovado ou não: pela raiz
        return await self._abrir(alvo, host)

    async def _na_frente(self) -> bool:
        """A janela do pedido em primeiro plano antes de agir: atrás, a UIA não mexia nela (rodada de 09/11)."""
        if await self._b.primeiro_plano() == self._hwnd:
            return True
        return await self._b.trazer(self._hwnd)

    async def _passo_busca(self, site: str, termo: str) -> Desfecho | None:
        """Busca por molde: o termo só leva palavras do usuário e a URL é montada aqui, nunca a do modelo."""
        molde = r.BUSCAS[site]
        host = urlsplit(molde).netloc
        d = r.avaliar_url(f"https://{host}/", self._pedido, frozenset(self._alcancados), self._sites, self._extras)
        if d.tipo == "perguntar":
            if not await self._aprovou(f"Posso abrir {d.valor}, senhor?"):
                return await self._parou("o senhor não autorizou abrir esse site")
        elif d.tipo != "ok":
            return await self._parou("esse site não pode ser aberto")
        return await self._abrir(molde.replace("{q}", quote(termo, safe="")), host)

    async def _abrir(self, url: str, host: str) -> Desfecho | None:
        if url in self._abertos and self._endereco and r.host_de(self._endereco) == host:  # 09/11: 5 abas do Gmail
            self._recusar("esse site já está aberto nesta aba: navegue pela página (clicar, buscar ou rolar)")
            return None
        antes = await self._b.janelas()
        await self._b.abrir_site(url)
        hwnd = await self._achar(self._b, antes, host)
        if hwnd is None:
            return await self._parou("a janela que abri não apareceu")
        self._agir("abrir_site", True)
        self._hwnd, self._chrome, self._alcancados = hwnd, True, self._alcancados | {host}
        self._origem, self._janelas = self._origem_de(host), antes | {hwnd}
        self._aba = hwnd in antes
        self._abertos.add(url)
        self._novo_hwnd()
        self._acao_pendente = False
        await self._na_frente()
        return None

    async def _passo_abrir_app(self, nome: str) -> Desfecho | None:
        nome = nome.strip().lower()
        if r.e_outro_navegador(nome):
            return await self._parou(r.FRASE_SO_CHROME)
        if not r.nome_de_app_citado(nome, self._pedido) and nome != self._herdada:  # qualquer app, mas só o que o usuário falou
            return await self._parou("esse app não foi pedido")
        antes = await self._b.janelas()
        hwnd = await self._b.abrir_app(nome)
        if hwnd is None:
            return await self._parou("não achei esse app")
        self._agir("abrir_app", True)
        self._hwnd, self._chrome, self._origem, self._janelas = hwnd, False, nome, antes | {hwnd}
        self._aba = False
        self._novo_hwnd()
        self._acao_pendente = False
        await self._na_frente()
        return None

    async def _passo_focar(self, nome: str) -> Desfecho | None:
        """Volta para a janela (ou aba do Chrome) que já está aberta, sem abrir outra. Só o nome que o usuário falou; a leitura
        seguinte passa pelas mesmas conferências (bloqueio, login). No Chrome a janela é do usuário: o laço nunca a navega de volta."""
        if not nome or (not r.nome_de_app_citado(nome, self._pedido) and nome != self._herdada):
            self._recusar("focar só um site ou app que o usuário citou")
            return None
        achada = await self._b.procurar(nome)  # sem trocar nada: o título passa pelo bloqueio antes de a aba vir à frente
        if achada is not None and r.bloqueado(None, achada[1], self._extras):
            self._travou = True
            return await self._parou("essa página é bloqueada")
        hwnd = await self._b.focar(nome) if achada is not None else None
        if hwnd is None:
            self._notas.append("não achei janela aberta com esse nome: abra o site ou o app")
            self._historico.append("recusado")
            return None
        info = await self._b.info_janela(hwnd)
        chrome = info is not None and info.processo.lower().removesuffix(".exe") == "chrome"
        self._agir("focar", True)
        self._hwnd, self._chrome, self._aba = hwnd, chrome, chrome
        self._origem, self._janelas = (None if chrome else nome), await self._b.janelas() | {hwnd}
        self._novo_hwnd()
        self._dele = True  # a aba (ou janela) já era do usuário: o laço nunca a navega de volta
        self._acao_pendente = False
        await self._na_frente()
        return None

    def _e_item(self, el: r.Elemento) -> bool:
        """Item de mídia (cartão, faixa) de um pedido de mídia: o clique nele é decisivo."""
        tipos = r.ITENS_DE_MIDIA.get(self._origem or "", ())
        return (r.pedido_de_midia(self._pedido, self._herdada) and not r._isento(el.nome, self._origem)
                and (el.tipo in tipos or f"{el.tipo}/{el.papel}" in tipos))

    async def _passo_clicar(self, el: r.Elemento) -> Desfecho | None:
        host = r.host_de(self._endereco) if self._chrome and self._endereco else None
        decisao = r.classificar_clique(el, host, self._pedido, self._origem)
        if decisao.tipo == "parar":
            return await self._parou("esse clique não tem volta")
        if decisao.tipo == "forte":
            if desfecho := await self._frase_forte():
                return desfecho
        midia = r.pedido_de_midia(self._pedido, self._herdada)
        tocavel = midia and (self._e_item(el) or bool(_PLAY.search(_norm(el.nome))))
        if self.cancelado:
            return Desfecho("cancelado")
        await self._na_frente()
        ok = await self._b.clicar(self._hwnd, el, self._endereco)
        self._agir("clicar", ok)
        if not ok:
            if getattr(self._b, "coberto", False) is True:
                self._notas.append(NOTA_COBERTO)
            return None
        if self._e_item(el):
            self._item = " ".join(el.nome.replace("]", " ").split())[:RESUMO_ITEM_MAX]
        if midia and (tocando := await self._esperar_play(PLAY_ESPERA_S if tocavel else 0)):
            return await self._fim_tocou(tocando)
        return None

    async def _passo_tecla(self, tecla: str) -> Desfecho | None:
        if self._hwnd is None or not r.tecla_permitida(tecla):
            self._recusar("tecla pede janela aberta e um nome da lista de teclas")
            return None
        if self.cancelado:
            return Desfecho("cancelado")
        await self._na_frente()
        ok = await self._b.tecla(self._hwnd, tecla)
        self._agir("tecla", ok)
        midia = r.pedido_de_midia(self._pedido, self._herdada)
        if ok and midia and (tocando := await self._esperar_play(PLAY_ESPERA_S if tecla in TECLAS_DE_PLAY else 0)):
            return await self._fim_tocou(tocando)
        return None

    async def _passo_clicar_visual(self, descricao: str) -> Desfecho | None:
        """Degraus 2 e 3 da visão: o PC captura só esta janela, a visão aponta, regras_pc decide pelo rótulo e a sonda clica
        se a janela continua na frente e no mesmo lugar."""
        if self._hwnd is None or self._visao is None or not descricao:
            self._recusar("clicar_visual pede janela aberta e descrição do alvo (sem visão neste PC)")
            return None
        await self._na_frente()
        # relê e confere (bloqueio, login, aba trocada) no ato: a captura sai do PC e o usuário pode ter mudado de aba
        if desfecho := await self._ler():
            return desfecho
        olhar = await self._b.olhar(self._hwnd)
        alvo = await self._visao(descricao, olhar) if olhar is not None else None
        if self.cancelado:
            return Desfecho("cancelado")
        if alvo is None:
            self._agir("clicar_visual", False)
            self._notas.append(NOTA_NAO_ACHEI)
            return None
        host = r.host_de(self._endereco) if self._chrome and self._endereco else None
        midia = r.pedido_de_midia(self._pedido, self._herdada)  # o app aberto não conta como citado
        decisao = r.alvo_visual(alvo.rotulo, descricao, host, self._pedido, self._origem, midia)
        if decisao.tipo == "parar":
            return await self._parou("esse clique não tem volta")
        if decisao.tipo == "forte" and (desfecho := await self._frase_forte()):
            return desfecho
        if self.cancelado:
            return Desfecho("cancelado")
        await self._na_frente()
        ok = await self._b.clicar_ponto(self._hwnd, alvo.x, alvo.y, olhar.retangulo)
        self._agir("clicar_visual", ok)
        if ok and midia and (tocando := await self._esperar_play(PLAY_ESPERA_S)):
            return await self._fim_tocou(tocando)
        return None

    async def _frase_forte(self) -> Desfecho | None:
        """Enviar: o PC monta a pergunta com o que relê do campo real e só age com "pode enviar" dita na pergunta forte."""
        envio = await self._b.envio(self._hwnd)
        montar = self._montar_envio
        if montar is None:
            try:
                from src.conversa.pergunta import montar_pergunta_envio as montar
            except ImportError:
                return await self._parou("não sei confirmar esse envio")
        texto = montar(envio.destino, envio.texto, envio.anexos, envio.cc) if envio else None
        if texto is None:
            return await self._parou("não posso confirmar esse envio")
        resposta = await self._perguntar(texto, "forte")
        if resposta is None or not pode_enviar(resposta):
            return await self._parou("o senhor não confirmou o envio")
        if await self._b.envio(self._hwnd) != envio:  # o conteúdo mudou depois da pergunta: não age
            return await self._parou("o que seria enviado mudou")
        return None

    def _janela_lida(self) -> tuple[str, str]:
        """Título e texto da última leitura; só de app (no Chrome a página de login já para o laço em `_conferir`)."""
        u = self._ultima
        return (u.titulo, u.texto) if u is not None and not self._chrome else ("", "")

    async def _passo_texto(self, acao: str, el: r.Elemento, texto: str, modo: str | None = None) -> Desfecho | None:
        if acao == "buscar" and (not r.e_campo_de_busca(el, self._origem) or r.digitacao_bloqueada(el, *self._janela_lida())):
            self._recusar("esse controle não é um campo de busca")
            return None
        processo = ""
        if acao == "digitar" and not self._chrome and r.e_nome_de_editor(el.nome):  # só o editor de texto puro foge da regra de janela de login
            info = await self._b.info_janela(self._hwnd)
            processo = info.processo.lower().removesuffix(".exe") if info else ""
        if acao == "digitar" and (el.tipo not in ("Edit", "ComboBox") or r.digitacao_bloqueada(el, *self._janela_lida(), processo)):
            self._recusar("não digito nesse controle")
            return None
        if not await self._na_frente() and acao == "buscar":  # o Enter da busca só vai à janela da frente
            return await self._parou("a janela não está em primeiro plano")
        if self.cancelado:
            return Desfecho("cancelado")
        if acao == "buscar":
            ok = await self._b.buscar(self._hwnd, el, texto, self._endereco)
        else:  # digitar nunca apaga o que já está, a menos que o usuário tenha pedido (o modelo sozinho não decide apagar)
            apagar = modo == "substituir" and _PEDE_SUBSTITUIR.search(_norm(self._pedido)) is not None
            ok = await self._b.digitar(self._hwnd, el, texto, self._endereco, acrescentar=not apagar)
        self._agir(acao, ok)
        return None

    async def _passo_perguntar(self, texto: str, opcoes: list[str] | None = None) -> Desfecho | None:
        if not r.fala_permitida(texto, "perguntar"):
            return await self._parou("a pergunta pedia algo que não posso pedir")
        if r.pede_dado_tecnico(texto):  # decisão provisória (a revisar): 1ª vez é recusa, 2ª para
            self._pediu_dado += 1
            if self._pediu_dado > 1:
                return await self._parou("a pergunta pedia algo que não posso pedir")
            self._recusar("não peça id, link nem dado técnico ao usuário")
            return None
        if self._perguntas >= PERGUNTAS_MAX:
            return await self._parou("perguntei demais e não avancei")
        self._perguntas += 1
        self._passos += 1  # pergunta é passo: sem isso o modelo perguntava sem parar
        # as opções vêm do modelo que lê páginas: mesmos limites e filtro da pergunta; qualquer defeito = sem botões
        opcoes = tuple(o.strip() for o in opcoes or ())
        if not (2 <= len(opcoes) <= OPCOES_MAX and all(o and len(o) <= OPCAO_MAX_CARACTERES and r.fala_permitida(o, "perguntar")
                                                       for o in opcoes)):
            opcoes = ()
        resposta = await self._perguntar(texto, "livre", opcoes)  # livre orienta o laço, nunca autoriza ação sem volta
        if resposta is None:
            return await self._parou("não ouvi a resposta")
        self._respostas.append(resposta)
        self._historico.append("perguntei")
        self._notas.append(f"o usuário respondeu: {resposta}")
        return None

    # ---- fim do laço ----

    async def _passo_responder(self, texto: str) -> Desfecho | None:
        if not r.fala_permitida(texto, "responder"):
            self._recusas += 1
            if self._recusas > 1:
                return await self._parou("o resultado não passou nas regras de segurança")
            self._notas.append("resposta recusada pelo formato (número longo ou documento): reescreva sem eles")
            return None
        # mídia só vale com o sinal de play; o texto do modelo não prova nada. 14/11: num player, "está tocando" dito pelo
        # modelo também passa pelo sinal, mesmo que o pedido não tenha soado como mídia
        diz_que_toca = self._origem in r.ORIGENS_DE_PLAYER and _DIZ_QUE_TOCA.search(_norm(texto)) is not None
        if r.pedido_de_midia(self._pedido, self._herdada) or diz_que_toca:
            if tocando := await self._esperar_play(0):
                return await self._fim_tocou(tocando)
            await self._falar(FRASE_SEM_SINAL)
            return Desfecho("respondeu", FRASE_SEM_SINAL)
        await self._falar(texto)
        extra = await self._timer_do_pedido()
        await self._falar(extra)
        return Desfecho("respondeu", f"{texto} {extra}".strip())

    async def _timer_do_pedido(self) -> str:
        """Lê o timer da transcrição (nunca do modelo) e arma; devolve a frase do resultado ("" se não há timer)."""
        t = r.ler_timer(self._pedido)
        if t is None:
            return ""
        if t.ambiguo or not t.minutos:  # ali ele já vai dormir: não pergunta, não arma, avisa
            return "Não armei o timer, senhor: não entendi o tempo."
        try:
            armou = await self._timers.armar(t)
        except Exception as erro:
            log.warning("timer falhou: %s", type(erro).__name__)
            armou = False
        if not armou:
            return "Não consegui armar o timer, senhor."
        return f"Timer {'de desligar ' if t.desligar else ''}de {t.minutos} minutos armado, senhor."

    def _app_da_janela(self, midia: Midia) -> bool:
        app = midia.app.lower()
        if self._origem in r.APPS:
            return self._origem in app
        return "chrome" in app  # decisão provisória (a revisar): a prova 3 da Netflix no Chrome ainda está pendente

    def _comecou(self, midia: Midia) -> bool:
        """Tocando, do app da janela do pedido, e diferente do que já tocava antes do laço."""
        if not (midia.tocando and self._app_da_janela(midia)):
            return False
        return not any(b.app == midia.app and b.tocando and b.titulo == midia.titulo for b in self._base_midias)

    async def _no_player(self) -> bool:
        """Na origem com player (Netflix), só vale o play com a página nele; a prévia do modal também toca."""
        segmento = r.PLAYER.get(self._origem or "")
        if segmento is None:
            return True
        try:
            endereco = (await self._b.ler(self._hwnd)).endereco or ""
        except Exception as erro:
            log.warning("ler falhou: %s", type(erro).__name__)
            return False
        return segmento in urlsplit(endereco if "://" in endereco else "https://" + endereco).path.lower().split("/")

    async def _esperar_play(self, espera: float) -> Midia | None:
        fim = self._relogio() + espera
        while True:
            novas = [m for m in await self._b.midias() if self._comecou(m)]
            if novas and await self._no_player():
                return novas[0]
            if self._relogio() >= fim or self.cancelado:
                return None
            await self._esperar(PLAY_PASSO_S)

    @staticmethod
    def _sem_serie(midia: Midia, pagina: str = "") -> bool:
        """Título (da mídia e da aba) só de enchimento ("Netflix", "T1:E30", "Episódio 30"): não prova que tocou outra coisa."""
        return all(_SEM_SERIE.fullmatch(p) for p in r._palavras(f"{midia.titulo} {midia.artista} {pagina}"))

    async def _titulo_da_pagina(self) -> str:
        try:
            return (await self._b.ler(self._hwnd)).titulo or ""
        except Exception as erro:
            log.warning("ler falhou: %s", type(erro).__name__)
            return ""

    async def _titulo_confere(self, midia: Midia) -> tuple[bool, Midia]:
        """No player espera o título carregar (a sessão de mídia e a aba mostram primeiro "Netflix" ou só o episódio); se até lá
        só houver enchimento, não há prova de que tocou outra coisa. Fora do player (Spotify) confere na hora."""
        player = self._origem in r.PLAYER
        fim = self._relogio() + (TITULO_ESPERA_S if player else 0)
        while True:
            pagina = await self._titulo_da_pagina() if player else ""
            if self._titulo_bate(midia, pagina):
                return True, midia
            if self._relogio() >= fim or self.cancelado:
                return player and self._sem_serie(midia, pagina), midia
            await self._esperar(PLAY_PASSO_S)
            midia = next((m for m in await self._b.midias() if m.app == midia.app and m.tocando), midia)

    def _titulo_bate(self, midia: Midia, pagina: str = "") -> bool:
        tocando = set(r._palavras(f"{midia.titulo} {midia.artista} {pagina}"))
        titulo = set(r._palavras(midia.titulo))
        if any(set(a.split()) <= titulo for a in self._aprovados if a):  # palavras inteiras, nunca pedaço de palavra
            return True
        alvo = r.alvo_nomeado(self._pedido, self._origem or "")
        if alvo:
            return set(r._palavras(alvo)) <= tocando or r.casa_alvo(midia.titulo, self._pedido) >= r.LIMIAR_ALVO
        citados = r._citados_sem_alvo(self._pedido)  # sem alvo nomeado: confere só o que foi citado ("Kaluê")
        return not citados or r.casa_alguma(citados, tocando)

    async def _por_em_tela_cheia(self) -> None:
        """Série, filme ou vídeo que tocou vai para tela cheia (tecla f do player): Netflix sempre; YouTube menos música."""
        if self._hwnd is None or self._origem not in ("netflix", "youtube"):
            return
        if self._origem == "youtube" and _MUSICA.search(_norm(self._pedido)):
            return
        if await self._b.tela_cheia(self._hwnd) or self.cancelado:
            return
        await self._na_frente()
        await self._b.tecla(self._hwnd, "f")

    async def _jev_confirma(self, midia: Midia) -> bool:
        """O Jev julga se o que tocou é o pedido (sai só o pedido e o título, para a TypeSafe); sem chave ou na dúvida, False."""
        if self._escolher is None:
            return False
        partes = [f"Pedido anterior do usuário: {self._anterior}"] if self._anterior else []
        partes += [f"Pedido do usuário: {self._pedido}", f"Tocando: {midia.titulo} — {midia.artista}".rstrip(" —")]
        achou = await self._escolher("\n".join(partes), "O que está tocando é o que o usuário pediu?", ["sim", "não"])
        return achou is not None and achou[0] == 0 and achou[1] >= LIMIAR_JEV_TOCOU

    async def _fim_tocou(self, midia: Midia) -> Desfecho | None:
        """Sinal de play: sem o modelo, arma o timer pedido, fala, dorme e encerra. Tocou outra coisa: pausa e pergunta."""
        confere, midia = await self._titulo_confere(midia)  # `midia` volta com o título relido
        if self.cancelado:
            return Desfecho("cancelado")
        if not confere and not await self._jev_confirma(midia):
            # 14/11: pedido de correção ou mal transcrito não bate com o título; não pausa sozinho, pergunta tocando
            resposta = await self._perguntar(f"Tocou {midia.titulo[:RESUMO_ITEM_MAX]}, senhor. É isso?", "livre")
            if self.cancelado:
                return Desfecho("cancelado")
            if resposta is not None and resposta_do_que_tocou(resposta) == "nao":
                await self._b.pausar_midia(midia.app)
                self._base_midias = await self._b.midias()
                self._notas.append("tocou outra coisa e foi pausado: procure de novo")
                return None
        await self._por_em_tela_cheia()
        fala = " ".join(p for p in (f"Tocando {midia.titulo}, senhor.", await self._timer_do_pedido()) if p)
        await self._falar(fala)
        if not self.cancelado:
            await self._dormir()
        return Desfecho("tocou", fala)
