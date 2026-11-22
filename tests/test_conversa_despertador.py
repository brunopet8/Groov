import asyncio
import wave
from pathlib import Path

import pytest

pytest.importorskip("pipecat")

from pipecat.frames.frames import InputAudioRawFrame, TextFrame
from pipecat.tests.utils import run_test

from src.conversa.despertador import Despertador, PortaoDoDespertador
from src.conversa.sessao import Sessao

RAIZ = Path(__file__).parent.parent
MODELO = RAIZ / "hermes" / "wake" / "hey_jarvis_v0.1.onnx"
FIXTURE = RAIZ / "tests" / "fixtures" / "hey_jarvis.wav"
precisa_modelo = pytest.mark.skipif(not MODELO.exists(), reason="modelo do Hey JARVIS ausente (hermes/wake/)")


@precisa_modelo
def test_despertador_ignora_silencio():
    assert Despertador(MODELO).ouvir(bytes(2 * 16000 * 3)) is False


@precisa_modelo
@pytest.mark.skipif(not FIXTURE.exists(), reason="rode tests/gerar_fixtures.py")
def test_despertador_ouve_hey_jarvis():
    with wave.open(str(FIXTURE)) as w:
        assert w.getframerate() == 16000 and w.getnchannels() == 1
        pcm = w.readframes(w.getnframes())
    despertador = Despertador(MODELO)
    bloco = 2 * 320  # 20 ms, como chega da janela
    assert any(despertador.ouvir(pcm[i:i + bloco]) for i in range(0, len(pcm), bloco))


class DespertadorFalso:
    def __init__(self, acorda):
        self.acorda, self.chamadas = acorda, 0

    def ouvir(self, pcm16):
        self.chamadas += 1
        return self.acorda


def audio():
    return InputAudioRawFrame(audio=bytes(640), sample_rate=16000, num_channels=1)


async def passa_pelo_portao(sessao, despertador, ao_acordar=None, relogio=None):
    chamadas = []

    async def acordar():
        chamadas.append(1)

    extra = {"relogio": relogio} if relogio else {}
    portao = PortaoDoDespertador(sessao, despertador, ao_acordar or acordar, **extra)
    saida, _ = await run_test(portao, frames_to_send=[audio(), TextFrame("oi")])
    return [type(f).__name__ for f in saida], chamadas


def test_portao_bloqueia_audio_dormindo_mas_deixa_o_resto():
    saida, _ = asyncio.run(passa_pelo_portao(Sessao(), DespertadorFalso(False)))
    assert saida == ["TextFrame"]


def test_portao_deixa_audio_conversando():
    sessao = Sessao()
    sessao.acordar(0)
    sessao.pronto(0)
    saida, _ = asyncio.run(passa_pelo_portao(sessao, DespertadorFalso(False)))
    assert saida == ["InputAudioRawFrame", "TextFrame"]


def test_portao_acorda_ao_detectar_e_ainda_bloqueia_o_audio():
    saida, chamadas = asyncio.run(passa_pelo_portao(Sessao(), DespertadorFalso(True)))
    assert saida == ["TextFrame"] and chamadas == [1]


def test_portao_ignora_deteccao_na_pausa_depois_de_dormir():
    """Logo depois de "tchau"/"vá embora", o próprio áudio da despedida não pode acordar o GROOV de novo."""
    sessao = Sessao()
    sessao.dormir(100)
    falso = DespertadorFalso(True)
    _, chamadas = asyncio.run(passa_pelo_portao(sessao, falso, relogio=lambda: 104))
    assert chamadas == [] and falso.chamadas == 1  # o detector segue ouvindo; só a detecção é ignorada
    _, chamadas = asyncio.run(passa_pelo_portao(sessao, DespertadorFalso(True), relogio=lambda: 105))
    assert chamadas == [1]


def test_portao_acordando_nao_consulta_o_despertador():
    sessao = Sessao()
    sessao.acordar(0)
    falso = DespertadorFalso(True)
    saida, chamadas = asyncio.run(passa_pelo_portao(sessao, falso))
    assert saida == ["TextFrame"] and chamadas == [] and falso.chamadas == 0


def test_portao_ocioso_acorda_ao_detectar_e_bloqueia_o_audio():
    sessao = Sessao()
    sessao.acordar(0)
    sessao.pronto(0)
    sessao.ociar()
    saida, chamadas = asyncio.run(passa_pelo_portao(sessao, DespertadorFalso(True)))
    assert saida == ["TextFrame"] and chamadas == [1]


def test_portao_ocioso_ignora_deteccao_na_pausa_do_tchau():
    sessao = Sessao()
    sessao.acordar(0)
    sessao.pronto(0)
    sessao.ociar(100)
    _, chamadas = asyncio.run(passa_pelo_portao(sessao, DespertadorFalso(True), relogio=lambda: 104))
    assert chamadas == []


# ---- modo surdo (14/11): o áudio não segue; só "Hey JARVIS" (ou o botão) volta ----

