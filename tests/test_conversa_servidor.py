import asyncio
import re
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("pipecat")

from fastapi.testclient import TestClient
from loguru import logger

from src.conversa import servidor
from src.conversa.servidor import criar_app, montar_coletor
from src.vida.banco import Banco

RAIZ = Path(__file__).parent.parent


@pytest.fixture
def restaurar_log():
    yield
    logger.remove()
    logger.add(sys.stderr)


@pytest.fixture
def log_em_lista(monkeypatch, restaurar_log):
    monkeypatch.delenv("GROOV_LOG", raising=False)
    lista = []
    servidor.configurar_log(lista.append)
    yield lista


def test_log_nao_grava_variaveis_locais(log_em_lista):
    def falha():
        conteudo = "MARCADOR-SENSIVEL"
        raise ValueError("falhou" + conteudo[:0])  # a variável aparece na linha que falha: o diagnose a gravaria
    try:
        falha()
    except ValueError:
        logger.exception("erro na fonte")
    texto = "".join(log_em_lista)
    assert "falhou" in texto and "MARCADOR-SENSIVEL" not in texto


def test_log_omite_texto_dos_modulos_do_pipecat(log_em_lista):
    logger.patch(lambda r: r.update(name="pipecat.services.tts_service")).warning("vou falar MARCADOR-SENSIVEL")
    texto = "".join(log_em_lista)
    assert "MARCADOR-SENSIVEL" not in texto and "texto omitido" in texto


def test_log_fica_em_info_por_padrao(log_em_lista):
    logger.debug("so-debug")
    logger.info("so-info")
    texto = "".join(log_em_lista)
    assert "so-debug" not in texto and "so-info" in texto


def test_log_de_medicao_em_debug_tambem_omite_o_system(restaurar_log):
    lista = []
    servidor.configurar_log(lista.append, "DEBUG")
    logger.patch(lambda r: r.update(name="pipecat.services.openai.base_llm")).debug("Using system instruction: MARCADOR-PERFIL")
    logger.debug("Transcription: ola")
    texto = "".join(lista)
    assert "MARCADOR-PERFIL" not in texto and "Transcription: ola" in texto


def cliente():
    # o servidor só aceita Host localhost:7860 (anti DNS rebinding); o TestClient usa "testserver" por padrão
    return TestClient(criar_app(bot=lambda args: None), base_url="http://localhost:7860")


def test_raiz_serve_a_janela():
    r = cliente().get("/")
    assert r.status_code == 200 and "<title>GROOV</title>" in r.text
    assert r.headers["content-security-policy"] == servidor.CSP


def test_scripts_da_janela_levam_versao():
    """14/11: o no-cache não alcança o JS que já estava no cache: o endereço muda a cada início do servidor."""
    html = cliente().get("/").text
    assert 'src="/janela/cromo.js?v=' in html and 'src="/ds/_ds_bundle.js?v=' in html and 'href="/janela/groov.css?v=' in html
    assert cliente().get("/janela/cromo.js?v=1").status_code == 200


def test_janela_sem_cache():
    """14/11: a janela rodava o telas.js antigo do cache do Chrome depois de atualizar o GROOV."""
    c = cliente()
    for caminho in ["/", "/janela/telas.js", "/ds/tokens/motion.css"]:
        assert c.get(caminho).headers.get("cache-control") == "no-cache", caminho


def test_titulo_da_janela_depende_da_porta():
    """A tela acha a janela pelo título: o teste em outra porta não pode ter o título da janela de verdade."""
    assert "<title>GROOV</title>" in cliente().get("/").text
    c = TestClient(criar_app(bot=lambda args: None, porta=7861), base_url="http://localhost:7861")
    assert "<title>GROOV :7861</title>" in c.get("/").text


def test_main_liga_a_tela_da_porta_do_servidor(monkeypatch):
    import uvicorn

    from src.conversa import servidor, tela

    ligadas = []
    monkeypatch.setattr(tela, "ativar", lambda porta, backend=None: ligadas.append(porta))
    monkeypatch.setattr(uvicorn.Server, "run", lambda self, *a, **k: None)
    servidor.main()
    assert ligadas == [servidor.PORTA]


