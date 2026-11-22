import asyncio
import subprocess
import sys
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.vida.banco import Banco
from src.vida.coletor import Coletor, Fonte, descrever_erro, fonte_trello
from src.vida.trava import travar

RAIZ = Path(__file__).parent.parent
RIO = timezone(timedelta(hours=-3))


async def rodar_uma_vez(coletor):
    t = asyncio.create_task(coletor.rodar())
    await asyncio.sleep(0.2)
    t.cancel()
    try:
        await t
    except asyncio.CancelledError:
        pass


def test_fonte_que_falha_nao_para_as_outras_e_nao_vaza_texto(tmp_path):
    avisos, rodou = [], []

    async def ruim(agora):
        raise ValueError("SEGREDO no corpo")

    async def boa(agora):
        rodou.append(agora)

    async def cenario():
        c = Coletor(Banco(tmp_path / "vida.db"), [Fonte("ruim", 0.05, ruim), Fonte("boa", 0.05, boa)],
                    avisar=avisos.append)
        await rodar_uma_vez(c)

    asyncio.run(cenario())
    assert len(rodou) >= 2 and avisos and all("SEGREDO" not in a and "ValueError" in a for a in avisos)


def test_pedir_rodada_roda_antes_do_intervalo(tmp_path):
    rodou = []

    async def fonte(agora):
        rodou.append(agora)

    async def cenario():
        c = Coletor(Banco(tmp_path / "vida.db"), [Fonte("f", 60.0, fonte)])
        t = asyncio.create_task(c.rodar())
        await asyncio.sleep(0.1)
        assert len(rodou) == 1  # 1ª volta: todas rodam
        c.pedir_rodada()
        await asyncio.sleep(0.3)
        t.cancel()

    asyncio.run(cenario())
    assert len(rodou) == 2


def test_sem_fontes_so_espera_pedidos(tmp_path):
    async def cenario():
        c = Coletor(Banco(tmp_path / "vida.db"), [])
        t = asyncio.create_task(c.rodar())
        await asyncio.sleep(0.1)
        c.pedir_rodada()  # não pode quebrar nem girar à toa
        await asyncio.sleep(0.1)
        assert not t.done()
        t.cancel()

    asyncio.run(cenario())


def test_descrever_erro_so_tipo_e_codigo():
    assert descrever_erro(urllib.error.HTTPError("http://x", 401, "SEGREDO", {}, None)) == "HTTPError 401"
    assert descrever_erro(urllib.error.URLError("SEGREDO")) == "URLError"
    assert descrever_erro(ValueError("SEGREDO")) == "ValueError"


def test_trello_401_avisa_com_codigo_e_mantem_o_banco(tmp_path):
    banco = Banco(tmp_path / "vida.db")
    banco.trocar_itens("trello", {"c1": {"nome": "A"}})

    def buscar(url, cab):
        raise urllib.error.HTTPError(url, 401, "invalid token", {}, None)

    avisos = []
    fonte = fonte_trello(banco, "K", "T", ["Projeto 2026"], avisos.append, buscar=buscar)
    asyncio.run(rodar_uma_vez(Coletor(banco, [fonte], avisar=avisos.append)))
    assert avisos == ["coletor: trello falhou (HTTPError 401)"] and banco.itens("trello") == {"c1": {"nome": "A"}}
    assert banco.ultima_coleta("trello") is None  # falha não conta como coleta: o "hoje" não pode fingir que está em dia


def test_sem_internet_avisa_e_mantem_o_banco(tmp_path):
    banco = Banco(tmp_path / "vida.db")
    banco.trocar_itens("trello", {"c1": {"nome": "A"}})

    def buscar(url, cab):
        raise urllib.error.URLError("x")

    avisos = []
    fonte = fonte_trello(banco, "K", "T", ["Projeto 2026"], avisos.append, buscar=buscar)
    asyncio.run(rodar_uma_vez(Coletor(banco, [fonte], avisar=avisos.append)))
    assert avisos == ["coletor: trello falhou (URLError)"] and banco.itens("trello") == {"c1": {"nome": "A"}}


