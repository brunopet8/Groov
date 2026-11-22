"""Chats do Claude Code do usuário (`~/.claude/projects/*/*.jsonl`), lidos no PC para o painel PROJETOS. Nada vai a log."""
import json
import re
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
DIA = 86400.0
JANELA_LISTA = 30 * DIA
JANELA_CONTA = 7 * DIA
CHATS_MAX = 30
TITULO_MAX = 80
TEXTO_MAX = 2000
LINHA_MAX = 200_000  # bytes; acima disso é anexo ou saída de ferramenta
FIM_DO_CHAT = 8_000_000  # bytes lidos do fim de um chat grande para mostrar as últimas mensagens


@dataclass
class Chat:
    id: str
    titulo: str
    atualizado: float
    prompts_7d: int
    pasta: Path | None


@dataclass
class Workspace:
    nome: str
    pasta: Path | None
    prompts_7d: int
    atualizado: float
    chats: list[Chat] = field(default_factory=list)


@dataclass
class _Leitura:
    titulo: str
    prompts: list[float]  # horários (epoch) de cada prompt
    cwd: str | None


_CACHE: dict[Path, tuple[float, bool, _Leitura]] = {}  # uma entrada por arquivo: a leitura nova substitui a velha


def valido(id_: str) -> bool:
    return isinstance(id_, str) and bool(ID.fullmatch(id_))


def _prompt(e: dict) -> str | None:
    """O texto de um prompt do usuário, ou None (resultado de ferramenta, comando, aviso do sistema, subagente)."""
    if e.get("type") != "user" or e.get("isSidechain") or e.get("isMeta"):
        return None
    texto = (e.get("message") or {}).get("content")
    if not isinstance(texto, str) or not texto.strip() or texto.lstrip().startswith("<"):
        return None
    return texto


def _quando(e: dict) -> float | None:
    try:
        return datetime.fromisoformat(e["timestamp"]).timestamp()
    except (KeyError, TypeError, ValueError):
        return None


def _linhas(arquivo: Path, marcas: tuple[str, ...], ultimos: int | None = None):
    marcas_b = tuple(m.encode() for m in marcas)
    with open(arquivo, "rb") as f:
        if ultimos is not None and (tamanho := f.seek(0, 2)) > ultimos:  # chat gigante: só o fim
            f.seek(tamanho - ultimos)
            f.readline()  # linha cortada pela metade
        else:
            f.seek(0)
        for linha in f:
            # filtro barato antes do json (o histórico tem centenas de MB e o json segura o GIL): resultado de
            # ferramenta e linhas gigantes nunca são prompt nem fala
            if len(linha) > LINHA_MAX or b'"tool_result"' in linha or not any(m in linha for m in marcas_b):
                continue
            try:
                e = json.loads(linha.decode("utf-8", "replace"))
            except ValueError:
                continue
            if isinstance(e, dict):
                yield e


def _ler(arquivo: Path, inteiro: bool = True) -> _Leitura:
    titulo, prompts, cwds = "", [], Counter()
    for e in _linhas(arquivo, ('"type":"user"', '"type": "user"')):
        texto = _prompt(e)
        if texto is None:
            continue
        if isinstance(e.get("cwd"), str):
            cwds[e["cwd"]] += 1
        titulo = titulo or " ".join(texto.split())[:TITULO_MAX]
        if (t := _quando(e)) is not None:
            prompts.append(t)
        if not inteiro:  # arquivo velho: só o título e a pasta
            break
    return _Leitura(titulo, prompts, cwds.most_common(1)[0][0] if cwds else None)


def _leitura(arquivo: Path, mtime: float, inteiro: bool) -> _Leitura:
    guardado = _CACHE.get(arquivo)
    if guardado and guardado[0] == mtime and (guardado[1] or not inteiro):
        return guardado[2]
    lido = _ler(arquivo) if inteiro else _ler(arquivo, False)
    _CACHE[arquivo] = (mtime, inteiro, lido)
    return lido


