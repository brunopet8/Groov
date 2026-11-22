"""A cadeia de produção do bot (SondaPaginaComposta > SondaComposta > Sonda + SondaAD) com falsos, passando pelo laço."""
import asyncio
import logging
from pathlib import Path
from functools import partial

from src.conversa import laco as L
from src.conversa.pc import Leitura, Sonda, janela_da_aba
from src.conversa.sessao import Sessao
from src.conversa.sonda_ad import SondaAD, SondaComposta
from src.conversa.sonda_pagina import SondaPagina, SondaPaginaComposta
from src.conversa.timers import Timers
from tests.test_conversa_laco import Ctx, P, Relogio, Roteiro

HWND = 4242
PEDIDO = "abre o bloco de notas e escreve olá mundo"


class SondaFalsa(Sonda):
    """A Sonda de verdade (abrir_app, janelas...) com o PowerShell trocado por respostas fixas."""

    def __init__(self):
        super().__init__(comando=["nao-roda"])
        self.pedidos = []

    async def _chamar(self, op, teto=None, **dados):
        self.pedidos.append((op, dados))
        return {"abrir_app": {"hwnd": HWND}, "janelas": {"janelas": []}, "primeiro_plano": {"hwnd": HWND},
                "trazer": {"ok": True}}.get(op, {"ok": True})


class ADFalso(SondaAD):
    def __init__(self):
        super().__init__(comando=["nao-roda"], processo_de=lambda h: "notepad", titulo_de=lambda h: "Sem título - Bloco de Notas")
        self.chamadas = []

    async def _chamar(self, *args, teto=None):
        self.chamadas.append(args)
        if args[0] == "snapshot":
            return {"window": {"title": "Sem título - Bloco de Notas"}, "complete": True,
                    # formato real do 1.2.0 (snapshot vivo do Notepad, 11/11): o editor é `textfield` com `states`
                    "tree": {"role": "window", "name": "Bloco de Notas", "available_actions": ["SetFocus"], "children": [
                        {"role": "group", "available_actions": ["SetFocus"], "children": [
                            {"role": "textfield", "name": "Editor de Texto", "role_description": "documento", "ref_id": "@s1:e1",
                             "states": ["focused"], "available_actions": ["SetValue", "Scroll", "SetFocus"]}]}]}}
        if args[0] == "get":
            return {"value": ""}
        return {"disposition": "delivered_verified"}


class ClienteNunca:
    async def chamar(self, *a, **k):
        raise AssertionError("o Notepad não passa pela sonda de página")


def cadeia():
    base, ad = SondaFalsa(), ADFalso()
    return SondaPaginaComposta(SondaComposta(base, ad, minimizada=lambda h: False),
                               SondaPagina(ClienteNunca(), processo_de=lambda h: "notepad")), base, ad


def laco(backend, *passos):
    ctx, relogio = Ctx(()), Relogio()
    return L.Laco(backend, Roteiro(*passos), ctx.perguntar, ctx.falar, ctx.dormir, Timers(ctx.rodar), Sessao(),
                  relogio=relogio, esperar=relogio.esperar, achar_janela=partial(janela_da_aba, prazo=1, passo=0, assentar=0))


def test_abrir_app_pela_cadeia_inteira_nao_cai(caplog):
    backend, base, ad = cadeia()
    caplog.set_level(logging.INFO)
    d = asyncio.run(laco(backend, P("abrir_app", app="bloco de notas"), P("desistir")).executar(PEDIDO))
    assert "laço caiu" not in caplog.text, caplog.text
    assert ("abrir_app", {"processo": "notepad", "exe": "notepad.exe"}) in base.pedidos
    assert d.tipo == "desistiu"


def test_hwnd_que_nao_e_numero_nao_vira_typeerror():
    """11/11 (Bloco de Notas): o sonda.ps1 devolveu a lista de janelas no lugar do hwnd e o int() caiu em TypeError."""
    base = SondaFalsa()

    async def chamar(op, teto=None, **dados):
        return {"hwnd": [1, 2, 3]}
    base._chamar = chamar
    assert asyncio.run(base.abrir_app("bloco de notas")) is None


def test_laco_que_cai_loga_tipo_e_onde_sem_conteudo(caplog):
    class Quebrado(SondaFalsa):
        async def abrir_app(self, nome):
            raise TypeError("segredo da janela")
    caplog.set_level(logging.INFO)
    asyncio.run(laco(Quebrado(), P("abrir_app", app="bloco de notas")).executar(PEDIDO))
    assert "laço caiu: TypeError em abrir_app:" in caplog.text and "(passo abrir_app)" in caplog.text
    assert "segredo" not in caplog.text


def test_script_nao_passa_a_lista_inteira_ao_where_object():
    ps1 = (Path(__file__).parents[1] / "src" / "conversa" / "sonda.ps1").read_text(encoding="utf-8")
    assert "Janelas-Dos-Processos { $true } | ForEach-Object { $_ } | Where-Object" in ps1


def test_notepad_le_a_janela_e_digita_pelo_set_value():
    backend, base, ad = cadeia()
    leitura = asyncio.run(backend.ler(HWND))
    assert isinstance(leitura, Leitura) and leitura.elementos[0].runtime_id == "@s1:e1"
    assert asyncio.run(backend.digitar(HWND, leitura.elementos[0], "teste do GROOV", None)) is True
    assert ("set-value", "@s1:e1", "--", "teste do GROOV") in ad.chamadas


def test_laco_abre_le_e_digita_no_notepad(caplog):
    backend, base, ad = cadeia()
    caplog.set_level(logging.INFO)
    asyncio.run(laco(backend, P("abrir_app", app="bloco de notas"), P("digitar", id=0, texto="teste do GROOV"),
                     P("desistir")).executar(PEDIDO))
    assert "laço caiu" not in caplog.text, caplog.text
    assert ("set-value", "@s1:e1", "--", "teste do GROOV") in ad.chamadas


def test_bloco_de_notas_digita_pelo_json_real():
    """11/11: com `ref_id` o editor vira Elemento Edit e o `digitar` chega ao `set-value`."""
    backend, base, ad = cadeia()
    d = asyncio.run(laco(backend, P("abrir_app", app="bloco de notas"), P("digitar", id=0, texto="teste do GROOV"),
                         P("responder", texto="Pronto.")).executar(PEDIDO))
    assert ("set-value", "@s1:e1", "--", "teste do GROOV") in ad.chamadas and d.tipo == "respondeu"


def test_laco_digita_embaixo_sem_apagar_o_texto_do_bloco_de_notas():
    """11/11: 'escreve embaixo de oi tudo bem' apagou o 'oi tudo bem' (o set-value troca o valor inteiro)."""
    backend, base, ad = cadeia()
    chamar = ad._chamar

    async def com_texto(*args, teto=None):
        r = await chamar(*args, teto=teto)
        return {"value": "oi tudo bem"} if args[0] == "get" else r

    ad._chamar = com_texto
    asyncio.run(laco(backend, P("abrir_app", app="bloco de notas"), P("digitar", id=0, texto="uma frase"),
                     P("responder", texto="Pronto.")).executar(PEDIDO))
    assert ("set-value", "@s1:e1", "--", "oi tudo bem\r\numa frase") in ad.chamadas
