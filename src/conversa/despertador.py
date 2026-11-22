""""Hey JARVIS": openWakeWord sobre o áudio da janela e o portão que só deixa o áudio seguir com a conversa aberta.
Também acorda pelo nome ("groov", "acorda groov"...): Whisper pequeno na CPU, só para falas curtas (14/11)."""
import difflib
import re
import time
import unicodedata
from collections import deque
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from loguru import logger
from openwakeword.model import Model
from pipecat.frames.frames import Frame, InputAudioRawFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from src import config
from src.conversa.comandos import normalizar
from src.conversa.sessao import Estado, Sessao

BLOCO = 2 * 1280  # bytes: 1280 amostras de 16 kHz (80 ms), o passo do openWakeWord


class Despertador:
    def __init__(self, modelo: Path, limiar: float = 0.5):
        framework = "onnx" if modelo.suffix == ".onnx" else "tflite"
        self._modelo = Model(wakeword_models=[str(modelo)], inference_framework=framework)
        self._limiar = limiar
        self._resto = b""

    def ouvir(self, pcm16: bytes) -> bool:
        """pcm16: áudio mono de 16 kHz. True na detecção; o estado do modelo é zerado para não repetir."""
        self._resto += pcm16
        acordou = False
        while len(self._resto) >= BLOCO:
            bloco, self._resto = self._resto[:BLOCO], self._resto[BLOCO:]
            notas = self._modelo.predict(np.frombuffer(bloco, dtype=np.int16))
            acordou = acordou or bool(max(notas.values()) >= self._limiar)
        if acordou:
            self._modelo.reset()
            self._resto = b""
        return acordou


# sem espaços: o Whisper corta e junta as palavras do jeito dele ("Groovacordas", "Escreva o Acorda")
FRASES_DO_NOME = ("groov", "heygroov", "acordagroov", "groovacorda")  # + GROOV_FRASES_EXTRA (frases_do_nome())
PARECIDO = 0.8  # medido em 14/11 com o Kokoro: as frases ficaram >= 0,83; "acorda", "o grupo acordou" <= 0,71
_HEY = re.compile(r"^(?:hey|ei|e|a|oi|rei) groov\b")  # "E Groov", "A Groove": o Whisper engole o "hey"


def _chave(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", normalizar(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", _HEY.sub("hey groov", texto))


def frases_do_nome() -> tuple[str, ...]:
    """As frases fixas + as de GROOV_FRASES_EXTRA, no mesmo formato sem espaços."""
    extras = (_chave(f) for f in config.lista("GROOV_FRASES_EXTRA"))
    return FRASES_DO_NOME + tuple(f for f in extras if f and f not in FRASES_DO_NOME)


def e_chamado(texto: str, frases: tuple[str, ...] = FRASES_DO_NOME) -> bool:
    """A fala inteira parece uma das frases de acordar ("o groov é legal" não parece)."""
    chave = _chave(texto)
    return bool(chave) and max(difflib.SequenceMatcher(None, chave, f).ratio() for f in frases) >= PARECIDO


PASSO = 2 * 512  # bytes: 512 amostras de 16 kHz (32 ms), o passo do Silero
FIM_DA_FALA = 10  # passos de silêncio (~0,3 s) que fecham a frase
FALA_MAXIMA = int(2.5 / 0.032)  # passos; frase maior não é chamado e nem vai ao Whisper (poupa CPU)
PREVIA = 6  # passos guardados antes da voz, para o Whisper pegar o começo da palavra
MODELO_DO_NOME = "tiny"  # medido 14/11 na CPU: tiny ~0,3 s, small ~1,8 s; com o casamento aproximado acertam parecido
VOZ_MINIMA = 6  # passos com voz (~0,2 s): tosse e estalo não vão ao Whisper
SEM_FALA = 0.45  # no_speech_prob: ruído alucinado ficou >= 0,53 e fala real <= 0,33 (14/11, tiny com as hotwords)
LACUNA = 0.5  # s sem áudio: o portão parou de alimentar (conversando); a fala pela metade e o resultado velho caem


