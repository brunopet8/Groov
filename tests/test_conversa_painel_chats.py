import asyncio
import json
import os

import pytest

from src.conversa import ajudante, chats, painel_chats, trabalho
from src.conversa.mensagens import Recusada, ler_envio, ler_id
from src.conversa.sessao import Estado, Sessao

ID = "11111111-2222-3333-4444-555555555555"
AGORA = 1_800_000_000.0


@pytest.fixture(autouse=True)
def _sem_filtro_de_temp(monkeypatch):
    monkeypatch.setattr(chats, "_temporaria", lambda cwd: False)


def _historico(tmp_path):
    ws = tmp_path / "Proj"
    ws.mkdir()
    d = tmp_path / "projects" / "p"
    d.mkdir(parents=True)
    linhas = [{"type": "user", "cwd": str(ws), "timestamp": "2027-01-15T08:00:00.000Z",
               "message": {"role": "user", "content": "oi"}},
              {"type": "assistant", "cwd": str(ws), "message": {"content": [{"type": "text", "text": "olá"}]}}]
    f = d / f"{ID}.jsonl"
    f.write_text("".join(json.dumps(x) + "\n" for x in linhas), encoding="utf-8")
    os.utime(f, (AGORA, AGORA))
    return tmp_path / "projects", ws


class TrabalhoFalso:
    def __init__(self, saida="Feito."):
        self.saida, self.rodando, self.cancelado, self.comando, self.chamadas = saida, False, False, None, []

    async def executar(self, pedido, pasta):
        self.chamadas.append((self.comando(pedido), pasta))
        return self.saida


class ClaudeFalso:
    """Faz o papel do módulo claude_app: registra o que a janela pediu."""
    def __init__(self, feitos, abre=True):
        self.feitos, self.abre = feitos, abre

    def abrir(self, cli_id):
        self.feitos.append(("abrir", cli_id))
        return self.abre

    def area(self, a):
        self.feitos.append(("area", a))

    def soltar(self):
        self.feitos.append(("soltar",))


def _acoes(tmp_path, t=None, estado=Estado.CONVERSANDO):
    projetos, ws = _historico(tmp_path)
    enviadas, abertos, retomadas = [], [], []
    sessao = Sessao()
    sessao.estado = estado
    ditado = {"armado": False, "usado": False}

    async def mandar(d):
        enviadas.append(d)

    async def retomar(com_fala=True):
        retomadas.append(com_fala)
        sessao.estado = Estado.CONVERSANDO
    t = t or TrabalhoFalso()
    acoes = painel_chats.criar_acoes_dos_chats(lambda: projetos, mandar, t, sessao, retomar, ditado,
                                               claude=ClaudeFalso(abertos),
                                               achar_claude=lambda: "claude", agora=lambda: AGORA)
    return acoes, enviadas, abertos, retomadas, ditado, t, ws


def _rodar(coro):
    async def main():
        await coro
        await asyncio.gather(*list(painel_chats._tarefas))
    asyncio.run(main())


def test_ler_id():
    assert ler_id({"id": ID}) == ID
    assert ler_envio({"id": ID, "texto": " faz X "}) == (ID, "faz X")


@pytest.mark.parametrize("d", [{"id": "../x"}, {"id": 3}, {}, {"id": "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"}])
def test_chat_id_invalido(d):
    with pytest.raises(Recusada):
        ler_id(d)


def test_projetos_responde_lista(tmp_path):
    acoes, enviadas, *_ = _acoes(tmp_path)
    _rodar(acoes["projetos"]({}))
    [w] = enviadas[0]["projetos"]
    assert w["nome"] == "Proj" and w["chats"][0]["id"] == ID


def test_chat_responde_mensagens(tmp_path):
    acoes, enviadas, *_ = _acoes(tmp_path)
    _rodar(acoes["chat"]({"id": ID}))
    assert enviadas == [{"chat": {"id": ID, "workspace": "Proj",
                                  "mensagens": [{"quem": "voce", "texto": "oi"}, {"quem": "claude", "texto": "olá"}]}}]


