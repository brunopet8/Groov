import asyncio
import base64
import json
import struct
import sys
import zlib

from src.conversa import visao
from src.conversa.pc import LinhaOcr, Olhar
from src.conversa.visao import Alvo, VisaoClaude, achar_alvo


def _png(w: int, h: int) -> bytes:
    """PNG mínimo válido (só o cabeçalho importa para o tamanho)."""
    def bloco(tipo, dados):
        return struct.pack(">I", len(dados)) + tipo + dados + struct.pack(">I", zlib.crc32(tipo + dados))
    linha = b"\x00" + b"\x00\x00\x00" * w
    return (b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + bloco(b"IDAT", zlib.compress(linha * h)) + bloco(b"IEND", b""))


LINHAS = (LinhaOcr("Início", (0, 0, 50, 20)), LinhaOcr("Pular anúncio", (700, 500, 100, 30)))


def _olhar(linhas=LINHAS, escala=1.0) -> Olhar:
    return Olhar((0, 0, 1600, 1000), linhas, _png(4, 4), escala)


def _escolher(resultado, vistos=None):
    async def f(estado, instrucao, opcoes):
        if vistos is not None:
            vistos.append(opcoes)
        return resultado
    return f


def _ver(resultado, chamadas=None):
    async def f(png, descricao):
        if chamadas is not None:
            chamadas.append(descricao)
        return resultado
    return f


def test_degrau2_acha_pelo_ocr():
    chamadas = []
    # o índice é da lista enviada ao Jev, que põe "Pular anúncio" primeiro
    alvo = asyncio.run(achar_alvo("botão pular anúncio", _olhar(), _escolher((0, 0.9)), _ver(None, chamadas)))
    assert alvo == Alvo(750, 515, "Pular anúncio", 2) and chamadas == []


def test_degrau2_poe_o_parecido_primeiro():
    vistos = []
    asyncio.run(achar_alvo("pular anúncio", _olhar(), _escolher((0, 0.9), vistos), _ver(None)))
    assert vistos[0][0] == "Pular anúncio"


def test_degrau2_incerto_vai_ao_3():
    alvo = asyncio.run(achar_alvo("centro do vídeo", _olhar(escala=0.5), _escolher((1, 0.5)), _ver((400, 300, "vídeo"))))
    assert alvo == Alvo(800, 600, "vídeo", 3)


def test_sem_linhas_vai_ao_3():
    alvo = asyncio.run(achar_alvo("x", _olhar(linhas=()), _escolher((0, 0.99)), _ver((10, 10, ""))))
    assert alvo == Alvo(10, 10, "", 3)


def test_sem_escolher_vai_ao_3():
    assert asyncio.run(achar_alvo("x", _olhar(), None, _ver((10, 10, "a")))) == Alvo(10, 10, "a", 3)


def test_sem_nada_e_none():
    assert asyncio.run(achar_alvo("x", _olhar(), _escolher(None), None)) is None


def test_ponto_fora_e_none():
    assert asyncio.run(achar_alvo("x", _olhar(linhas=()), None, _ver((5000, 5000, "x")))) is None


# --- VisaoClaude: um claude one-shot com a imagem no stream-json ---

def _falso_claude(resultado: str) -> list[str]:
    """Script que confere a 1ª linha do stdin (user com bloco image base64 + texto) e devolve um `result` em stream-json."""
    codigo = (
        "import sys,json\n"
        "m=json.loads(sys.stdin.buffer.readline())\n"
        "c=m['message']['content']\n"
        "ok=m['type']=='user' and c[0]['type']=='image' and c[0]['source']['media_type']=='image/png' and c[1]['type']=='text'\n"
        f"r={resultado!r} if ok else 'sem imagem'\n"
        "print(json.dumps({'type':'system'}))\n"
        "print(json.dumps({'type':'result','is_error':False,'result':r}))\n")
    return [sys.executable, "-c", codigo]


def _visao(resultado: str) -> VisaoClaude:
    return VisaoClaude(achar=lambda: "claude", montar=lambda caminho: _falso_claude(resultado))


def test_visao_claude_monta_imagem_e_le_ponto():
    assert asyncio.run(_visao('{"x": 2, "y": 3, "rotulo": "Arquivo"}')(_png(4, 4), "menu Arquivo")) == (2, 3, "Arquivo")


def test_visao_claude_json_torto_e_none():
    assert asyncio.run(_visao("não sei")(_png(4, 4), "x")) is None


def test_visao_claude_nulls_e_none():
    assert asyncio.run(_visao('{"x": null, "y": null, "rotulo": ""}')(_png(4, 4), "x")) is None


def test_visao_claude_fora_da_imagem_e_none():
    assert asyncio.run(_visao('{"x": 99, "y": 1, "rotulo": ""}')(_png(4, 4), "x")) is None


def test_visao_claude_sem_claude_e_none():
    assert asyncio.run(VisaoClaude(achar=lambda: None)(_png(4, 4), "x")) is None


def test_comando_visao_sem_ferramentas_nem_sessao():
    c = visao.comando_visao("claude")
    assert c[c.index("--tools") + 1] == "" and "--no-session-persistence" in c and c[c.index("--model") + 1] == "haiku"
    assert "--input-format" in c and c[c.index("--input-format") + 1] == "stream-json"


def test_mensagem_leva_imagem_base64():
    m = visao.mensagem(b"PNG", "alvo", 4, 4)
    bloco = m["message"]["content"][0]
    assert base64.b64decode(bloco["source"]["data"]) == b"PNG" and "alvo" in m["message"]["content"][1]["text"]
    json.dumps(m)