def test_serve_o_que_a_janela_precisa():
    c = cliente()
    for caminho in ["/ds/styles.css", "/ds/tokens/colors.css", "/ds/assets/fonts/Michroma-400.woff2",
                    "/janela/vendor/react.production.min.js", "/janela/icones/power.svg"]:
        assert c.get(caminho).status_code == 200, caminho
    assert "<svg" in c.get("/janela/icones/power.svg").text


def test_do_design_system_so_sai_o_publico():
    c = cliente()
    for caminho in ["/ds/components/core/Icon.jsx", "/ds/readme.md", "/ds/ui_kits/groov-hud/App.jsx",
                    "/ds/assets/reference/idle-screen.png", "/ds/../CLAUDE.md"]:
        assert c.get(caminho).status_code == 404, caminho


def test_prefixo_publico_nao_leva_a_arquivo_interno():
    """A lista vale para o caminho já resolvido: `tokens/..` não pode abrir o resto da pasta."""
    c = cliente()
    for caminho in ["/ds/tokens/%2e%2e/readme.md", "/ds/tokens/%2e%2e/components/core/Icon.jsx",
                    "/ds/assets/fonts/%2e%2e/%2e%2e/readme.md", "/ds/tokens%5C..%5Creadme.md"]:
        assert c.get(caminho).status_code == 404, caminho
    # o bundle é público: pelo atalho `tokens/..` sai o mesmo, já com a troca (nunca o cru com a URL da internet)
    r = c.get("/ds/tokens/%2e%2e/_ds_bundle.js")
    assert r.status_code == 200 and "https://" not in r.text


def test_bundle_sai_com_os_icones_locais_e_sem_internet():
    r = cliente().get("/ds/_ds_bundle.js")
    assert r.status_code == 200 and "javascript" in r.headers["content-type"]
    assert "/janela/icones/" in r.text and "https://" not in r.text


def test_nada_da_internet_na_janela():
    for arquivo in servidor.JANELA.rglob("*"):
        if not arquivo.is_file() or "vendor" in arquivo.relative_to(servidor.JANELA).parts:
            continue
        if arquivo.suffix in (".js", ".html", ".css"):
            texto = arquivo.read_text(encoding="utf-8")
            assert "http://" not in texto and "https://" not in texto, arquivo
        elif arquivo.suffix == ".svg":
            urls = re.findall(r"https?://[^\s\"'<>)]+", arquivo.read_text(encoding="utf-8"))
            assert set(urls) <= {"http://www.w3.org/2000/svg"}, arquivo


def test_encerrar_fecha_a_janela_e_para_o_servidor():
    falso, chamadas = SimpleNamespace(should_exit=False), []
    servidor.criar_encerrar(falso, lambda: chamadas.append(1))()
    assert falso.should_exit is True and chamadas == [1]

    def estoura():
        raise OSError("janela sumiu")

    falso = SimpleNamespace(should_exit=False)
    servidor.criar_encerrar(falso, estoura)()
    assert falso.should_exit is True


def test_nao_sai_da_pasta_do_design_system():
    c = cliente()
    for caminho in ["/ds/../privado/.env", "/ds/..%2Fprivado%2F.env", "/ds/../ESTADO.md",
                    "/ds/uploads/x.png", "/ds/tokens/../../ESTADO.md", "/ds/tokens/%2e%2e/%2e%2e/ESTADO.md",
                    "/janela/../servidor.py", "/janela/..%2Fservidor.py"]:
        assert c.get(caminho).status_code == 404, caminho


def test_janela_nao_usa_cdn():
    texto = cliente().get("/").text + cliente().get("/janela/vendor/react.production.min.js").text
    assert "unpkg" not in texto and "cdn" not in texto.lower() and "http://" not in texto and "https://" not in texto


def test_so_escuta_em_localhost():
    from src.conversa import servidor
    assert servidor.HOST == "127.0.0.1" and servidor.PORTA == 7860


def test_recusa_host_estranho_e_origem_de_outro_site():
    app = criar_app(bot=lambda args: None)
    assert TestClient(app, base_url="http://evil.example:7860").get("/").status_code == 403
    assert cliente().get("/", headers={"Origin": "https://evil.example"}).status_code == 403
    assert cliente().get("/", headers={"Origin": "http://localhost:7860"}).status_code == 200