def _transcritor_padrao(hotwords: str) -> Callable[[bytes], str]:
    modelo = None

    def transcrever(pcm16: bytes) -> str:
        nonlocal modelo
        if modelo is None:  # carrega na thread: não atrasa o início do servidor
            from faster_whisper import WhisperModel
            modelo = WhisperModel(MODELO_DO_NOME, device="cpu", compute_type="int8")
        audio = np.frombuffer(pcm16, dtype=np.int16).astype(np.float32) / 32768
        # as hotwords dobram o acerto (12/12 contra 7/12 no Kokoro); a alucinação que elas trazem cai no SEM_FALA
        partes, _ = modelo.transcribe(audio, language="pt", beam_size=1, hotwords=hotwords,
                                      condition_on_previous_text=False, without_timestamps=True)
        return " ".join(p.text for p in partes if p.no_speech_prob < SEM_FALA)
    return transcrever


def _voz_padrao() -> Callable[[bytes], float]:
    from pipecat.audio.vad.silero import SileroVADAnalyzer
    vad = SileroVADAnalyzer()
    vad.set_sample_rate(16000)  # no construtor ele não vale até o set_sample_rate (o passo ficaria 256)
    return vad.voice_confidence


class OuvidoDoNome:
    """Mesma interface do Despertador. O VAD recorta cada fala; a curta vai ao Whisper numa thread e o resultado
    sai num ouvir() seguinte (20 ms depois), sem travar o portão. Tudo local.
    falando: o GROOV está falando; a fala que o pega (eco da voz dele dizendo o nome) não acorda."""

    def __init__(self, transcrever: Callable[[bytes], str] | None = None, voz: Callable[[bytes], float] | None = None,
                 executor=None, falando: Callable[[], bool] = lambda: False, relogio=time.monotonic):
        padrao = transcrever is None
        self._frases = frases_do_nome()
        palavras = {p.lower(): p for p in "Groov acorda".split()}  # sem repetir: "Groov acorda X", como medido em 14/11
        for frase in config.lista("GROOV_FRASES_EXTRA"):
            palavras.update({p.lower(): p for p in frase.split() if p.lower() not in palavras})
        self._transcrever = transcrever or _transcritor_padrao(" ".join(palavras.values()))
        self._voz = voz or _voz_padrao()
        self._executor = executor or ThreadPoolExecutor(1)
        self._falando = falando
        self._relogio = relogio
        self._ultimo = relogio()
        self._futuro = None
        self._zerar()
        if padrao:  # carrega o Whisper já, para o 1º "groov" da conexão não se perder na carga
            self._executor.submit(self._transcrever, bytes(2 * 1600))

    def _zerar(self) -> None:
        self._resto = b""
        self._previa: deque[bytes] = deque(maxlen=PREVIA)
        self._fala: bytearray | None = None
        self._passos = self._silencio = self._com_voz = 0
        self._longa = self._eco = False

    def _chamado(self, pcm16: bytes) -> bool:
        try:
            return e_chamado(self._transcrever(pcm16), self._frases)
        except Exception as erro:  # sem modelo ou erro do Whisper: só não acorda pelo nome; o Hey JARVIS segue
            logger.warning(f"despertador: nome falhou ({type(erro).__name__})")
            return False

    def _fechar(self) -> None:
        if not (self._longa or self._eco) and self._com_voz >= VOZ_MINIMA:
            if self._futuro is None:  # uma transcrição por vez
                self._futuro = self._executor.submit(self._chamado, bytes(self._fala))
            else:
                logger.info("despertador: fala ignorada (o Whisper ainda está na anterior)")
        self._fala = None
        self._previa.clear()

    def _passo(self, bloco: bytes) -> None:
        voz = self._voz(bloco) >= 0.5
        if self._fala is None:
            if not voz:
                self._previa.append(bloco)
                return
            self._fala, self._passos, self._silencio, self._com_voz = bytearray(b"".join(self._previa)), 0, 0, 0
            self._longa = self._eco = False
        self._passos += 1
        self._com_voz += voz
        self._eco = self._eco or self._falando()
        if self._passos > FALA_MAXIMA and not self._longa:
            self._longa, self._fala = True, bytearray()
        if not self._longa:
            self._fala += bloco
        self._silencio = 0 if voz else self._silencio + 1
        if self._silencio >= FIM_DA_FALA:
            self._fechar()

    def ouvir(self, pcm16: bytes) -> bool:
        agora = self._relogio()
        if agora - self._ultimo > LACUNA:
            self._zerar()
            self._futuro = None  # resultado de antes da conversa: não vale mais
        self._ultimo = agora
        self._resto += pcm16
        while len(self._resto) >= PASSO:
            bloco, self._resto = self._resto[:PASSO], self._resto[PASSO:]
            self._passo(bloco)
        if self._futuro is not None and self._futuro.done():
            futuro, self._futuro = self._futuro, None
            if futuro.result():
                logger.info("despertador: ouviu o nome")
                return True
        return False


