"""Perguntas do laço ao usuário (livre e frase forte). Sem pipecat. Vaga única: uma pergunta aberta por vez.
O prazo de resposta começa no fim da fala (`ao_terminar_fala`), com teto duro desde o pedido de falar; resposta que começou
antes do fim da fala + a margem (MARGEM_ECO_S) é eco e não conta. Na livre o eco se julga pelo conteúdo (palavras da própria fala), não só
pelo tempo. Log: só tipos, contagens e tempos, nunca o texto."""
import asyncio
import inspect
import logging
import re
from collections.abc import Awaitable, Callable

from src.conversa.comandos import pode_enviar
from src.conversa.laco import (FORTE_MAX_CARACTERES, FRASE_ANDAMENTO, MARGEM_ECO_LIVRE_S, MARGEM_ECO_S, PERGUNTA_TETO_S,
                               RESPOSTA_S)
from src.conversa.regras_pc import _casa_palavra, _palavras

log = logging.getLogger("groov.pergunta")

_FATIA_S = 0.05  # o relógio é injetado: espera em fatias curtas e reconfere o prazo
# com esquema/www, ou domínio/caminho sem esquema (decisão provisória (a revisar): domínio solto sem barra não é link;
# o último rótulo precisa ter letra, senão "R$ 1.000/mês" e "8.5/10" seriam trocados por "link para ...")
_LINK = re.compile(r"(?:https?://|www\.)\S+|(?<![\w.-])[\w-]+(?:\.[\w-]+)*\.(?=[\w-]*[a-z])[\w-]+/\S*", re.I)
_PONTA = ".,;:!?)\"'"
# Pergunta livre: o eco se julga pelo CONTEÚDO (palavras da própria fala do GROOV), o tempo só desempata. Constantes do critério:
ECO_PREFIXO_MIN = 2  # palavras da fala no começo do trecho para tratá-las como eco colado na resposta
ECO_RAZAO = 0.8  # fração das palavras do trecho que vêm da fala: acima disso o trecho inteiro é eco
ECO_FOLGA_S = 1.5  # sem palavra da fala, o trecho que começou até tanto ANTES do fim dela ainda é resposta ("sim" em cima do rabo)
_LIGACAO = frozenset({"o", "a", "os", "as", "de", "do", "da", "um", "uma", "e", "em", "no", "na", "que"})
# palavras que a pergunta fala mas também são a resposta ("diga sim ou não"): não provam eco, nem entram na razão
_NEUTRAS = frozenset({"sim", "nao", "ou", "diga"})


def _link_falado(m: re.Match) -> str:
    url = m.group(0).rstrip(_PONTA)
    cauda = m.group(0)[len(url):]
    autoridade = re.split(r"[/?#]", re.sub(r"^https?://", "", url, flags=re.I))[0]
    usuario, arroba, hostport = autoridade.rpartition("@")
    host = hostport.split(":")[0].lower().removeprefix("www.")
    falado = " ponto ".join(host.split("."))
    if arroba:  # usuário@host engana: fala o usuário e o "arroba" para o host verdadeiro ficar claro
        usuario = " dois pontos ".join(" ponto ".join(u.lower().split(".")) for u in usuario.split(":"))
        falado = f"{usuario} arroba {falado}"
    return "link para " + falado + cauda


def montar_pergunta_envio(destino: str, texto: str, anexos: int, cc: str) -> str | None:
    """O molde fixo da frase forte. `None` para texto longo, anexo ou Cc/Cco: nessa versão não se confirma por voz."""
    if len(texto) > FORTE_MAX_CARACTERES or anexos or cc:
        return None
    falado = _LINK.sub(_link_falado, texto.strip())
    return f"Vou enviar para {destino}: {falado}. Para confirmar, diga: pode enviar."