def trello_que_responde(lista_do_cartao):
    def buscar(url, cab):
        if "/members/me/boards" in url:
            return [{"id": "b1", "name": "Projeto 2026"}]
        return [{"id": "l1", "name": lista_do_cartao["nome"], "closed": False, "cards": [
            {"id": "c1", "name": "Entrevista X", "idList": "l1", "due": None, "closed": False,
             "dateLastActivity": "2026-10-27T12:00:00.000Z", "badges": {}}]}]
    return buscar


def test_fonte_trello_grava_itens_e_eventos(tmp_path):
    banco = Banco(tmp_path / "vida.db")
    lista = {"nome": "A fazer"}
    fonte = fonte_trello(banco, "K", "T", ["Projeto 2026"], print, buscar=trello_que_responde(lista))
    agora = datetime(2026, 10, 27, 9, tzinfo=RIO)
    asyncio.run(fonte.coletar(agora))
    assert banco.itens("trello")["c1"]["lista"] == "A fazer" and banco.eventos_nao_contados() == []  # 1ª: só a base
    lista["nome"] = "Em andamento"
    asyncio.run(fonte.coletar(agora))
    (evento,) = banco.eventos_nao_contados()
    assert evento.tipo == "mudou" and evento.texto == "No Projeto 2026, Entrevista X foi para Em andamento."
    assert banco.itens("trello")["c1"]["lista"] == "Em andamento"
    assert banco.ultima_coleta("trello") == agora


def test_fonte_trello_avisa_quadro_nao_achado(tmp_path):
    avisos = []
    fonte = fonte_trello(Banco(tmp_path / "vida.db"), "K", "T", ["Não existe"], avisos.append,
                         buscar=trello_que_responde({"nome": "A fazer"}))
    asyncio.run(fonte.coletar(datetime(2026, 10, 27, 9, tzinfo=RIO)))
    assert avisos == ["trello: quadros não achados: Não existe"]


def test_nenhum_quadro_achado_nao_apaga_nem_marca_coleta(tmp_path):
    banco = Banco(tmp_path / "vida.db")
    banco.trocar_itens("trello", {"c1": {"nome": "A"}})
    fonte = fonte_trello(banco, "K", "T", ["Não existe"], print, buscar=trello_que_responde({"nome": "A fazer"}))
    asyncio.run(fonte.coletar(datetime(2026, 10, 27, 9, tzinfo=RIO)))
    assert banco.itens("trello") == {"c1": {"nome": "A"}} and banco.ultima_coleta("trello") is None


def test_coletor_ocioso_nao_gira_a_toa(tmp_path):
    """Com o intervalo longe, o laço dorme até o vencimento ou um pedido; um laço ocupado travaria o áudio."""
    chamadas = []

    def relogio():
        chamadas.append(1)
        return 0.0

    async def fonte(agora):
        pass

    async def cenario():
        c = Coletor(Banco(tmp_path / "vida.db"), [Fonte("f", 60.0, fonte)], relogio=relogio)
        t = asyncio.create_task(c.rodar())
        await asyncio.sleep(0.3)
        t.cancel()

    asyncio.run(cenario())
    assert len(chamadas) < 10, len(chamadas)


def test_trava_impede_segundo_coletor(tmp_path):
    arquivo = travar(tmp_path / "coletor.lock")
    outro = subprocess.run(
        [sys.executable, "-c",
         f"from src.vida.trava import travar; "
         f"print(travar(__import__('pathlib').Path(r'{tmp_path / 'coletor.lock'}')) is None)"],
        capture_output=True, text=True, cwd=RAIZ)
    assert arquivo is not None and outro.stdout.strip() == "True", outro.stderr
    arquivo.close()
    livre = subprocess.run(
        [sys.executable, "-c",
         f"from src.vida.trava import travar; "
         f"print(travar(__import__('pathlib').Path(r'{tmp_path / 'coletor.lock'}')) is None)"],
        capture_output=True, text=True, cwd=RAIZ)
    assert livre.stdout.strip() == "False", livre.stderr  # solta a trava ao fechar


def test_fonte_trello_marca_o_quadro_de_contagem(tmp_path):
    banco = Banco(tmp_path / "vida.db")
    fonte = fonte_trello(banco, "K", "T", ["Projeto 2026"], print, buscar=trello_que_responde({"nome": "A"}),
                         contagem=["projeto 2026"])
    asyncio.run(fonte.coletar(datetime(2026, 10, 27, 9, tzinfo=RIO)))
    assert banco.itens("trello")["c1"]["contagem"] is True
