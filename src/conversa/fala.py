"""Texto escrito -> texto falável: o XTTS lê símbolos ao pé da letra ("°C" vira "Ce", "." vira "ponto")."""
import re

NOME = "GROOV"
NOME_FALADO = "Gruv"  # como o TTS fala o nome
_URL = re.compile(r"https?://\S+")
_TROCAS = [
    (re.compile(rf"^\s*(?:{NOME}|jarvis)\s*:\s*", re.I), ""),  # o modelo às vezes assina a própria fala
    (re.compile(rf"\b{NOME}\b", re.I), NOME_FALADO),
    (re.compile(r"-(\d)(?=\s*[°º]\s*C?)"), r"menos \1"),
    (re.compile(r"\s*[°º]\s*[CcFf]?\b|\s*[°º]"), " graus"),
    (re.compile(r"\s*%"), " por cento"),
    (re.compile(r"\bkm/h\b"), "quilômetros por hora"),
    (re.compile(r"R\$\s*(\d+(?:[.,]\d+)*)"), r"\1 reais"),
    (re.compile(r"\s*&\s*"), " e "),
    (re.compile(r"[*_#`]+"), ""),
]


def para_fala(texto: str) -> str:
    texto = _URL.sub("", texto)
    for padrao, troca in _TROCAS:
        texto = padrao.sub(troca, texto)
    return re.sub(r"\s+([.,!?;:])", r"\1", re.sub(r"\s{2,}", " ", texto)).strip()