class DespertadorDuplo:
    """"Hey JARVIS" ou o nome: os dois ouvem sempre (cada um fica em dia); qualquer um acorda."""

    def __init__(self, *despertadores):
        self._despertadores = despertadores

    def ouvir(self, pcm16: bytes) -> bool:
        return any([d.ouvir(pcm16) for d in self._despertadores])


class PortaoDoDespertador(FrameProcessor):
    """Dormindo, ocioso ou acordando, o áudio do microfone não passa adiante (nem Whisper nem VAD o veem);
    dormindo ou ocioso, ele alimenta o detector. O resto dos frames passa sempre."""

    def __init__(self, sessao: Sessao, despertador: Despertador, ao_acordar: Callable[[], Awaitable[None]],
                 relogio=time.monotonic, ao_voltar_a_ouvir: Callable[[], Awaitable[None]] | None = None):
        super().__init__()
        self._sessao = sessao
        self._despertador = despertador
        self._ao_acordar = ao_acordar
        self._relogio = relogio
        self._ao_voltar_a_ouvir = ao_voltar_a_ouvir  # sai do modo surdo e avisa a janela; None: só desliga a flag

    async def _sair_do_surdo(self) -> None:
        if self._ao_voltar_a_ouvir is not None:
            await self._ao_voltar_a_ouvir()
        self._sessao.surdo = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, InputAudioRawFrame) and self._sessao.surdo:
            # modo surdo: em nenhum estado o áudio segue (nem Whisper nem VAD); só o "Hey JARVIS" ou o nome (local) tiram dele
            # o eco da própria fala do GROOV não tira do surdo (revisão 14/11); o detector segue ouvindo para ficar em dia
            if self._despertador.ouvir(frame.audio) and not self._sessao.falando:
                logger.info("despertador: ouviu (sai do modo surdo)")
                await self._sair_do_surdo()
                if self._sessao.estado in (Estado.DORMINDO, Estado.OCIOSO) and self._sessao.pode_acordar(self._relogio()):
                    await self._ao_acordar()
            return
        if isinstance(frame, InputAudioRawFrame):
            # na pausa logo depois de dormir o detector segue ouvindo (estado em dia), mas a detecção é ignorada
            if self._sessao.estado in (Estado.DORMINDO, Estado.OCIOSO) and self._despertador.ouvir(frame.audio):
                pode = self._sessao.pode_acordar(self._relogio())
                logger.info(f"despertador: ouviu ({'acorda' if pode else 'na pausa, ignorado'})")
                if pode:
                    await self._ao_acordar()
            if self._sessao.estado is not Estado.CONVERSANDO:
                return
        await self.push_frame(frame, direction)