def listar(projetos: Path, agora: float) -> list[Workspace]:
    """Workspaces com chats alterados nos últimos 30 dias, o mais novo primeiro."""
    juntos: dict[str, Workspace] = {}
    try:
        pastas = [p for p in projetos.iterdir() if p.is_dir()]
    except OSError:
        return []
    for pasta in pastas:
        chats, cwds = [], Counter()
        try:
            arquivos = [(a, a.stat().st_mtime) for a in pasta.glob("*.jsonl")]
        except OSError:
            continue
        for arquivo, mtime in arquivos:
            if not valido(arquivo.stem) or agora - mtime > JANELA_LISTA:
                continue
            try:
                lido = _leitura(arquivo, mtime, inteiro=agora - mtime <= JANELA_CONTA)
            except OSError:
                continue
            if lido.cwd:
                cwds[lido.cwd] += 1
            conta = sum(1 for t in lido.prompts if agora - t <= JANELA_CONTA)
            chats.append(Chat(arquivo.stem, lido.titulo or "(sem prompt)", mtime, conta,
                              Path(lido.cwd) if lido.cwd and Path(lido.cwd).is_dir() else None))
        cwd = cwds.most_common(1)[0][0] if cwds else None
        if not chats or (cwd and _temporaria(cwd)):  # pasta temporária: sessões do próprio GROOV e de testes
            continue
        chave = cwd.lower() if cwd else pasta.name
        ws = juntos.setdefault(chave, Workspace(Path(cwd).name if cwd else pasta.name,
                                                Path(cwd) if cwd and Path(cwd).is_dir() else None, 0, 0.0))
        ws.chats.extend(chats)
    for ws in juntos.values():  # o mesmo cwd pode ter mais de uma pasta de projeto (maiúsculas, caminhos antigos)
        ws.chats.sort(key=lambda c: c.atualizado, reverse=True)
        ws.prompts_7d, ws.atualizado, ws.chats = sum(c.prompts_7d for c in ws.chats), ws.chats[0].atualizado, ws.chats[:CHATS_MAX]
    return sorted(juntos.values(), key=lambda w: w.atualizado, reverse=True)


def _temporaria(cwd: str) -> bool:
    return Path(cwd).resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())


def achar(projetos: Path, id_: str) -> Path | None:
    if not valido(id_):
        return None
    for arquivo in projetos.glob(f"*/{id_}.jsonl"):
        return arquivo
    return None


def pasta(arquivo: Path) -> Path | None:
    """A pasta (cwd) do chat, se ainda existir."""
    cwd = _ler(arquivo, False).cwd
    return Path(cwd) if cwd and Path(cwd).is_dir() else None


def mensagens(arquivo: Path, limite: int = 50) -> list[dict]:
    """As últimas mensagens do chat: você, Claude e o nome de cada ferramenta usada."""
    saida = []
    for e in _linhas(arquivo, ('"type":"user"', '"type": "user"', '"type":"assistant"', '"type": "assistant"'), FIM_DO_CHAT):
        if e.get("isSidechain"):
            continue
        if (texto := _prompt(e)) is not None:
            saida.append({"quem": "voce", "texto": texto[:TEXTO_MAX]})
        elif e.get("type") == "assistant":
            for bloco in (e.get("message") or {}).get("content") or []:
                if not isinstance(bloco, dict):
                    continue
                if bloco.get("type") == "text" and str(bloco.get("text", "")).strip():
                    saida.append({"quem": "claude", "texto": str(bloco["text"])[:TEXTO_MAX]})
                elif bloco.get("type") == "tool_use":
                    saida.append({"quem": "ferramenta", "texto": str(bloco.get("name", "?"))[:80]})
    return saida[-limite:]


def para_janela(workspaces: list[Workspace]) -> list[dict]:
    return [{"nome": w.nome, "pasta": str(w.pasta) if w.pasta else None, "prompts_7d": w.prompts_7d,
             "atualizado": w.atualizado,
             "chats": [{"id": c.id, "titulo": c.titulo, "atualizado": c.atualizado, "prompts_7d": c.prompts_7d}
                       for c in w.chats]} for w in workspaces]
