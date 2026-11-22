"""Cliente MCP por stdio contra um servidor falso (script Python), nunca o Playwright de verdade."""
import asyncio
import sys

import pytest

from src.conversa.mcp_stdio import ClienteMCP, ErroFerramenta
from src.conversa.pc import ErroSonda

SERVIDOR = r'''
import json, os, sys
modo = os.environ.get("MODO", "")
for linha in sys.stdin:
    m = json.loads(linha)
    if "id" not in m:
        continue
    print(json.dumps({"jsonrpc": "2.0", "method": "notifications/message", "params": {}}), flush=True)  # ruído antes da resposta
    if m["method"] == "initialize":
        r = {"protocolVersion": "x", "capabilities": {}, "serverInfo": {"name": "f", "version": "1"}}
    elif modo == "morre":
        sys.exit(0)
    elif modo == "trava":
        import time; time.sleep(60)
    elif modo == "erro":
        r = {"content": [{"type": "text", "text": "SEGREDO da página"}], "isError": True}
    else:
        r = {"content": [{"type": "text", "text": "eco:" + m["params"]["name"] + ":" + os.environ.get("TOKEN", "-")},
                         {"type": "image", "data": "x"}, {"type": "text", "text": json.dumps(m["params"]["arguments"])}]}
    print(json.dumps({"jsonrpc": "2.0", "id": m["id"], "result": r}), flush=True)
'''


def cliente(tmp_path, teto=5, **env):
    script = tmp_path / "servidor.py"
    script.write_text(SERVIDOR, encoding="utf-8")
    return ClienteMCP([sys.executable, str(script)], {"PATH": "", **env}, teto=teto, teto_abertura=teto)


def rodar(coro):
    return asyncio.run(coro)


def test_chamada_devolve_so_os_blocos_de_texto_e_leva_o_ambiente(tmp_path):
    async def cena():
        c = cliente(tmp_path, TOKEN="t0k")
        try:
            return await c.chamar("browser_snapshot", {"a": 1}), await c.chamar("browser_tabs")
        finally:
            await c.fechar()
    a, b = rodar(cena())
    assert a == 'eco:browser_snapshot:t0k\n{"a": 1}'
    assert b.startswith("eco:browser_tabs")


def test_erro_da_ferramenta_tem_mensagem_fixa_e_o_servidor_segue(tmp_path):
    async def cena():
        c = cliente(tmp_path, MODO="erro")
        try:
            with pytest.raises(ErroFerramenta) as e:
                await c.chamar("browser_click")
            proc = c._proc
            return str(e.value), proc is not None and proc.returncode is None
        finally:
            await c.fechar()
    msg, vivo = rodar(cena())
    assert "SEGREDO" not in msg and vivo and "(outra)" in msg


def test_servidor_que_morre_vira_erro_e_a_proxima_chamada_reabre(tmp_path):
    async def cena():
        c = cliente(tmp_path, MODO="morre")
        try:
            with pytest.raises(ErroSonda):
                await c.chamar("x")
            assert c._proc is None
        finally:
            await c.fechar()
    rodar(cena())


def test_estourar_o_teto_mata_o_servidor(tmp_path):
    async def cena():
        c = cliente(tmp_path, teto=1.5, MODO="trava")
        with pytest.raises(ErroSonda, match="teto"):
            await c.chamar("x")
        assert c._proc is None
    rodar(cena())


def test_executavel_ausente_vira_erro(tmp_path):
    async def cena():
        c = ClienteMCP([str(tmp_path / "nao-existe.exe")], {}, 2, 2)
        with pytest.raises(ErroSonda, match="iniciar"):
            await c.chamar("x")
    rodar(cena())


def test_categoria_do_erro_so_devolve_nome_fixo():
    from src.conversa.mcp_stdio import categoria_do_erro
    assert categoria_do_erro("<div> subtree intercepts pointer events de Netflix") == "intercepta_ponteiro"
    assert categoria_do_erro("Timeout 5000ms exceeded") == "timeout" and categoria_do_erro("qualquer coisa") == "outra"
