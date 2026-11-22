import asyncio
import sys

import pytest

from src.briefing import catalogo
from src.conversa.regras_pc import PedidoTimer
from src.conversa.timers import FRASE_DEU_O_TEMPO, Timers, rodar_sem_janela


def gravador(codigos=None):
    chamadas = []
    async def rodar(cmd):
        chamadas.append(cmd)
        return (codigos or {}).get(tuple(cmd), 0)
    return rodar, chamadas


async def sem_espera(_segundos):
    return None


async def girar():
    for _ in range(5):
        await asyncio.sleep(0)


def test_desligar_roda_abort_antes_de_trocar():
    rodar, chamadas = gravador()
    async def cena():
        t = Timers(rodar)
        assert await t.armar(PedidoTimer(60, True, False))
        assert await t.armar(PedidoTimer(30, True, False))
        assert t.armado()
    asyncio.run(cena())
    assert chamadas == [["shutdown", "/s", "/t", "3600"], ["shutdown", "/a"], ["shutdown", "/s", "/t", "1800"]]


def test_desligar_ja_agendado_de_antes_do_reinicio_troca():
    chamadas, codigos = [], [1190, 0, 0]  # 1190: ERROR_SHUTDOWN_IS_SCHEDULED, o TIMERS novo não sabia
    async def rodar(cmd):
        chamadas.append(cmd)
        return codigos.pop(0)
    async def cena():
        t = Timers(rodar)
        return await t.armar(PedidoTimer(30, True, False)), t.armado()
    assert asyncio.run(cena()) == (True, True)
    assert chamadas == [["shutdown", "/s", "/t", "1800"], ["shutdown", "/a"], ["shutdown", "/s", "/t", "1800"]]


def test_cancelar_timer_do_forno_cancela_o_simples_e_roda_abort():
    rodar, chamadas = gravador()
    async def cena():
        t = Timers(rodar, dormir=lambda _s: asyncio.Event().wait())
        await t.armar(PedidoTimer(10, False, False))
        return await t.cancelar("cancela o timer de desligar o forno"), t.armado()
    assert asyncio.run(cena()) == ("simples", False)
    assert chamadas == [["shutdown", "/a"]]


def test_desliga_o_timer_para_o_simples_sem_rodar_abort():
    rodar, chamadas = gravador()
    async def cena():
        t = Timers(rodar, dormir=lambda _s: asyncio.Event().wait())
        await t.armar(PedidoTimer(10, False, False))
        return await t.cancelar("desliga o timer"), t.armado()
    assert asyncio.run(cena()) == ("simples", False)
    assert chamadas == []


def test_cancelar_citando_pc_roda_abort_mesmo_sem_registro():
    rodar, chamadas = gravador({("shutdown", "/a"): 1116})  # 1116: nada agendado, conta como sucesso
    assert asyncio.run(Timers(rodar).cancelar("não desliga o pc")) == "desligar"
    assert ["shutdown", "/a"] in chamadas


def test_abort_que_falha_nao_diz_cancelado():
    rodar, _ = gravador({("shutdown", "/a"): 5})
    async def cena():
        t = Timers(rodar)
        await t.armar(PedidoTimer(60, True, False))
        return await t.cancelar("cancela o timer"), t.armado()
    assert asyncio.run(cena()) == ("falhou", True)


def test_shutdown_que_falha_nao_arma():
    rodar, _ = gravador({("shutdown", "/s", "/t", "3600"): 5})
    async def cena():
        t = Timers(rodar)
        return await t.armar(PedidoTimer(60, True, False)), t.armado()
    assert asyncio.run(cena()) == (False, False)


def test_timer_simples_toca_o_aviso_no_fim():
    rodar, chamadas = gravador()
    tocou, esperas = [], []
    async def dormir(s):
        esperas.append(s)
    async def aviso():
        tocou.append(True)
    async def cena():
        t = Timers(rodar, dormir=dormir)
        t.conectar(aviso)
        assert await t.armar(PedidoTimer(10, False, False))
        await girar()
        return t.armado()
    assert asyncio.run(cena()) is False
    assert tocou == [True] and esperas == [600] and chamadas == []


def test_recarga_troca_a_conexao_do_aviso():
    tocou = []
    async def a():
        tocou.append("a")
    async def b():
        tocou.append("b")
    async def cena():
        libera = asyncio.Event()
        async def dormir(_s):
            await libera.wait()
        t = Timers(gravador()[0], dormir=dormir)
        t.conectar(a)
        await t.armar(PedidoTimer(5, False, False))
        t.conectar(b)
        t.desconectar(a)  # o finally do bot antigo roda depois do novo conectar
        libera.set()
        await girar()
    asyncio.run(cena())
    assert tocou == ["b"]


def test_sem_conexao_o_aviso_se_perde_sem_erro():
    async def cena():
        t = Timers(gravador()[0], dormir=sem_espera)
        await t.armar(PedidoTimer(5, False, False))
        await girar()
        return t.armado()
    assert asyncio.run(cena()) is False