def test_oferta_nova_derruba_a_conexao_anterior():
    """Review Focus 2: janela recarregada ou 2ª aba -> o pipeline antigo acaba antes de o novo começar."""
    import asyncio
    import socket

    import httpx
    import uvicorn
    from aiortc import RTCConfiguration, RTCPeerConnection, RTCSessionDescription
    from aiortc.mediastreams import AudioStreamTrack

    eventos = []
    avisos = []

    async def bot(args):
        conexao = args.webrtc_connection
        fechou = asyncio.Event()

        @conexao.event_handler("closed")
        async def ao_fechar(_):
            fechou.set()

        eventos.append("abriu")
        await fechou.wait()
        eventos.append("acabou")

    async def conectar(porta):
        pc = RTCPeerConnection(RTCConfiguration(iceServers=[]))  # o padrão do aiortc consulta o STUN do Google
        pc.addTransceiver(AudioStreamTrack(), direction="sendrecv")
        canal = pc.createDataChannel("chat")
        pc.recebidas = []
        canal.on("message", lambda m: pc.recebidas.append(m))
        await pc.setLocalDescription(await pc.createOffer())
        async with httpx.AsyncClient() as http:
            r = await http.post(f"http://127.0.0.1:{porta}/api/offer", timeout=20,
                                json={"sdp": pc.localDescription.sdp, "type": pc.localDescription.type})
        r.raise_for_status()
        await pc.setRemoteDescription(RTCSessionDescription(r.json()["sdp"], r.json()["type"]))
        while canal.readyState != "open":
            await asyncio.sleep(0.05)
        return pc

    async def cenario():
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            porta = s.getsockname()[1]
        servidor = uvicorn.Server(uvicorn.Config(criar_app(bot=bot, porta=porta), host="127.0.0.1",
                                                 port=porta, log_level="warning"))
        tarefa = asyncio.create_task(servidor.serve())
        while not servidor.started:
            await asyncio.sleep(0.05)
        try:
            primeiro = await conectar(porta)
            segundo = await conectar(porta)
            await asyncio.sleep(0.5)
            avisos.extend(primeiro.recebidas)
            await primeiro.close()
            await segundo.close()
        finally:
            servidor.should_exit = True
            await tarefa

    asyncio.run(cenario())
    assert eventos[:3] == ["abriu", "acabou", "abriu"], eventos
    # a janela derrubada precisa saber que foi substituída, senão reconecta e as duas brigam sem parar
    assert any("peerLeft" in m for m in avisos), avisos


def test_sem_stdout_do_pythonw_o_uvicorn_ainda_configura_o_log(monkeypatch, tmp_path):
    """O atalho de início roda pythonw (sys.stdout/stderr = None): o uvicorn quebrava no isatty()."""
    import sys

    import uvicorn
    from fastapi import FastAPI

    from src.conversa import servidor

    monkeypatch.setattr(servidor, "LOG", tmp_path / "conversa.log")
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    assert servidor.garantir_saida() is True
    try:
        uvicorn.Config(FastAPI()).configure_logging()  # levantava ValueError: Unable to configure formatter
        assert sys.stdout is not None and sys.stderr is not None
    finally:
        sys.stdout.close()


def test_com_stdout_normal_garantir_saida_nao_mexe_em_nada():
    from src.conversa import servidor

    assert servidor.garantir_saida() is False


def test_coletor_roda_no_ciclo_de_vida_e_para_no_fim():
    estados = []

    class Falso:
        async def rodar(self):
            estados.append("rodando")
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                estados.append("parou")
                raise

    app = criar_app(bot=lambda args: None, coletor=Falso())
    with TestClient(app, base_url="http://localhost:7860") as c:
        c.get("/")
        time.sleep(0.1)
    assert estados == ["rodando", "parou"]


def env_do_usuario(tmp_path, texto):
    (tmp_path / "privado").mkdir(exist_ok=True)
    (tmp_path / "privado" / ".env").write_text(texto, encoding="utf-8")


def test_montar_coletor_sem_chaves_fica_sem_fontes(tmp_path):
    env_do_usuario(tmp_path, "GROQ_API_KEY=x\n")
    avisos = []
    c = montar_coletor(tmp_path, avisar=avisos.append)
    assert c is not None and c.fontes == [] and avisos == ["coletor: Trello sem chave no .env"]


