"""Fase 8: compara a leitura da UIA (Sonda atual) com a leitura pela página (Playwright MCP + extensão) em Netflix, G1 e GitHub.
SÓ LEITURA: abre cada home numa aba NOVA do Chrome do usuário (browser_tabs new), lê e fecha só as abas que ele mesmo abriu; não clica nem digita. Imprime só tamanhos, tempos
e se a leitura caiu em tela de login; nunca o conteúdo da página.

Antes: extensão "Playwright Extension" instalada no Chrome do usuário e PLAYWRIGHT_MCP_EXTENSION_TOKEN em privado/.env (o script o
lê sozinho e não o imprime); servidor instalado com `npm ci --ignore-scripts` em ferramentas/navegador. Chrome aberto na janela
que o usuário quer usar (a aba nova abre nela).
Uso: .venv-conversa/Scripts/python scripts/medir_pagina.py [repeticoes=3]
"""
import asyncio
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.conversa import regras_pc, sonda_pagina  # noqa: E402
from src.conversa.ajudante import CHAVES_DOS_MODELOS  # noqa: E402
from src.conversa.pc import Sonda  # noqa: E402
from src.conversa.segredos import ler_segredos  # noqa: E402
from src.conversa.sonda_pagina import TOKEN_EXTENSAO, SondaPaginaComposta, escolher_sonda_pagina  # noqa: E402

HOMES = {"netflix": "https://www.netflix.com/browse", "g1": "https://g1.globo.com/", "github": "https://github.com/"}
ESPERA_CARGA_S = 8


def tamanho(l) -> dict:
    return {"chars_texto": len(l.texto), "elementos": len(l.elementos), "chars_elementos": sum(len(e.nome) + len(e.texto_interno) for e in l.elementos),
            "links_com_host": sum(e.host_do_link is not None for e in l.elementos), "login_mantido": not regras_pc.pagina_de_login(l.endereco, l.elementos), "cortado": l.cortado}


async def medir(nome: str, backend, hwnd: int, repeticoes: int) -> None:
    tempos, ultima = [], None
    for _ in range(repeticoes):
        t = time.monotonic()
        try:
            ultima = await backend.ler(hwnd)
        except Exception as e:  # noqa: BLE001 - só o tipo, nunca a mensagem
            print(f"  {nome}: falhou ({type(e).__name__})")
            return
        tempos.append(time.monotonic() - t)
    print(f"  {nome}: {tamanho(ultima)} tempo_mediano={statistics.median(tempos):.2f}s tempos={[round(x, 2) for x in tempos]}")


async def abas(cliente) -> list[tuple[int, str, str]]:
    """(indice, titulo, url) das abas que o servidor enxerga."""
    texto = await cliente.chamar("browser_tabs", {"action": "list"})
    return [(int(m[1]), m[3], m[4]) for linha in texto.splitlines() if (m := sonda_pagina._ABA.match(linha.strip()))]


def aba_para_fechar(lista: list[tuple[int, str, str]], titulo: str, url: str, previas: int) -> int | None:
    """Índice ATUAL da última aba que casa (URL ou título) SE houver mais dessas do que as `previas` do usuário; senão None (não fecha)."""
    achadas = [i for i, t, u in lista if u == url or t == titulo]
    return achadas[-1] if len(achadas) > previas else None


async def hwnd_do_chrome(uia, pagina, titulo: str) -> int | None:
    """A janela de Chrome cujo título casa com a aba nova (a UIA lê sem tirar o foco de ninguém)."""
    for h in await uia.janelas():
        if pagina.processo_de(h) == "chrome" and (pagina.titulo_de(h) == titulo or pagina.titulo_de(h).startswith(titulo + " - ")):
            return h
    return None


async def main(repeticoes: int) -> None:
    segredos = ler_segredos()
    token = segredos.get(TOKEN_EXTENSAO)
    if not token:
        print(f"não medido: {TOKEN_EXTENSAO} ausente em privado/.env")
        return
    uia = Sonda(segredos=frozenset(segredos) | CHAVES_DOS_MODELOS)
    composta = escolher_sonda_pagina(uia, frozenset(segredos) | CHAVES_DOS_MODELOS, token, ligada=True)
    if not isinstance(composta, SondaPaginaComposta):
        print("não medido: node ou servidor ausente (npm ci em ferramentas/navegador)")
        return
    pagina, cliente = composta.pagina, composta.pagina.cliente
    criadas = []  # (título, URL, quantas iguais o usuário já tinha) das abas que ESTE script abriu; ao fechar, procuro cada uma de novo na lista atual
    try:
        antes_fg = await uia.primeiro_plano()
        t = time.monotonic()
        existentes = await abas(cliente)  # a 1ª chamada conecta a extensão
        print(f"conexão: {time.monotonic() - t:.2f}s; abas visíveis ao servidor: {len(existentes)}")
        depois_fg = await uia.primeiro_plano()
        print(f"primeiro plano mudou na conexão: {antes_fg != depois_fg} (processo depois: {pagina.processo_de(depois_fg) or '?'})")
        for site, url in HOMES.items():
            print(site)
            antes = await abas(cliente)
            n_antes = len(antes)
            await cliente.chamar("browser_tabs", {"action": "new", "url": url})
            nova = [a for a in await abas(cliente) if a[0] >= n_antes]
            if len(nova) != 1:
                print("  não medido: não consegui isolar a aba nova (nada foi fechado)")
                continue
            indice, titulo, endereco = nova[0]
            criadas.append([titulo, endereco, sum(u == endereco or t == titulo for _, t, u in antes)])  # previas já certas, antes de qualquer espera
            await asyncio.sleep(ESPERA_CARGA_S)
            nova = [a for a in await abas(cliente) if a[0] == indice]
            titulo = nova[0][1] if nova else titulo
            endereco = nova[0][2] if nova else endereco
            criadas[-1] = [titulo, endereco, sum(u == endereco or t == titulo for _, t, u in antes)]  # iguais que já eram dele
            hwnd = await hwnd_do_chrome(uia, pagina, titulo)
            print(f"  janela achada pelo título da aba: {hwnd is not None}")
            if hwnd is None:
                continue
            print(f"  SondaPagina identificou a aba certa: {await pagina.aceita(hwnd)}")
            await medir("uia", uia, hwnd, repeticoes)
            await medir("pagina", pagina, hwnd, repeticoes)
    finally:
        try:
            for titulo, endereco, previas in criadas:
                try:
                    indice = aba_para_fechar(await abas(cliente), titulo, endereco, previas)
                    if indice is None:
                        print("  aviso: uma aba ficou aberta (não achei excedente sobre as do usuário); não fechei nada")
                        continue
                    await cliente.chamar("browser_tabs", {"action": "close", "index": indice})
                except Exception as e:  # noqa: BLE001
                    print(f"  aviso: não fechei uma aba ({type(e).__name__})")
            print(f"abas visíveis ao final: {len(await abas(cliente))}")
        except Exception as e:  # noqa: BLE001
            print(f"  aviso: não contei as abas ao final ({type(e).__name__})")
        finally:
            await cliente.fechar()


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 3))