def test_dois_armados_sem_citar_pergunta_qual():
    rodar, _ = gravador()
    async def cena():
        t = Timers(rodar, dormir=lambda _s: asyncio.Event().wait())
        await t.armar(PedidoTimer(60, True, False))
        await t.armar(PedidoTimer(10, False, False))
        qual = await t.cancelar("cancela o timer")
        ambos = await t.cancelar("cancela os dois timers")
        return qual, ambos, t.armado()
    assert asyncio.run(cena()) == ("qual", "ambos", False)


def test_cancelar_um_so_armado():
    rodar, chamadas = gravador()
    async def cena():
        t = Timers(rodar, dormir=lambda _s: asyncio.Event().wait())
        nada = await t.cancelar("cancela o timer")
        await t.armar(PedidoTimer(10, False, False))
        simples = await t.cancelar("tira o timer")
        await t.armar(PedidoTimer(60, True, False))
        desligar = await t.cancelar("cancela o timer")
        return nada, simples, desligar, t.armado()
    assert asyncio.run(cena()) == ("nenhum", "simples", "desligar", False)
    assert chamadas == [["shutdown", "/s", "/t", "3600"], ["shutdown", "/a"]]


def test_timer_simples_novo_substitui_o_anterior():
    tocou = []
    async def aviso():
        tocou.append(True)
    async def cena():
        libera = asyncio.Event()
        async def dormir(_s):
            await libera.wait()
        t = Timers(gravador()[0], dormir=dormir)
        t.conectar(aviso)
        await t.armar(PedidoTimer(10, False, False))
        await t.armar(PedidoTimer(20, False, False))
        libera.set()
        await girar()
    asyncio.run(cena())
    assert tocou == [True]


def test_timer_simples_nao_roda_shutdown():
    rodar, chamadas = gravador()
    async def cena():
        t = Timers(rodar, dormir=lambda _s: asyncio.Event().wait())
        assert await t.armar(PedidoTimer(10, False, False))
        await girar()
    asyncio.run(cena())
    assert chamadas == []


def test_ambiguo_ou_sem_minutos_nao_arma():
    rodar, chamadas = gravador()
    async def cena():
        t = Timers(rodar)
        return [await t.armar(p) for p in (PedidoTimer(None, True, False), PedidoTimer(10, False, True),
                                           PedidoTimer(0, False, False))]
    assert asyncio.run(cena()) == [False, False, False] and chamadas == []


def test_aviso_esta_no_catalogo_de_frases_gravadas():
    assert FRASE_DEU_O_TEMPO in catalogo().values()


@pytest.mark.skipif(sys.platform != "win32", reason="cmd.exe")
def test_rodar_sem_janela_devolve_o_codigo():
    assert asyncio.run(rodar_sem_janela(["cmd", "/c", "exit 3"])) == 3
    assert asyncio.run(rodar_sem_janela(["programa_que_nao_existe_groov"])) == -1


def test_fins_e_observador_do_timer_simples():
    rodar, _ = gravador()
    async def cena():
        t, avisos = Timers(rodar, dormir=lambda _s: asyncio.Event().wait(), agora=lambda: 1000.0), []
        t.observar(lambda: avisos.append(dict(t.fins())))
        assert t.fins() == {}
        await t.armar(PedidoTimer(5, False, False))
        assert t.fins() == {"simples": 1300.0} and avisos[-1] == {"simples": 1300.0}
        antes = len(avisos)
        await t.cancelar("cancela o timer")
        assert t.fins() == {} and len(avisos) > antes and avisos[-1] == {}
    asyncio.run(cena())


def test_timer_simples_que_dispara_sai_de_fins_e_avisa():
    rodar, _ = gravador()
    async def cena():
        t, avisos = Timers(rodar, dormir=sem_espera, agora=lambda: 1000.0), []
        t.observar(lambda: avisos.append(dict(t.fins())))
        t.conectar(lambda: asyncio.sleep(0))
        await t.armar(PedidoTimer(5, False, False))
        await girar()
        assert t.fins() == {} and avisos[-1] == {}
    asyncio.run(cena())


def test_desobservar_so_solta_o_mesmo_callback():
    rodar, _ = gravador()
    async def cena():
        t, a, b = Timers(rodar, dormir=lambda _s: asyncio.Event().wait()), [], []
        fa, fb = lambda: a.append(1), lambda: b.append(1)
        t.observar(fa)
        t.observar(fb)
        t.desobservar(fa)  # o antigo chegando tarde: não apaga o novo
        await t.armar(PedidoTimer(5, False, False))
        assert a == [] and b
        n = len(b)
        t.desobservar(fb)
        await t.cancelar("cancela o timer")
        assert len(b) == n
    asyncio.run(cena())


def test_fim_do_desligar_e_observador_que_levanta_nao_quebra():
    rodar, _ = gravador()
    def ruim():
        raise RuntimeError("x")
    async def cena():
        t = Timers(rodar, agora=lambda: 1000.0)
        t.observar(ruim)
        assert await t.armar(PedidoTimer(30, True, False))
        assert t.fins() == {"desligar": 1000.0 + 60 * 30}
        assert await t.cancelar("cancela o desligar") == "desligar" and t.fins() == {}
    asyncio.run(cena())