def _conversando_surdo():
    sessao = Sessao()
    sessao.acordar(0)
    sessao.pronto(0)
    sessao.surdo = True
    return sessao


def test_surdo_nao_passa_audio_conversando():
    sessao = _conversando_surdo()
    saida, chamadas = asyncio.run(passa_pelo_portao(sessao, DespertadorFalso(False)))
    assert saida == ["TextFrame"] and chamadas == [] and sessao.surdo is True


def test_surdo_hey_jarvis_volta_a_ouvir():
    sessao, voltas = _conversando_surdo(), []

    async def voltar():
        voltas.append(1)
        sessao.surdo = False

    async def cenario():
        portao = PortaoDoDespertador(sessao, DespertadorFalso(True), lambda: asyncio.sleep(0), ao_voltar_a_ouvir=voltar)
        saida, _ = await run_test(portao, frames_to_send=[audio()])
        return saida
    saida = asyncio.run(cenario())
    assert voltas == [1] and sessao.surdo is False and [type(f).__name__ for f in saida] == []


def test_surdo_dormindo_hey_jarvis_volta_e_acorda():
    sessao = Sessao()
    sessao.surdo = True
    saida, chamadas = asyncio.run(passa_pelo_portao(sessao, DespertadorFalso(True)))
    assert chamadas == [1] and sessao.surdo is False


def test_surdo_ignora_deteccao_enquanto_o_groov_fala():
    """Revisão 14/11: o eco da própria voz não tira do surdo."""
    sessao = _conversando_surdo()
    sessao.comecou_a_falar(0)
    saida, chamadas = asyncio.run(passa_pelo_portao(sessao, DespertadorFalso(True)))
    assert sessao.surdo is True and chamadas == []


# ---- acordar pelo nome (14/11): Whisper pequeno na CPU, ligado só por fala curta ----

from concurrent.futures import Future

from src.conversa.despertador import DespertadorDuplo, OuvidoDoNome, e_chamado, frases_do_nome


@pytest.mark.parametrize("texto", ["Groov.", "Hey, Groove!", "ei gruv", "Acorda, Groov.", "Groov, acorda!",
                                   "groove", "E Groov.", "Groovacordas", "Groves"])
def test_e_chamado_aceita_as_frases(texto):
    assert e_chamado(texto)


EXTRAS = ["Acorda, assistente.", "Assistente, acorda.", "acorda assistente", "Assistente acorda!"]


def test_frases_extras_so_valem_com_a_config(monkeypatch):
    assert frases_do_nome() == ("groov", "heygroov", "acordagroov", "groovacorda")
    assert not any(e_chamado(t, frases_do_nome()) for t in EXTRAS)
    monkeypatch.setenv("GROOV_FRASES_EXTRA", "acorda assistente, Assistente acorda")
    frases = frases_do_nome()
    assert frases[-2:] == ("acordaassistente", "assistenteacorda")
    assert all(e_chamado(t, frases) for t in EXTRAS)
    assert not any(e_chamado(t, frases) for t in ("assistente", "acorda", "o grupo acordou"))


def test_ouvido_guarda_as_frases_e_as_extras_vao_nas_hotwords(monkeypatch):
    import sys
    from types import SimpleNamespace

    vistos = []

    class Modelo:
        def __init__(self, *a, **k):
            pass

        def transcribe(self, audio, **k):
            vistos.append(k["hotwords"])
            return [SimpleNamespace(text="acorda assistente", no_speech_prob=0.0)], None

    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=Modelo))
    sem = OuvidoDoNome(voz=lambda b: 1.0 if any(b) else 0.0, executor=Imediato())
    monkeypatch.setenv("GROOV_FRASES_EXTRA", "acorda assistente")
    com = OuvidoDoNome(voz=lambda b: 1.0 if any(b) else 0.0, executor=Imediato())
    assert not _fala(sem, 20) and _fala(com, 20)
    assert set(vistos) == {"Groov acorda", "Groov acorda assistente"}  # palavras sem repetir: "Groov acorda X"


@pytest.mark.parametrize("texto", ["", "o groov é legal", "acorda", "assistente", "Obrigado.", "groov que horas são",
                                   "o grupo acordou", "grupo", "Jarvis, que horas são?", "Legendas pela comunidade Amara.org"])
def test_e_chamado_recusa_o_resto(texto):
    assert not e_chamado(texto)


class Imediato:
    """Executor que roda na hora, para o teste não depender de thread."""
    def __init__(self):
        self.vezes = 0

    def submit(self, fn, *args):
        self.vezes += 1
        futuro = Future()
        futuro.set_result(fn(*args))
        return futuro


VOZ, SILENCIO = b"\x01\x00" * 512, bytes(1024)  # um passo do VAD (512 amostras) cada


