"""Gravar e repetir (Fase 7): ao fim de um laço que tocou, guarda a sequência de passos; o mesmo pedido volta a rodar sem
o modelo. Os passos são guardados pelos campos do Elemento (nome, tipo, papel, ancestrais), nunca por id ou runtime_id,
então valem para qualquer sonda. O arquivo mora em privado/ porque a chave contém o que o usuário pediu.
Log: só contagens e tipos, nunca o pedido nem o texto de um passo."""
import json
import logging
import os
from pathlib import Path

from src.conversa.regras_pc import Elemento

log = logging.getLogger("groov.gravacao")

GRAVACAO_LIGADA = True  # False: o laço nunca grava nem repete
ARQUIVO_GRAVACOES = Path(__file__).resolve().parents[2] / "privado" / "gravacoes_pc.json"
GRAVACOES_MAX = 200  # passando disto, as mais antigas saem
ACOES_GRAVAVEIS = ("abrir_site", "abrir_app", "clicar", "buscar", "digitar", "rolar")  # perguntar/responder dependem do momento


def chave(pedido_normalizado: str, origem: str | None) -> str:
    return f"{pedido_normalizado}|{origem or ''}"


def ficha(el: Elemento) -> dict:
    return {"nome": el.nome, "tipo": el.tipo, "papel": el.papel, "ancestrais": list(el.ancestrais)}


def achar(f: dict, elementos) -> Elemento | None:
    """O único elemento da leitura com a ficha gravada; zero ou mais de um: None (volta ao modelo)."""
    achados = [e for e in elementos if ficha(e) == f]
    return achados[0] if len(achados) == 1 else None


class Gravacoes:
    def __init__(self, caminho: Path = ARQUIVO_GRAVACOES):
        self._caminho = caminho

    def _ler(self) -> dict:
        try:
            dados = json.loads(self._caminho.read_text(encoding="utf-8"))
            return dados if isinstance(dados, dict) else {}
        except (OSError, ValueError):
            return {}

    def buscar(self, k: str) -> list[dict] | None:
        passos = self._ler().get(k)
        if not isinstance(passos, list) or not passos:
            return None
        if not all(isinstance(p, dict) and isinstance(p.get("elemento", {}), dict) for p in passos):
            return None  # JSON válido de formato errado: como se não houvesse gravação
        return list(passos)

    def guardar(self, k: str, passos: list[dict]) -> None:
        dados = self._ler()
        dados.pop(k, None)
        dados[k] = passos
        self._gravar(dict(list(dados.items())[-GRAVACOES_MAX:]))

    def apagar(self, k: str) -> None:
        dados = self._ler()
        if dados.pop(k, None) is not None:
            self._gravar(dados)

    def _gravar(self, dados: dict) -> None:
        tmp = self._caminho.with_suffix(".tmp")
        try:
            self._caminho.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self._caminho)
        except OSError as erro:
            log.warning("gravação não salva: %s", type(erro).__name__)