def test_chat_desconhecido_recusa(tmp_path):
    acoes, *_ = _acoes(tmp_path)
    with pytest.raises(Recusada):
        _rodar(acoes["chat"]({"id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"}))


def test_enviar_entrega_resposta(tmp_path):
    acoes, enviadas, _, _, _, t, ws = _acoes(tmp_path)
    _rodar(acoes["chat_enviar"]({"id": ID, "texto": "faz X"}))
    assert t.chamadas == [(trabalho.comando_retomar("claude", ID, "faz X"), ws)]
    assert enviadas == [{"chat_resposta": {"id": ID, "texto": "Feito."}}] and t.rodando is False


def test_enviar_falhou(tmp_path):
    acoes, enviadas, *_ = _acoes(tmp_path, TrabalhoFalso(ajudante.FALHOU))
    _rodar(acoes["chat_enviar"]({"id": ID, "texto": "faz X"}))
    assert enviadas == [{"chat_resposta": {"id": ID, "erro": "falhou"}}]


def test_enviar_ocupado(tmp_path):
    t = TrabalhoFalso()
    t.rodando = True
    acoes, *_ = _acoes(tmp_path, t)
    with pytest.raises(Recusada, match="ocupado"):
        _rodar(acoes["chat_enviar"]({"id": ID, "texto": "faz X"}))
    assert t.chamadas == []


def test_claude_abre_o_chat_no_app_e_encaixa_na_area(tmp_path):
    acoes, _, feitos, *_ = _acoes(tmp_path)
    assert "chat_terminal" not in acoes  # o terminal saiu (14/11): o chat abre no app desktop
    _rodar(acoes["chat_claude"]({"id": ID}))
    _rodar(acoes["claude_area"]({"x": 0.1, "y": 0.1, "w": 0.8, "h": 0.8}))
    _rodar(acoes["claude_solto"]({}))
    assert feitos == [("abrir", ID), ("area", (0.1, 0.1, 0.8, 0.8)), ("soltar",)]


def test_claude_recusa_chat_inexistente_area_ruim_e_app_que_nao_abre(tmp_path):
    acoes, _, feitos, *_ = _acoes(tmp_path)
    with pytest.raises(Recusada):
        _rodar(acoes["chat_claude"]({"id": "99999999-2222-3333-4444-555555555555"}))
    with pytest.raises(Recusada):
        _rodar(acoes["claude_area"]({"x": 2, "y": 0, "w": 1, "h": 1}))
    assert feitos == []
    (tmp_path / "b").mkdir()
    projetos, _ = _historico(tmp_path / "b")
    acoes = painel_chats.criar_acoes_dos_chats(lambda: projetos, None, TrabalhoFalso(), Sessao(), None, {},
                                               claude=ClaudeFalso([], abre=False))
    with pytest.raises(Recusada, match="não abriu"):
        _rodar(acoes["chat_claude"]({"id": ID}))


def test_ditar_arma(tmp_path):
    acoes, _, _, retomadas, ditado, *_ = _acoes(tmp_path, estado=Estado.OCIOSO)
    _rodar(acoes["ditar"]({}))
    assert ditado["armado"] is True and retomadas == [False]


def test_ditar_dormindo_recusa(tmp_path):
    acoes, *_ = _acoes(tmp_path, estado=Estado.DORMINDO)
    with pytest.raises(Recusada):
        _rodar(acoes["ditar"]({}))


def test_comando_retomar():
    c = trabalho.comando_retomar("claude", ID, "--faz X")
    assert c[:4] == ["claude", "-p", "--resume", ID] and c[-2:] == ["--", "--faz X"] and "--setting-sources" in c


def test_ditar_vence_em_30s(tmp_path):
    acoes, *_, ditado, _, _ = _acoes(tmp_path)
    _rodar(acoes["ditar"]({}))
    assert ditado["ate"] - __import__("time").monotonic() == pytest.approx(painel_chats.DITADO_S, abs=1)
