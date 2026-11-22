import asyncio
import json
import sys
from pathlib import Path

from src.conversa import ajudante, trabalho


def test_listar_workspaces(tmp_path):
    proj, real = tmp_path / "projects", tmp_path / "Meu Projeto"
    real.mkdir()
    (proj / "a").mkdir(parents=True)
    (proj / "a" / "x.jsonl").write_text('{"type":"x"}\n' + json.dumps({"cwd": str(real)}) + "\n", encoding="utf-8")
    (proj / "b").mkdir()
    (proj / "b" / "y.jsonl").write_text(json.dumps({"cwd": str(tmp_path / "sumiu")}) + "\n", encoding="utf-8")
    fixos = {"Groov-vault": tmp_path / "v"}
    ws = trabalho.listar_workspaces(proj, fixos)
    assert list(ws) == ["Groov-vault", "Meu Projeto"] and ws["Meu Projeto"] == real


def test_listar_workspaces_sem_pasta(tmp_path):
    assert trabalho.listar_workspaces(tmp_path / "nada", {"v": tmp_path}) == {"v": tmp_path}


def test_pasta_do_workspace_desconhecido(tmp_path):
    ws = {"projeto": tmp_path / "e"}
    assert trabalho.pasta_do_workspace("projeto", ws, tmp_path) == tmp_path / "e"
    assert trabalho.pasta_do_workspace("outro", ws, tmp_path) == tmp_path
    assert trabalho.pasta_do_workspace(None, ws, tmp_path) == tmp_path


def test_comando_trabalho_flags():
    c = trabalho.comando_trabalho("claude", "faz X")
    assert c[:2] == ["claude", "-p"] and c[2].endswith("Pedido: faz X") and "RESUMO:" in c[2]
    assert "acceptEdits" not in c and "--dangerously-skip-permissions" not in c
    for par in (["--model", "sonnet"], ["--permission-mode", "default"], ["--setting-sources", "project,local"],
                ["--allowedTools", "Read,Glob,Grep,WebSearch,WebFetch,Skill,Edit(./**)"], ["--output-format", "text"]):
        i = c.index(par[0])
        assert c[i:i + 2] == par


def test_separar_com_resumo():
    assert trabalho.separar("# Relatório\nlinha\nRESUMO: Pronto, senhor.\n") == ("# Relatório\nlinha", "Pronto, senhor.")


def test_separar_sem_resumo():
    assert trabalho.separar("Texto sem resumo.") == ("Texto sem resumo.", "Texto sem resumo.")
    assert trabalho.separar("  ") == ("", ajudante.VAZIO)


def test_executar_usa_a_pasta(tmp_path):
    t = trabalho.Trabalho(comando=lambda pedido: [sys.executable, "-c", "import os;print(os.getcwd())"])
    assert Path(asyncio.run(t.executar("x", tmp_path)).strip()) == tmp_path


def test_executar_falha(tmp_path):
    t = trabalho.Trabalho(comando=lambda pedido: [sys.executable, "-c", "raise SystemExit(3)"])
    assert asyncio.run(t.executar("x", tmp_path)) == ajudante.FALHOU


def test_fixos_do_usuario_vem_da_config(tmp_path, monkeypatch):
    v = tmp_path / "vault"
    assert trabalho.fixos_do_usuario(v) == {"Groov-vault": v}
    monkeypatch.setenv("GROOV_WORKSPACES_EXTRA", r"C:\A\Proj1, ,D:\B\Proj 2")
    assert trabalho.fixos_do_usuario(v) == {"Groov-vault": v, "Proj1": Path(r"C:\A\Proj1"), "Proj 2": Path(r"D:\B\Proj 2")}
