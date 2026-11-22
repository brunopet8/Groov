"""Briefing do 1º "Hey JARVIS" do dia: data, tempo e mar, montados no PC por modelo fixo (sem cérebro, sem Claude).

Uma fonte só para os dois jeitos de falar: cada frase é uma lista de trechos (texto, chave). Com a voz pronta, o Qwen
lê o texto junto; com a voz ainda carregando, tocam os trechos gravados antes (hermes/voz/frases/<chave>.wav).
"""
import json
import math
import urllib.request
import unicodedata
import wave
from array import array
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from src.clima import CONDICOES, Mar, Tempo, mar_local

RAIZ = Path(__file__).resolve().parents[1]
PASTA_FRASES = RAIZ / "hermes" / "voz" / "frases"  # voz pessoal: fora do git, nunca publicar
TAXA = 24000  # o que o servidor de voz (Qwen) grava
PAUSA_S = 0.12
LIMIAR_SILENCIO = 300  # amostras 16-bit abaixo disso nas pontas são silêncio

Trecho = tuple[str, str]  # (texto, chave)
Frase = list[Trecho]
DEU_O_TEMPO: Trecho = ("Senhor, deu o tempo.", "deu_o_tempo")  # aviso do timer simples (src/conversa/timers.py)

DIAS = ("segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo")
MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro")
TEMPERATURAS = range(0, 46)
CHUVA_MIN = 20  # abaixo disso a frase da chuva sai
ONDA_MAX = 5.0
# (a partir de, faixa falada, chave): altura significativa, palpite para o usuário calibrar
FAIXAS_MAR = ((2.5, "muito grande", "muito_grande"), (1.5, "grande", "grande"), (1.0, "médio", "medio"),
              (0.5, "pequeno", "pequeno"), (0.0, "flat", "flat"))
_ALTURAS = {0.5: "meio metro", 1.0: "um metro", 1.5: "um metro e meio", 2.0: "dois metros",
            2.5: "dois metros e meio", 3.0: "três metros", 3.5: "três metros e meio", 4.0: "quatro metros",
            4.5: "quatro metros e meio", 5.0: "cinco metros"}