def test_montar_coletor_com_trello_tem_uma_fonte(tmp_path):
    env_do_usuario(tmp_path, "TRELLO_KEY=k\nTRELLO_TOKEN=t\nTRELLO_QUADROS=Projeto 2026,Empresa X — Prospecção\n")
    avisos = []
    c = montar_coletor(tmp_path, avisar=avisos.append)
    assert [f.nome for f in c.fontes] == ["trello"] and avisos == [] and c.trava is not None


def test_segundo_servidor_so_le_o_banco(tmp_path):
    (tmp_path / "privado").mkdir()
    codigo = ("import pathlib, sys; from src.vida.trava import travar; "
              "f = travar(pathlib.Path(sys.argv[1])); print(f is not None, flush=True); sys.stdin.readline()")
    outro = subprocess.Popen([sys.executable, "-c", codigo, str(tmp_path / "privado" / "coletor.lock")],
                             cwd=RAIZ, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        assert outro.stdout.readline().strip() == "True"  # o outro processo está com a trava
        avisos = []
        c = montar_coletor(tmp_path, avisar=avisos.append)
        assert c.fontes == [] and isinstance(c.banco, Banco)
        assert avisos == ["coletor: já roda em outro servidor; este só lê o banco"]
    finally:
        outro.stdin.write("\n")
        outro.stdin.close()
        outro.wait(timeout=10)


def test_montar_coletor_sem_pasta_privado_nao_derruba_o_servidor(tmp_path):
    avisos = []
    assert montar_coletor(tmp_path / "nao-existe", avisar=avisos.append) is None
    assert avisos == ["coletor: banco não abriu (OperationalError); sem coletor"]


def test_coletor_que_morre_vai_para_o_log_sem_o_texto(log_em_lista):
    class Falso:
        async def rodar(self):
            raise RuntimeError("SEGREDO no erro")

    app = criar_app(bot=lambda args: None, coletor=Falso())
    with TestClient(app, base_url="http://localhost:7860") as c:
        c.get("/")
        time.sleep(0.2)
    texto = "".join(log_em_lista)
    assert "coletor parou (RuntimeError)" in texto and "SEGREDO" not in texto


def test_log_omite_o_traceback_dos_modulos_do_pipecat(log_em_lista):
    try:
        raise ValueError("SEGREDO-NO-ERRO")
    except ValueError:
        logger.patch(lambda r: r.update(name="pipecat.services.tts_service")).exception("falhou")
    texto = "".join(log_em_lista)
    assert "SEGREDO-NO-ERRO" not in texto and "texto omitido" in texto


def test_log_do_laco_chega_ao_arquivo_so_com_a_mensagem(log_em_lista):
    """Os logs do laço, do PC e dos timers usam `logging` (jarvis.*): sem a ponte nada deles chegava ao conversa.log."""
    import logging

    logging.getLogger("groov.laco").info("laço terminou: respondeu, 3 passos, 0 chamadas ao Claude")
    try:
        raise ValueError("TEXTO-DE-JANELA")
    except ValueError:
        logging.getLogger("groov.pc").warning("sonda ler: estourou o teto", exc_info=True)
    texto = "".join(log_em_lista)
    assert "laço terminou: respondeu, 3 passos" in texto and "sonda ler: estourou o teto" in texto
    assert "TEXTO-DE-JANELA" not in texto and "Traceback" not in texto  # nunca o traceback: pode trazer conteúdo


def test_ponte_do_log_nao_duplica_ao_configurar_de_novo(log_em_lista):
    import logging

    servidor.configurar_log(log_em_lista.append)
    logging.getLogger("groov.timers").info("uma vez só")
    assert "".join(log_em_lista).count("uma vez só") == 1


def test_montar_coletor_passa_os_quadros_de_contagem(tmp_path, monkeypatch):
    env_do_usuario(tmp_path, "TRELLO_KEY=k\nTRELLO_TOKEN=t\nTRELLO_QUADROS=Projeto 2026,Empresa X — Prospecção\n"
                             "TRELLO_QUADROS_CONTAGEM=Empresa X — Prospecção\n")
    vistos = []
    original = servidor.fonte_trello
    monkeypatch.setattr(servidor, "fonte_trello", lambda *a, **k: vistos.append(k.get("contagem")) or original(*a, **k))
    montar_coletor(tmp_path, avisar=lambda m: None)
    assert vistos == [["Empresa X — Prospecção"]]
