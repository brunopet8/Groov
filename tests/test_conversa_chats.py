import json
import os
from pathlib import Path

import pytest

from src.conversa import chats

DIA = 86400.0
AGORA = 1_800_000_000.0
ID1 = "11111111-2222-3333-4444-555555555555"
ID2 = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


@pytest.fixture(autouse=True)
def _temp_em_outro_lugar(monkeypatch, request):
    # o tmp_path do pytest fica dentro da pasta temporária do sistema, que a listagem ignora
    if request.node.name != "test_pasta_temporaria_fica_fora":
        monkeypatch.setattr(chats, "_temporaria", lambda cwd: False)


def _iso(t: float) -> str:
    from datetime import datetime, timezone
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _user(texto, t, cwd, **extra):
    return {"type": "user", "cwd": str(cwd), "timestamp": _iso(t), "isSidechain": False,
            "message": {"role": "user", "content": texto}, **extra}


def _assistant(blocos, t, cwd):
    return {"type": "assistant", "cwd": str(cwd), "timestamp": _iso(t), "message": {"role": "assistant", "content": blocos}}


def _escrever(projetos: Path, pasta: str, id_: str, linhas, mtime=AGORA):
    d = projetos / pasta
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{id_}.jsonl"
    f.write_text("".join((l if isinstance(l, str) else json.dumps(l)) + "\n" for l in linhas), encoding="utf-8")
    os.utime(f, (mtime, mtime))
    return f


def test_listar_conta_prompts_7d(tmp_path):
    ws = tmp_path / "Meu Projeto"
    ws.mkdir()
    proj = tmp_path / "projects"
    _escrever(proj, "C--Meu-Projeto", ID1, [
        _user("velho", AGORA - 8 * DIA, ws),
        _user("novo 1", AGORA - DIA, ws),
        _user("<command-name>/model</command-name>", AGORA - DIA, ws),
        _user([{"type": "tool_result", "content": "x"}], AGORA - DIA, ws),
        _user("lateral", AGORA - DIA, ws, isSidechain=True),
        _user("novo 2", AGORA - 100, ws),
    ])
    [w] = chats.listar(proj, AGORA)
    assert w.nome == "Meu Projeto" and w.pasta == ws and w.prompts_7d == 2
    assert [(c.id, c.prompts_7d, c.titulo) for c in w.chats] == [(ID1, 2, "velho")]


def test_titulo_primeiro_prompt(tmp_path):
    _escrever(tmp_path, "p", ID1, [_user("x" * 200, AGORA, tmp_path)])
    assert len(chats.listar(tmp_path, AGORA)[0].chats[0].titulo) == 80


def test_fora_dos_30_dias_nao_lista(tmp_path):
    _escrever(tmp_path, "p", ID1, [_user("oi", AGORA - 40 * DIA, tmp_path)], mtime=AGORA - 40 * DIA)
    assert chats.listar(tmp_path, AGORA) == []


def test_linha_torta_ignorada(tmp_path):
    _escrever(tmp_path, "p", ID1, ['{"type":"user", quebrado', _user("ok", AGORA, tmp_path), "[1,2]"])
    assert chats.listar(tmp_path, AGORA)[0].prompts_7d == 1


def test_cache_por_mtime(tmp_path, monkeypatch):
    _escrever(tmp_path, "p", ID1, [_user("ok", AGORA, tmp_path)])
    chats._CACHE.clear()
    lidos = []
    original = chats._ler

    def contar(arquivo):
        lidos.append(arquivo)
        return original(arquivo)
    monkeypatch.setattr(chats, "_ler", contar)
    chats.listar(tmp_path, AGORA)
    chats.listar(tmp_path, AGORA)
    assert len(lidos) == 1


def test_mais_novo_primeiro(tmp_path):
    _escrever(tmp_path, "a", ID1, [_user("a", AGORA - DIA, tmp_path / "a")], mtime=AGORA - DIA)
    _escrever(tmp_path, "b", ID2, [_user("b", AGORA, tmp_path / "b")], mtime=AGORA)
    assert [w.nome for w in chats.listar(tmp_path, AGORA)] == ["b", "a"]


def test_pasta_temporaria_fica_fora(tmp_path):
    (tmp_path / "x").mkdir()  # o tmp_path do pytest já está dentro da pasta temporária do sistema
    _escrever(tmp_path / "proj", "p", ID1, [_user("oi", AGORA, tmp_path / "x")])
    assert chats.listar(tmp_path / "proj", AGORA) == []


def test_mesmo_cwd_junta(tmp_path):
    ws = tmp_path / "Proj"
    ws.mkdir()
    _escrever(tmp_path / "proj", "a", ID1, [_user("um", AGORA, ws)])
    _escrever(tmp_path / "proj", "b", ID2, [_user("dois", AGORA, str(ws).upper())])
    [w] = chats.listar(tmp_path / "proj", AGORA)
    assert w.prompts_7d == 2 and len(w.chats) == 2


def test_mensagens_ordem_e_limite(tmp_path):
    f = _escrever(tmp_path, "p", ID1, [
        _user("pergunta", AGORA, tmp_path),
        _assistant([{"type": "text", "text": "resposta"}, {"type": "tool_use", "name": "Read", "input": {"x": 1}}],
                   AGORA, tmp_path),
        _user([{"type": "tool_result", "content": "segredo"}], AGORA, tmp_path),
        _assistant([{"type": "text", "text": "fim"}], AGORA, tmp_path),
    ])
    assert chats.mensagens(f) == [{"quem": "voce", "texto": "pergunta"}, {"quem": "claude", "texto": "resposta"},
                                  {"quem": "ferramenta", "texto": "Read"}, {"quem": "claude", "texto": "fim"}]
    assert chats.mensagens(f, limite=2) == [{"quem": "ferramenta", "texto": "Read"}, {"quem": "claude", "texto": "fim"}]


def test_mensagem_longa_cortada(tmp_path):
    f = _escrever(tmp_path, "p", ID1, [_user("y" * 5000, AGORA, tmp_path)])
    assert len(chats.mensagens(f)[0]["texto"]) == chats.TEXTO_MAX


def test_achar_rejeita_id_invalido(tmp_path):
    f = _escrever(tmp_path, "p", ID1, [_user("ok", AGORA, tmp_path)])
    assert chats.achar(tmp_path, ID1) == f
    assert chats.achar(tmp_path, ID2) is None
    for ruim in ("../x", "abc", ID1 + "/..", ""):
        assert chats.achar(tmp_path, ruim) is None


def test_para_janela_serializa(tmp_path):
    _escrever(tmp_path, "p", ID1, [_user("ok", AGORA, tmp_path)])
    [d] = chats.para_janela(chats.listar(tmp_path, AGORA))
    json.dumps(d)
    assert d["chats"][0]["id"] == ID1 and d["prompts_7d"] == 1