def _chave(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().replace(" ", "_")


_SAUDACOES = {"dia": "Bom dia, senhor.", "tarde": "Boa tarde, senhor.", "noite": "Boa noite, senhor."}


def _saud(periodo: str) -> Trecho:
    return _SAUDACOES[periodo], f"saud_{periodo}"


def saudacao(agora: datetime) -> Trecho:
    """Mesmos períodos do som de início antigo: dia 5–12 h, tarde 12–18 h, noite no resto."""
    return _saud("dia" if 5 <= agora.hour < 12 else "tarde" if 12 <= agora.hour < 18 else "noite")


def _dia(semana: int) -> Trecho:
    return f"Hoje é {DIAS[semana]},", f"dia_{semana}"


def _data(dia: int) -> Trecho:
    return f"{dia} de", f"data_{dia}"


def _mes(mes: int) -> Trecho:
    return f"{MESES[mes - 1]}.", f"mes_{mes}"


def _faz(t: int) -> Trecho:
    return f"Faz {t} graus,", f"faz_{t}"


def _cond(condicao: str) -> Trecho:
    return f"{condicao},", f"cond_{_chave(condicao)}"


def _max(t: int) -> Trecho:
    return f"máxima de {t}", f"max_{t}"


def _min(t: int) -> Trecho:
    return f"e mínima de {t}.", f"min_{t}"


def _chuva(p: int) -> Trecho:
    return f"{p} por cento de chance de chuva.", f"chuva_{p}"


def _mar(faixa: str, chave: str, lugar: str) -> Trecho:
    # a chave não leva o lugar: trocar GROOV_MAR pede regravar as frases (scripts/gerar_frases.py)
    return f"O mar em {lugar} está {faixa},", f"mar_{chave}"


def _onda(altura: float) -> Trecho:
    return f"com ondas de {_ALTURAS[altura]}.", f"onda_{round(altura * 10)}"


def _meio_metro(altura: float) -> float:
    return max(0.5, math.floor(altura * 2 + 0.5) / 2)


def _faixa(altura: float) -> tuple[str, str]:
    return next((falada, chave) for desde, falada, chave in FAIXAS_MAR if altura >= desde)


def descrever_mar(altura: float) -> tuple[str, str] | None:
    """(faixa falada, altura falada arredondada a meio metro); None acima de ONDA_MAX (dado estranho: não fala)."""
    if not 0 <= altura <= ONDA_MAX:
        return None
    return _faixa(altura)[0], _ALTURAS[min(_meio_metro(altura), ONDA_MAX)]


def montar_briefing(agora: datetime, tempo: Tempo | None, mar: Mar | None) -> list[Frase]:
    """Frase 1 (data) sempre; tempo, chuva e mar só com dado válido. Valor fora da faixa tira a frase inteira."""
    frases: list[Frase] = [[_dia(agora.weekday()), _data(agora.day), _mes(agora.month)]]
    if tempo and all(t in TEMPERATURAS for t in (tempo.temperatura, tempo.maxima, tempo.minima)):
        frase = [_faz(tempo.temperatura)]
        if tempo.condicao:
            frase.append(_cond(tempo.condicao))
        frases.append([*frase, _max(tempo.maxima), _min(tempo.minima)])
        if tempo.chuva >= CHUVA_MIN:
            frases.append([_chuva(min(100, math.floor(tempo.chuva / 10 + 0.5) * 10))])
    if mar and mar.lugar and descrever_mar(mar.altura):
        faixa, chave = _faixa(mar.altura)
        frases.append([_mar(faixa, chave, mar.lugar), _onda(min(_meio_metro(mar.altura), ONDA_MAX))])
    return frases


def frases_do_inicio(agora: datetime, com_briefing: bool, tempo: Tempo | None, mar: Mar | None) -> list[Frase]:
    """Fala do áudio de início: a saudação sempre; o briefing só no 1º Hey JARVIS desde que o servidor ligou."""
    return [[saudacao(agora)], *(montar_briefing(agora, tempo, mar) if com_briefing else [])]


def texto_falado(frases: list[Frase]) -> str:
    return " ".join(texto for frase in frases for texto, _ in frase)


def catalogo() -> dict[str, str]:
    """Todo trecho que montar_briefing pode pedir: é o que scripts/gerar_frases.py grava com a voz do GROOV."""
    praia = mar_local()
    trechos = [*(_saud(p) for p in _SAUDACOES), *(_dia(d) for d in range(7)), *(_data(d) for d in range(1, 32)), *(_mes(m) for m in range(1, 13)),
               *(f(t) for f in (_faz, _max, _min) for t in TEMPERATURAS),
               *(_cond(c) for c in sorted(set(CONDICOES.values()))),
               *(_chuva(p) for p in range(CHUVA_MIN, 101, 10)),
               *(_mar(falada, chave, praia[0]) for _, falada, chave in FAIXAS_MAR if praia), *(_onda(a) for a in _ALTURAS),
               DEU_O_TEMPO]
    return {chave: texto for texto, chave in trechos}


def _ler_trecho(arquivo: Path) -> array | None:
    """Amostras sem o silêncio das pontas; None se faltar ou não for mono 16-bit 24 kHz (tocaria na altura errada)."""
    try:
        with wave.open(str(arquivo)) as w:
            if (w.getnchannels(), w.getsampwidth(), w.getframerate()) != (1, 2, TAXA):
                return None
            amostras = array("h", w.readframes(w.getnframes()))
    except (OSError, EOFError, ValueError, wave.Error):  # ValueError: arquivo cortado no meio de uma amostra
        return None
    sons = [i for i, a in enumerate(amostras) if abs(a) >= LIMIAR_SILENCIO]
    return amostras[sons[0]:sons[-1] + 1] if sons else None


def montar_audio(frases: list[Frase], pasta: Path = PASTA_FRASES) -> bytes | None:
    """PCM 16-bit mono 24 kHz da fala emendada dos trechos gravados. Frase com trecho faltando sai inteira
    (nunca meia frase); None só quando nenhuma frase pôde ser montada."""
    pausa = array("h", [0] * round(PAUSA_S * TAXA))
    partes: list[array] = []
    for frase in frases:
        trechos = [_ler_trecho(pasta / f"{chave}.wav") for _, chave in frase]
        if all(t is not None for t in trechos):
            partes.extend(trechos)
    if not partes:
        return None
    audio = array("h")
    for i, parte in enumerate(partes):
        if i:
            audio.extend(pausa)
        audio.extend(parte)
    return audio.tobytes()


URL_VOZ = "http://127.0.0.1:8765/v1/audio/speech"


def sintetizar(texto: str, abrir=urllib.request.urlopen, timeout: float = 60) -> bytes | None:
    """WAV 24 kHz da voz do GROOV pelo servidor local; None se ele estiver fora do ar ou falhar."""
    pedido = urllib.request.Request(
        URL_VOZ, method="POST", data=json.dumps({"input": texto, "response_format": "wav"}).encode(),
        headers={"Authorization": "Bearer local", "Content-Type": "application/json"})
    try:
        with abrir(pedido, timeout=timeout) as resposta:
            return resposta.read()
    except OSError:  # URLError, HTTPError (500 do servidor) e timeout são OSError
        return None


def gerar_banco(falar: Callable[[str], bytes], pasta: Path = PASTA_FRASES,
                trechos: dict[str, str] | None = None) -> int:
    """Grava <chave>.wav de cada trecho com falar(texto) -> WAV; pula o que já existe. Devolve quantos gravou."""
    pasta.mkdir(parents=True, exist_ok=True)
    feitos = 0
    for chave, texto in (catalogo() if trechos is None else trechos).items():
        arquivo = pasta / f"{chave}.wav"
        if not arquivo.exists():
            arquivo.write_bytes(falar(texto))
            feitos += 1
    return feitos