def _ouvido(texto="groov"):
    executor, ouvidos = Imediato(), []

    def transcrever(pcm):
        ouvidos.append(len(pcm))
        return texto
    ouvido = OuvidoDoNome(transcrever, voz=lambda bloco: 1.0 if any(bloco) else 0.0, executor=executor)
    return ouvido, executor, ouvidos


def _fala(ouvido, passos_de_voz):
    """Fala + silêncio que fecha a frase; devolve se algum passo acordou."""
    resultados = [ouvido.ouvir(VOZ) for _ in range(passos_de_voz)]
    resultados += [ouvido.ouvir(SILENCIO) for _ in range(15)]
    return any(resultados)


def test_ouvido_acorda_com_fala_curta_que_e_o_nome():
    ouvido, executor, _ = _ouvido("Groov.")
    assert _fala(ouvido, 20) and executor.vezes == 1


def test_ouvido_nao_acorda_com_outra_frase():
    ouvido, executor, _ = _ouvido("o groov é legal")
    assert not _fala(ouvido, 20) and executor.vezes == 1


def test_ouvido_fala_longa_nem_e_transcrita():
    ouvido, executor, _ = _ouvido("groov")
    assert not _fala(ouvido, 100) and executor.vezes == 0  # 100 x 32 ms = 3,2 s > 2,5 s


def test_ouvido_silencio_nao_transcreve():
    ouvido, executor, _ = _ouvido()
    assert not any(ouvido.ouvir(SILENCIO) for _ in range(50)) and executor.vezes == 0


def test_ouvido_aceita_blocos_de_20_ms():
    ouvido, executor, _ = _ouvido()
    fala = VOZ * 20 + SILENCIO * 15
    assert any(ouvido.ouvir(fala[i:i + 640]) for i in range(0, len(fala), 640)) and executor.vezes == 1


def test_ouvido_erro_na_transcricao_nao_acorda_nem_quebra():
    def falha(pcm):
        raise RuntimeError("modelo ausente")
    ouvido = OuvidoDoNome(falha, voz=lambda b: 1.0 if any(b) else 0.0, executor=Imediato())
    assert not _fala(ouvido, 20)
    assert not _fala(ouvido, 20)


def test_duplo_acorda_por_qualquer_um_e_alimenta_os_dois():
    a, b = DespertadorFalso(False), DespertadorFalso(True)
    assert DespertadorDuplo(a, b).ouvir(b"x") is True and a.chamadas == 1 and b.chamadas == 1
    assert DespertadorDuplo(DespertadorFalso(False), DespertadorFalso(False)).ouvir(b"x") is False


def _real(nome):
    caminho = RAIZ / "tests" / "fixtures" / nome
    if not caminho.exists():
        pytest.skip("rode tests/gerar_fixtures.py")
    with wave.open(str(caminho)) as w:
        pcm = w.readframes(w.getnframes())
    ouvido = OuvidoDoNome(executor=Imediato())  # Silero e Whisper small de verdade, na CPU
    pcm += bytes(2 * 16000)  # silêncio que fecha a frase
    return any(ouvido.ouvir(pcm[i:i + 640]) for i in range(0, len(pcm), 640))


def test_ouvido_real_acorda_com_acorda_groov():
    assert _real("acorda_groov.wav")


def test_ouvido_real_nao_acorda_com_que_horas_sao():
    assert not _real("jarvis_hora.wav")


def test_ouvido_fala_curtinha_tosse_nem_e_transcrita():
    ouvido, executor, _ = _ouvido("groov")
    assert not _fala(ouvido, 3) and executor.vezes == 0


def test_ouvido_eco_do_groov_falando_nao_acorda():
    falando = [True]
    ouvido = OuvidoDoNome(lambda pcm: "groov", voz=lambda b: 1.0 if any(b) else 0.0, executor=Imediato(),
                          falando=lambda: falando[0])
    assert not _fala(ouvido, 20)
    falando[0] = False
    assert _fala(ouvido, 20)


def test_ouvido_lacuna_da_conversa_descarta_fala_e_resultado_velhos():
    """Conversando, o portão não alimenta o ouvido; ao voltar a dormir, nada de antes pode acordar."""
    agora = [0.0]

    class Pendente(Imediato):
        def submit(self, fn, *args):
            self.vezes += 1
            return Future()  # nunca termina sozinho
    executor = Pendente()
    ouvido = OuvidoDoNome(lambda pcm: "groov", voz=lambda b: 1.0 if any(b) else 0.0, executor=executor,
                          relogio=lambda: agora[0])
    for _ in range(20):
        ouvido.ouvir(VOZ)
    for _ in range(15):
        ouvido.ouvir(SILENCIO)
    assert executor.vezes == 1
    velho = ouvido._futuro
    for _ in range(10):
        ouvido.ouvir(VOZ)  # fala pela metade quando a conversa abre
    agora[0] = 60.0
    velho.set_result(True)  # o resultado velho chega durante a conversa
    assert not ouvido.ouvir(SILENCIO * 15) and executor.vezes == 1
