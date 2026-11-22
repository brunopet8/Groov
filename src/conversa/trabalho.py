"""Nível 3: o Claude Code (`claude -p`, Sonnet) trabalha em segundo plano num workspace do usuário. Lê, pesquisa na web,
roda skills e edita só dentro do workspace; comandos só os liberados no settings do próprio workspace. O resultado inteiro volta para o vault; o resumo é falado."""
import asyncio
import json
import subprocess
from pathlib import Path

from src import config
from src.conversa.ajudante import (CANCELADA, CHAVES_DOS_MODELOS, ESTOUROU, FALHOU, SEM_JANELA, VAZIO, _matar,
                                   ambiente_sem, resumir)
from src.conversa.cerebro_pc import achar_claude

TETO_S = 900.0
WORKSPACES_MAX = 200
# provado em 13/11 (claude 2.1.314, modo default em -p): rm, mkdir, python e PowerShell bloqueados; escrita fora do
# workspace bloqueada. Edit(./**) cobre Edit e Write só na pasta. Sem o settings do usuário: comandos só os do workspace.
FERRAMENTAS = "Read,Glob,Grep,WebSearch,WebFetch,Skill,Edit(./**)"
INSTRUCAO = ("Você é o GROOV, assistente do usuário, fazendo um trabalho em segundo plano nesta pasta. Faça o pedido abaixo "
             "por inteiro. Responda em português. Termine com uma última linha começando com 'RESUMO:' e até 2 frases "
             "curtas, sem markdown, para serem faladas em voz alta.")


def _cwd(arquivo: Path) -> str | None:
    with open(arquivo, encoding="utf-8", errors="replace") as f:
        for _, linha in zip(range(50), f):
            try:
                cwd = json.loads(linha).get("cwd")
            except (ValueError, AttributeError):
                continue
            if isinstance(cwd, str):
                return cwd
    return None


def fixos_do_usuario(raiz_vault: Path) -> dict[str, Path]:
    """O vault + as pastas de GROOV_WORKSPACES_EXTRA (vírgula), pelo nome da pasta."""
    return {"Groov-vault": raiz_vault} | {Path(p).name: Path(p) for p in config.lista("GROOV_WORKSPACES_EXTRA")}


def listar_workspaces(projetos: Path, fixos: dict[str, Path]) -> dict[str, Path]:
    """Os fixos primeiro; depois cada pasta onde o usuário já usou o Claude Code (o `cwd` da sessão mais nova)."""
    ws = dict(fixos)
    try:
        pastas = sorted(p for p in projetos.iterdir() if p.is_dir())
    except OSError:
        return ws
    for pasta in pastas:
        if len(ws) >= WORKSPACES_MAX:
            break
        try:
            sessoes = sorted(pasta.glob("*.jsonl"), key=lambda a: a.stat().st_mtime, reverse=True)
            cwd = _cwd(sessoes[0]) if sessoes else None
        except OSError:
            continue
        if cwd and Path(cwd).is_dir() and Path(cwd) not in ws.values():
            ws.setdefault(Path(cwd).name, Path(cwd))
    return ws


def pasta_do_workspace(nome: str | None, ws: dict[str, Path], padrao: Path) -> Path:
    return ws.get(nome, padrao) if nome else padrao


def comando_trabalho(caminho: str, pedido: str) -> list[str]:
    return [caminho, "-p", f"{INSTRUCAO}\n\nPedido: {pedido}", "--model", "sonnet", "--permission-mode", "default",
            "--setting-sources", "project,local", "--allowedTools", FERRAMENTAS, "--output-format", "text"]


def comando_retomar(caminho: str, id_: str, prompt: str) -> list[str]:
    """Um prompt do usuário num chat existente (painel PROJETOS), com as permissões do nível 3."""
    # o prompt depois de "--": texto começando com "--" não vira opção do claude
    return [caminho, "-p", "--resume", id_, "--permission-mode", "default", "--setting-sources", "project,local",
            "--allowedTools", FERRAMENTAS, "--output-format", "text", "--", prompt]


def separar(saida: str) -> tuple[str, str]:
    """(corpo, resumo falado). Sem a linha RESUMO:, o começo do texto."""
    texto = saida.strip()
    if not texto:
        return "", VAZIO
    corpo, _, resumo = texto.rpartition("RESUMO:")
    if corpo or texto.startswith("RESUMO:"):
        return corpo.strip(), " ".join(resumo.split()) or VAZIO
    return texto, resumir(texto, 300)


def _comando_padrao(pedido: str) -> list[str]:
    return comando_trabalho(achar_claude() or "claude", pedido)


class Trabalho:
    def __init__(self, comando=_comando_padrao, teto: float = TETO_S):
        self.comando, self.teto = comando, teto
        self.cancelado = False
        self.rodando = False  # um trabalho por vez (quem dispara marca e desmarca)
        self._proc: asyncio.subprocess.Process | None = None

    async def executar(self, pedido: str, pasta: Path) -> str:
        """O texto inteiro que o Claude Code escreveu, ou ESTOUROU/FALHOU/CANCELADA."""
        self.cancelado = False
        env = ambiente_sem({"ANTHROPIC_API_KEY"} | CHAVES_DOS_MODELOS)
        try:
            proc = self._proc = await asyncio.create_subprocess_exec(
                *self.comando(pedido), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                env=env, cwd=str(pasta), creationflags=SEM_JANELA)
        except OSError:
            return FALHOU
        try:
            saida, _ = await asyncio.wait_for(proc.communicate(), self.teto)
        except asyncio.TimeoutError:
            _matar(proc)
            await proc.wait()
            return ESTOUROU
        except asyncio.CancelledError:
            _matar(proc)
            raise
        finally:
            self._proc = None
        if self.cancelado:
            return CANCELADA
        if proc.returncode != 0:
            return FALHOU
        return saida.decode("utf-8", errors="replace")

    def cancelar(self) -> None:
        self.cancelado = True
        if self._proc is not None:
            _matar(self._proc)