class Pergunta:
    def __init__(self, falar_literal: Callable[[str], Awaitable], falar: Callable[[str], Awaitable],
                 som_tocando: Callable[[], Awaitable[bool] | bool], relogio: Callable[[], float],
                 ao_mudar: Callable[[dict | None], Awaitable] | None = None):
        # ao_mudar: a pergunta para a janela (dict ao abrir, None ao fechar); a janela é enfeite, a falha dela é engolida aqui.
        # falar_literal: pergunta forte, sem passar pelo para_fala (links e sublinhados ficam). falar: pergunta livre.
        # Se falar/falar_literal devolver False, a fala foi descartada: a pergunta vira None.
        self._literal, self._falar, self._som, self._relogio = falar_literal, falar, som_tocando, relogio
        self._ao_mudar = ao_mudar
        self._aberta = False
        self._fut: asyncio.Future | None = None
        self._tipo = "livre"
        self._falou = False
        self._fim: float | None = None
        self._cortada = False
        self._som_visto = False
        self._fala: list[str] = []  # palavras da pergunta e da frase de andamento: o que o microfone pode ouvir de volta

    def ativa(self) -> bool:
        return self._aberta

    def ao_terminar_fala(self, agora: float) -> None:
        if self._aberta and self._falou:  # a última fala vale: a frase de andamento depois da pergunta também ecoa
            self._fim = agora

    def ao_comecar_a_falar(self) -> None:
        """Outra fala do GROOV (andamento) depois da pergunta: até ela acabar, tudo que se ouve é eco dela."""
        if self._aberta and self._falou:
            self._fim = None

    def fala_cortada(self, agora: float | None = None) -> None:
        """A fala foi interrompida: se vier o prazo sem resposta, repete uma vez. `agora`: onde ela terminou de fato."""
        if self._aberta:
            self._cortada = True
            if agora is not None and self._falou:
                self._fim = agora

    def responder_direto(self, texto: str) -> bool:
        """Clique ou texto digitado na livre aberta: é resposta, sem teste de eco (teclado e mouse não são eco). Na forte
        e sem pergunta aberta devolve False: a frase forte só vale por voz."""
        if not self._aberta or self._tipo != "livre":
            return False
        if not self._fut.done():
            self._fut.set_result(texto)
        return True

    def cancelar(self) -> None:
        if self._fut is not None and not self._fut.done():
            self._fut.set_result(None)

    def oferecer(self, texto: str, inicio_turno: float | None) -> bool:
        """True se havia pergunta aberta: a transcrição é consumida (não vai ao cérebro). Só vira resposta se o turno
        começou depois do fim da fala + margem (larga na forte, curta na livre); antes disso é o eco da própria pergunta.
        `inicio_turno` é o início do TRECHO DE ÁUDIO transcrito, não a chegada da transcrição: eco que chega tarde segue eco."""
        if not self._aberta:
            return False
        if inicio_turno is None:  # sem a marca do STT: só a livre aceita, pela chegada
            if self._tipo == "forte":
                log.info("resposta forte: eco")
                return True
            inicio_turno = self._relogio()
        if self._tipo == "livre" and not self._fut.done() and self._fim is not None:
            return self._oferecer_livre(texto, inicio_turno)
        if self._fut.done() or self._fim is None or inicio_turno < self._fim + (MARGEM_ECO_S if self._tipo == "forte" else MARGEM_ECO_LIVRE_S):
            log.info("resposta %s: eco", self._tipo)
            return True
        log.info("resposta %s: aceita", self._tipo)
        self._fut.set_result(texto)
        return True

    def _da_fala(self, palavra: str) -> bool:
        return palavra not in _NEUTRAS and self._na_pergunta(palavra)

    def _na_pergunta(self, palavra: str) -> bool:
        return any(_casa_palavra(palavra, f) for f in self._fala)

    def _oferecer_livre(self, texto: str, inicio: float) -> bool:
        """Pergunta livre com fim da fala conhecido. Decide pelo conteúdo: começo do trecho com palavras da fala = eco colado
        (o VAD juntou o rabo do GROOV com a resposta): tira e julga o resto; sobrou nada = eco. Sem eco no texto, só vale o tempo
        se o trecho começou bem no meio da fala. Log: só números."""
        palavras = _palavras(texto)
        no_prefixo = n = 0
        while n < len(palavras) and (self._da_fala(palavras[n]) or palavras[n] in _LIGACAO):
            no_prefixo += self._da_fala(palavras[n]) and palavras[n] not in _LIGACAO
            n += 1
        uteis = [w for w in palavras if w not in _LIGACAO | _NEUTRAS]  # a razão só conta palavras que dizem algo
        razao = sum(map(self._da_fala, uteis)) / len(uteis) if uteis else 0.0
        resto = palavras[n:] if no_prefixo >= ECO_PREFIXO_MIN else palavras
        if not resto:
            eco = True
        elif no_prefixo >= ECO_PREFIXO_MIN:
            eco = False
        elif len(uteis) >= ECO_PREFIXO_MIN and razao >= ECO_RAZAO:
            eco = True
        elif len(palavras) == 1 and self._na_pergunta(palavras[0]):  # "não" solto pode ser o rabo de "diga sim ou não": margem antiga
            eco = inicio < self._fim + MARGEM_ECO_LIVRE_S
        else:
            eco = inicio < self._fim - ECO_FOLGA_S
        log.info("resposta livre: %s ini=%+.2fs chegada=%+.2fs palavras=%d sobreposicao=%.2f", "eco" if eco else "aceita",
                 inicio - self._fim, self._relogio() - self._fim, len(palavras), razao)
        if not eco:
            self._fut.set_result(" ".join(resto) if resto is not palavras else texto)
        return True

    async def _dizer(self, texto: str) -> bool:
        self._fala = _palavras(f"{texto} {FRASE_ANDAMENTO}")
        self._falou, self._fim, self._cortada, self._som_visto = False, None, False, False
        ok = await (self._literal if self._tipo == "forte" else self._falar)(texto)
        self._falou = True
        return ok is not False

    def _prazo(self, pedido: float) -> float:
        teto = pedido + PERGUNTA_TETO_S
        return teto if self._fim is None else min(self._fim + RESPOSTA_S, teto)

    async def _mostrar(self, dados: dict | None) -> None:
        if self._ao_mudar is None:
            return
        try:
            await self._ao_mudar(dados)
        except Exception as erro:  # a janela é enfeite: nunca quebra a pergunta
            log.warning("pergunta na tela falhou (%s)", type(erro).__name__)

    async def perguntar(self, texto: str, tipo: str, opcoes: tuple[str, ...] = ()) -> str | None:
        if self._aberta:
            raise RuntimeError("já há uma pergunta aberta")
        self._aberta, self._tipo = True, tipo
        self._fut = asyncio.get_running_loop().create_future()
        try:
            await self._mostrar({"texto": texto, "opcoes": list(opcoes) if tipo == "livre" else [],
                                 "so_voz": tipo == "forte", "prazo_s": PERGUNTA_TETO_S})
            pedido = self._relogio()  # teto duro fixo no 1º pedido, vale também com repetição
            for repeticao in range(2):
                if not await self._dizer(texto):
                    return None
                while not self._fut.done() and self._relogio() < self._prazo(pedido):
                    await asyncio.wait([self._fut], timeout=_FATIA_S)
                    if self._tipo == "forte" and self._fim is not None and not self._som_visto:
                        self._som_visto = await self._som_agora()  # amostra durante a espera, não só na resposta
                if self._fut.done():
                    return await self._conferir(self._fut.result())
                if not (self._cortada and repeticao == 0 and self._relogio() < pedido + PERGUNTA_TETO_S):
                    log.info("resposta %s: tempo esgotado", tipo)
                    return None
            return None
        finally:
            self._aberta = False
            await self._mostrar(None)

    async def _conferir(self, resposta: str | None) -> str | None:
        if resposta is None or self._tipo != "forte":
            return resposta
        if not pode_enviar(resposta):
            return None
        if self._som_visto or await self._som_agora():  # som tocando pode ser alguém falando a frase: recusa
            log.info("frase forte recusada: som tocando")
            return None
        return resposta

    async def _som_agora(self) -> bool:
        som = self._som()
        return bool(await som if inspect.isawaitable(som) else som)
