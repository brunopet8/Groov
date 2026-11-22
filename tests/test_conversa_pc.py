import asyncio
import dataclasses
import json
import os
import shutil
import subprocess
import sys
import textwrap
import time

import pytest

from src.conversa import pc
from src.conversa.pc import ErroSonda, Falso, Leitura, Midia, Sonda, janela_da_aba, janela_nova
from src.conversa.regras_pc import Elemento

WIN = pytest.mark.skipif(sys.platform != "win32", reason="UI Automation só no Windows")


def rodar(coro):
    return asyncio.run(coro)


# --- janela_nova: a diferença de HWND ---

class Janelas:
    def __init__(self, *sequencia):
        self.sequencia = list(sequencia)

    async def janelas(self):
        return frozenset(self.sequencia.pop(0) if len(self.sequencia) > 1 else self.sequencia[0])


def nova(backend, antes, **k):
    return rodar(janela_nova(backend, frozenset(antes), prazo=1, passo=0, assentar=0, **k))


def test_janela_nova_exatamente_uma():
    assert nova(Janelas({1, 2}, {1, 2}, {1, 2, 9}, {1, 2, 9}), {1, 2}) == 9


def test_janela_nova_duas_devolve_none():  # Chrome restaurando a sessão abre duas
    assert nova(Janelas({1}, {1, 8}, {1, 8, 9}), {1}) is None


def test_janela_nova_nenhuma_estoura_o_prazo():
    assert nova(Janelas({1}), {1}) is None


def test_janela_nova_exclui_a_do_groov():
    assert nova(Janelas({1, 5, 9}), {1}, excluir=frozenset({5})) == 9



# --- janela_da_aba: aba nova na janela do usuário, ou janela nova com o Chrome fechado ---

def aba(plano, leituras, antes, host="github.com", janelas=None, **k):
    fb = Falso(leituras=leituras, janelas=janelas or [frozenset(antes)], plano=plano)
    return rodar(janela_da_aba(fb, frozenset(antes), host, prazo=0.05, passo=0, assentar=0, **k))


def test_aba_acha_janela_em_primeiro_plano():
    ler = Leitura(2, "www.github.com/", "t", "x", (), False)
    assert aba(2, [ler], {1, 2}) == 2
    assert aba(2, [Leitura(2, "gist.github.com/", "t", "x", (), False)], {1, 2}) == 2  # subdomínio
    assert aba(2, [Leitura(2, "github.com/", "t", "x", (), False)], {1, 2}, host="docs.github.com") == 2  # redirecionou
    assert aba(2, [Leitura(2, "g1.globo.com/", "t", "x", (), False)], {1, 2}) is None  # outra página
    assert aba(2, [ler], {1, 2}, excluir=frozenset({2})) is None


def test_aba_acha_janela_do_chrome_em_segundo_plano():
    """Rodada de 09/11: a aba nova abriu numa janela do Chrome que ficou atrás; o primeiro plano era outra."""
    ler = Leitura(2, "www.github.com/", "t", "x", (), False)
    assert aba(9, [ler], {1, 2}) == 2  # o Falso devolve a leitura da janela 2 só para o hwnd 2
    assert aba(9, [Leitura(2, "g1.globo.com/", "t", "x", (), False)], {1, 2}) is None
    assert aba(9, [ler], {1, 2}, excluir=frozenset({2})) is None


def test_aba_atras_em_duas_janelas_no_mesmo_site_nao_escolhe():
    """Revisor: a janela antiga do usuário já no Gmail não pode passar pela aba nova aberta em outra janela."""
    class PorJanela(Falso):
        async def ler(self, hwnd):
            return Leitura(hwnd, "mail.google.com/mail/u/0/", "t", "x", (), False)
    fb = PorJanela(janelas=[frozenset({1, 2})], plano=9)
    assert rodar(janela_da_aba(fb, frozenset({1, 2}), "mail.google.com", prazo=0.05, passo=0, assentar=0)) is None


def test_falso_trazer_poe_em_primeiro_plano():
    fb = Falso(plano=0)
    assert rodar(fb.trazer(7)) and rodar(fb.primeiro_plano()) == 7 and ("trazer", 7) in fb.chamadas
    fb = Falso(plano=0)
    fb.trazer_ok = False
    assert not rodar(fb.trazer(7)) and rodar(fb.primeiro_plano()) == 0


def test_aba_chrome_fechado_usa_janela_nova():
    fb = Falso(janelas=[frozenset({1}), frozenset({1, 9}), frozenset({1, 9})], plano=1)
    assert rodar(janela_da_aba(fb, frozenset({1}), "github.com", prazo=1, passo=0, assentar=0)) == 9


# --- processo da sonda, sem PowerShell: comando falso ---

ECO = ("import sys,json,os; d=json.loads(sys.stdin.buffer.read().decode('utf-8'))\n"
       "print(json.dumps({'ok': True, 'recebido': d, 'argv': sys.argv[1:], 'tem_groq': 'GROQ_API_KEY' in os.environ}))")


def fake(codigo=ECO, **k):
    return Sonda(comando=[sys.executable, "-c", codigo], titulo_groov="GROOV", **k)


def resposta(obj, **k):
    return fake("import sys,json; sys.stdin.buffer.read(); print(json.dumps(" + repr(obj) + "))", **k)


def test_pedido_vai_pelo_stdin_nao_no_argv():
    r = rodar(fake()._chamar("clicar", hwnd=5, nome="Segredo ç ação", runtime_id="1.2"))
    assert r["argv"] == []
    assert r["recebido"]["nome"] == "Segredo ç ação" and r["recebido"]["op"] == "clicar"


def test_sonda_sem_segredo_no_ambiente(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "nao-vazar")
    assert rodar(fake()._chamar("janelas"))["tem_groq"] is False


def espiar_matar(monkeypatch):
    mortos = []
    original = pc._matar
    def espia(proc):
        mortos.append(proc)
        original(proc)
    monkeypatch.setattr(pc, "_matar", espia)
    return mortos


def test_sonda_estoura_e_mata(monkeypatch):
    mortos = espiar_matar(monkeypatch)
    s = fake("import time; time.sleep(60)", teto=0.5)
    t0 = time.monotonic()
    with pytest.raises(ErroSonda):
        rodar(s._chamar("janelas"))
    assert time.monotonic() - t0 < 10 and len(mortos) == 1 and mortos[0].returncode is not None


def test_cancelar_mata_sonda_em_curso(monkeypatch):
    mortos = espiar_matar(monkeypatch)
    async def cena():
        t = asyncio.create_task(fake("import time; time.sleep(60)", teto=30)._chamar("janelas"))
        await asyncio.sleep(1)
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t
        await asyncio.wait_for(mortos[0].wait(), 5)
    rodar(cena())
    assert len(mortos) == 1 and mortos[0].returncode is not None


def test_erro_da_sonda_nao_vaza_texto():
    s = resposta({"erro": "COMException"})
    with pytest.raises(ErroSonda, match="COMException"):
        rodar(s._chamar("ler"))


def test_saida_com_codigo_de_erro_e_lixo():
    with pytest.raises(ErroSonda):
        rodar(fake("import sys; sys.exit(3)")._chamar("ler"))
    with pytest.raises(ErroSonda):
        rodar(fake("import sys; sys.stdin.buffer.read(); print('nao e json')")._chamar("ler"))


def test_acao_que_falha_devolve_falso_sem_levantar():
    el = Elemento(id=1, nome="Abrir", tipo="Button", runtime_id="1.2")
    assert rodar(fake("import sys; sys.exit(3)").clicar(1, el, None)) is False
    assert rodar(resposta({"ok": False, "motivo": "mudou"}).clicar(1, el, None)) is False
    assert rodar(resposta({"ok": True}).clicar(1, el, None)) is True


def test_acao_manda_a_conferencia_no_ato():
    el = Elemento(id=1, nome="Abrir", tipo="Button", runtime_id="1.2")
    chamado = {}
    async def _chamar(op, teto=None, **dados):
        chamado.update(op=op, **dados)
        return {"ok": True}
    s = Sonda()
    s._chamar = _chamar
    rodar(s.buscar(7, el, "kanata", "netflix.com/browse"))
    assert chamado == {"op": "buscar", "hwnd": 7, "endereco": "netflix.com/browse", "texto": "kanata",
                       "runtime_id": "1.2", "nome": "Abrir", "tipo": "Button"}


def test_ler_converte_a_resposta():
    s = resposta({"hwnd": 7, "endereco": "g1.globo.com", "titulo": "G1", "texto": "Manchete", "cortado": True, "elementos": [
        {"id": 1, "nome": "Manchete", "tipo": "Hyperlink", "papel": "link", "texto_interno": "x", "ancestrais": ["Topo"],
         "senha": False, "runtime_id": "42.9", "host_do_link": "g1.globo.com"},
        {"id": 2, "nome": "Busca", "tipo": "Edit", "papel": "editar", "texto_interno": "", "ancestrais": "Unico", "senha": False,
         "runtime_id": "42.10", "host_do_link": None}]})
    leitura = rodar(s.ler(7))
    assert isinstance(leitura, Leitura) and leitura.cortado and leitura.endereco == "g1.globo.com"
    assert leitura.elementos[0] == Elemento(1, "Manchete", "Hyperlink", "link", "x", ("Topo",), False, "42.9", "g1.globo.com")
    assert leitura.elementos[1].ancestrais == ("Unico",)  # o PowerShell desenrola lista de um item


def test_midias_converte_e_falha_vira_vazio():
    s = resposta({"midias": [{"app": "SpotifyAB.SpotifyMusic_zpdnekdrzrea0!Spotify", "tocando": True, "titulo": "t", "artista": "a"}]})
    assert rodar(s.midias()) == (Midia("SpotifyAB.SpotifyMusic_zpdnekdrzrea0!Spotify", True, "t", "a"),)
    assert rodar(fake("import sys; sys.exit(1)").midias()) == ()


def test_som_pelo_limiar_e_falha_diz_que_ha_som():
    assert rodar(resposta({"picos": [{"processo": "Spotify", "pico": 0.198}]}).som_tocando()) is True
    assert rodar(resposta({"picos": [{"processo": "Spotify", "pico": 0.0}, {"processo": "chrome", "pico": 0.004}]}).som_tocando()) is False
    assert rodar(resposta({"picos": []}).som_tocando()) is False
    assert rodar(fake("import sys; sys.exit(1)").som_tocando()) is True


def test_som_ignora_o_proprio_processo():
    s = fake()
    chamado = {}
    async def _chamar(op, teto=None, **dados):
        chamado.update(dados)
        return {"picos": []}
    s._chamar = _chamar
    rodar(s.som_tocando())
    import os
    assert chamado["ignorar_pids"] == [os.getpid()]


def test_envio_converte_e_ausente_vira_none():
    assert rodar(resposta({"envio": {"destino": "Ana", "texto": "oi", "anexos": 0, "cc": ""}}).envio(1)) == pc.Envio("Ana", "oi", 0, "")
    assert rodar(resposta({"envio": None}).envio(1)) is None


def sonda_que_anota():
    chamado = []
    async def _chamar(op, teto=None, **dados):
        chamado.append((op, dados))
        return {"hwnd": 77}
    s = Sonda(apps={"spotify": ("Spotify", "C:/x/Spotify.exe")})
    s._chamar = _chamar
    return s, chamado


def test_abrir_app_apelido_usa_o_executavel_da_tabela():
    s, chamado = sonda_que_anota()
    assert rodar(s.abrir_app(" Spotify ")) == 77 and chamado == [("abrir_app", {"processo": "Spotify", "exe": "C:/x/Spotify.exe"})]


def test_abrir_app_fora_da_tabela_abre_pelo_nome_e_a_janela_passa_a_ser_listada():
    s, chamado = sonda_que_anota()
    assert rodar(s.abrir_app("WhatsApp")) == 77 and chamado == [("abrir_app", {"processo": "whatsapp", "exe": ""})]
    assert "whatsapp" in s.listadas


@pytest.mark.parametrize("nome", [r"C:\Windows\System32\cmd.exe","cmd /c calc", "/bin/sh", "-Command x", "app;calc", "app&calc",
                                  "app|calc", "$(calc)", "a`b", 'app"x', r"..\app", "a..b", "", "x" * 41, "app*", "app?", "app>x",
                                  "https://x.com", "app\ncalc", "consent", "LogonUI"])
def test_abrir_app_recusa_nome_com_caminho_opcao_ou_metacaractere(nome):
    s, chamado = sonda_que_anota()
    assert rodar(s.abrir_app(nome)) is None and chamado == []


@pytest.mark.parametrize("nome", ["Edge", "Microsoft Edge", "msedge", "Firefox", "opera gx", "Brave", "vivaldi", "iexplore", "Internet Explorer"])
def test_abrir_app_recusa_outros_navegadores(nome):
    s, chamado = sonda_que_anota()
    assert rodar(s.abrir_app(nome)) is None and chamado == []


def test_janelas_acrescenta_so_o_alvo_de_nome_simples():
    s, chamado = sonda_que_anota()
    s._chamar = lambda op, **d: chamado.append(d) or _vazio()
    async def _vazio():
        return {"janelas": []}
    rodar(s.janelas("notepad")); rodar(s.janelas("a;b"))
    assert chamado[0]["listadas"][-1] == "notepad" and "a;b" not in chamado[1]["listadas"]


def test_abrir_site_perfil_normal_aba_nova_sem_segredo(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "nao-vazar")
    achado = {}
    def popen(args, **k):
        achado.update(args=args, **k)
    monkeypatch.setattr(pc.subprocess, "Popen", popen)
    s = Sonda(chrome="C:/chrome.exe")
    rodar(s.abrir_site("https://netflix.com/"))
    # aba nova na janela dele, sem --new-window; a flag esconde a barra "começou a depurar" quando é este comando que abre o Chrome
    assert achado["args"] == ["C:/chrome.exe", "--silent-debugger-extension-api", "https://netflix.com/"]
    assert "GROQ_API_KEY" not in achado["env"]
    for url in ("file:///c:/x", "--user-data-dir=x", "javascript:alert(1)"):
        with pytest.raises(ValueError):
            rodar(s.abrir_site(url))


@WIN
def test_primeiro_plano_devolve_inteiro():
    assert isinstance(rodar(Sonda().primeiro_plano()), int)


def test_falso_roteirizado_grava_as_chamadas():
    f = Falso(leituras=[Leitura(1, None, "t", "x", (), False)])
    assert rodar(f.ler(1)).texto == "x" and rodar(f.clicar(1, Elemento(1, "a", "Button"), None)) and f.chamadas[0] == ("ler", 1)


# --- UI Automation de verdade, só numa janela WinForms própria (Tk não serve: a UIA só vê Panes sem nome) ---

FORM = r"""
param([string]$Dir, [switch]$Frente, [switch]$Chrome)
Add-Type -AssemblyName PresentationFramework, PresentationCore, WindowsBase
Add-Type -Namespace T -Name U -MemberDefinition '[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h); [DllImport("user32.dll")] public static extern IntPtr SetFocus(IntPtr h); [DllImport("user32.dll")] public static extern IntPtr GetFocus(); [DllImport("user32.dll")] public static extern void keybd_event(byte v, byte s, uint f, UIntPtr e);'
$global:Dir = $Dir
$global:w = New-Object System.Windows.Window
$w.ShowActivated = [bool]$Frente  # sem -Frente a janela nasce sem roubar o foco de quem esta usando o PC
$w.Title = 'Janela de teste pc'; $w.Width = 420; $w.Height = 360; $w.WindowStartupLocation = 'CenterScreen'
$global:pilha = New-Object System.Windows.Controls.StackPanel
$w.Content = $pilha
function Registrar($c) { $c.Add_Click({ param($s, $e) Add-Content -Path (Join-Path $global:Dir 'log.txt') -Value ('clique:' + $s.Content + ':' + $s.Tag) }) }
function Botao($texto, $tag) { $b = New-Object System.Windows.Controls.Button; if ($texto) { $b.Content = $texto }; $b.Tag = $tag; $global:pilha.Children.Add($b) | Out-Null; $b }
function Campo($tipo, $nome, $texto) { $c = New-Object $tipo; [System.Windows.Automation.AutomationProperties]::SetName($c, $nome); if ($texto) { $c.Text = $texto }; $global:pilha.Children.Add($c) | Out-Null; $c }
$global:b1 = Botao 'Abrir' 'primeiro'; Registrar $b1
$global:b2 = Botao '' ''
$global:tb = Campo System.Windows.Controls.TextBox 'Pesquisar' ''
$null = Campo System.Windows.Controls.TextBox 'Para' 'ana@example.com'
$null = Campo System.Windows.Controls.TextBox 'Corpo da mensagem' 'chego as 8'
$senha = New-Object System.Windows.Controls.PasswordBox; [System.Windows.Automation.AutomationProperties]::SetName($senha, 'Senha'); $pilha.Children.Add($senha) | Out-Null
if ($Chrome) {
    # Chrome de mentira: o exe se chama chrome.exe; moldura (endereco + Voltar desligado) fora do Document, controles e um "Voltar" da pagina dentro
    $fd = New-Object System.Windows.Documents.FlowDocument
    $pv = Botao 'Voltar' 'pagina'; Registrar $pv
    foreach ($c in @($pilha.Children)) { $pilha.Children.Remove($c); $fd.Blocks.Add((New-Object System.Windows.Documents.BlockUIContainer($c))) }
    $global:addr = New-Object System.Windows.Controls.TextBox; $addr.Text = 'exemplo.com/a'
    [System.Windows.Automation.AutomationProperties]::SetName($addr, 'Barra de endereco e de pesquisa')
    $global:vf = New-Object System.Windows.Controls.Button; $vf.Content = 'Voltar'; $vf.Tag = 'frame'; $vf.IsEnabled = $false; Registrar $vf
    $vw = New-Object System.Windows.Controls.FlowDocumentScrollViewer; $vw.Document = $fd; $vw.Height = 200
    $pilha.Children.Add($addr) | Out-Null; $pilha.Children.Add($vf) | Out-Null; $pilha.Children.Add($vw) | Out-Null
}
$tb.Add_PreviewKeyDown({ param($s, $e) try { Add-Content -Path (Join-Path $global:Dir 'teclas.txt') -Value ([string]$e.Key + '@' + [Environment]::TickCount); if ($e.Key -eq [System.Windows.Input.Key]::Return) { Add-Content -Path (Join-Path $global:Dir 'log.txt') -Value ('enter:' + $global:tb.Text) } } catch { Add-Content -Path (Join-Path $global:Dir 'erros.txt') -Value ($_ | Out-String) } })
$tm = New-Object System.Windows.Threading.DispatcherTimer; $tm.Interval = [TimeSpan]::FromMilliseconds(100)
$tm.Add_Tick({
    $cmd = Join-Path $global:Dir 'cmd.txt'
    if (-not (Test-Path $cmd)) { return }
    $c = (Get-Content $cmd -Raw).Trim(); Remove-Item $cmd
    if ($c -eq 'renomear') { $global:b1.Content = 'Outro' }
    if ($c -eq 'duplicar') { $b3 = Botao 'Abrir' 'segundo'; Registrar $b3 }
    if ($c -eq 'fundo') { $global:w.WindowState = 'Minimized' }
    if ($c -eq 'voltar_on') { $global:vf.IsEnabled = $true }
    if ($c -eq 'endereco') { $global:addr.Text = 'outro.com/b' }
    if ($c -eq 'dump') { Set-Content -Path (Join-Path $global:Dir 'dump.txt') -Value $global:tb.Text -NoNewline }
})
$tm.Start()
$w.Add_ContentRendered({
    $h = (New-Object System.Windows.Interop.WindowInteropHelper($global:w)).Handle
    if ($Frente) {
        $global:w.Topmost = $true
        [T.U]::keybd_event(0x12, 0, 0, [UIntPtr]::Zero); [void][T.U]::SetForegroundWindow($h); [T.U]::keybd_event(0x12, 0, 2, [UIntPtr]::Zero)
        $global:w.Activate()
        [void][T.U]::SetFocus($h)
        $global:tb.Focus() | Out-Null
    }
    Set-Content -Path (Join-Path $global:Dir 'hwnd.txt') -Value $h.ToInt64() -NoNewline
})
[void]$w.ShowDialog()
"""


class FormWin:
    def __init__(self, pasta, frente=False, chrome=False):
        self.pasta = pasta
        script = pasta / "form.ps1"
        script.write_text(FORM, encoding="ascii")
        exe = "powershell"
        if chrome:  # processo chamado "chrome": a sonda o trata como Chrome (Document, endereco, conferencia)
            exe = str(pasta / "chrome.exe")
            shutil.copy(shutil.which("powershell"), exe)
        self.proc = subprocess.Popen(
            [exe, "-STA", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script), str(pasta), *(["-Frente"] if frente else []), *(["-Chrome"] if chrome else [])],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
        fim = time.monotonic() + 30
        while not (pasta / "hwnd.txt").exists():
            if time.monotonic() > fim or self.proc.poll() is not None:
                self.fechar()
                pytest.fail("a janela de teste não abriu")
            time.sleep(0.2)
        self.hwnd = int((pasta / "hwnd.txt").read_text())
        self.sonda = Sonda(titulo_groov="GROOV", processos_extras=("powershell",))

    def comando(self, c):
        (self.pasta / "cmd.txt").write_text(c, encoding="ascii")
        fim = time.monotonic() + 10
        while (self.pasta / "cmd.txt").exists() and time.monotonic() < fim:
            time.sleep(0.1)
        time.sleep(0.4)

    def log(self):
        p = self.pasta / "log.txt"
        return p.read_text().splitlines() if p.exists() else []

    def el(self, leitura, nome, tipo=None, n=0):
        return [e for e in leitura.elementos if e.nome == nome and (tipo is None or e.tipo == tipo)][n]

    def fechar(self):
        self.proc.kill()
        self.proc.wait()


@pytest.fixture(scope="module")
def form(tmp_path_factory):
    f = FormWin(tmp_path_factory.mktemp("form_ro"))
    yield f
    f.fechar()


@pytest.fixture
def form_novo(tmp_path):
    f = FormWin(tmp_path)
    yield f
    f.fechar()


@pytest.fixture
def form_chrome(tmp_path):
    f = FormWin(tmp_path, chrome=True)
    f.sonda = Sonda(titulo_groov="GROOV")
    yield f
    f.fechar()


@pytest.fixture
def form_frente(tmp_path):
    f = FormWin(tmp_path, frente=True)
    yield f
    f.fechar()


@WIN
def test_janelas_acha_a_janela_de_teste(form):
    assert form.hwnd in rodar(form.sonda.janelas())


@WIN
def test_janela_de_processo_proibido_nao_e_lida_e_o_resto_sim(form):
    with pytest.raises(ErroSonda, match="janela_nao_permitida"):
        rodar(Sonda(titulo_groov="GROOV", proibidos=("powershell",)).ler(form.hwnd))
    assert rodar(Sonda(titulo_groov="GROOV").ler(form.hwnd)).hwnd == form.hwnd  # sem lista de permitidos: powershell vale


@WIN
def test_ler_acha_os_controles_e_o_botao_sem_nome_nao_recebe_id(form):
    leitura = rodar(form.sonda.ler(form.hwnd))
    abrir, busca = form.el(leitura, "Abrir", "Button"), form.el(leitura, "Pesquisar", "Edit")
    assert abrir.runtime_id and busca.runtime_id and abrir.papel and leitura.endereco is None
    assert all(e.nome for e in leitura.elementos)
    assert len({e.id for e in leitura.elementos}) == len(leitura.elementos)
    assert form.el(leitura, "Senha", "Edit").senha is True
    assert leitura.titulo == "Janela de teste pc" and len(leitura.texto) <= pc.TEXTO_MAX


@WIN
def test_clicar_aciona_o_botao(form_novo):
    f = form_novo
    leitura = rodar(f.sonda.ler(f.hwnd))
    assert rodar(f.sonda.clicar(f.hwnd, f.el(leitura, "Abrir"), None)) is True
    time.sleep(0.5)
    assert f.log() == ["clique:Abrir:primeiro"]


@WIN
def test_acao_com_elemento_mudado_nao_age(form_novo):
    f = form_novo
    leitura = rodar(f.sonda.ler(f.hwnd))
    f.comando("renomear")  # o botão muda de nome entre ler e clicar
    assert rodar(f.sonda.clicar(f.hwnd, f.el(leitura, "Abrir"), None)) is False
    time.sleep(0.5)
    assert f.log() == []


@WIN
def test_id_de_outro_elemento_ou_inventado_nao_age(form_novo):
    f = form_novo
    abrir = f.el(rodar(f.sonda.ler(f.hwnd)), "Abrir")
    assert rodar(f.sonda.clicar(f.hwnd, dataclasses.replace(abrir, runtime_id="42.999999"), None)) is False
    assert rodar(f.sonda.clicar(f.hwnd, dataclasses.replace(abrir, runtime_id=""), None)) is False
    assert rodar(f.sonda.clicar(f.hwnd, dataclasses.replace(abrir, tipo="Hyperlink"), None)) is False
    time.sleep(0.5)
    assert f.log() == []


@WIN
def test_dois_botoes_iguais_age_so_no_que_foi_lido(form_novo):
    f = form_novo
    f.comando("duplicar")
    leitura = rodar(f.sonda.ler(f.hwnd))
    assert sum(e.nome == "Abrir" for e in leitura.elementos) == 2
    segundo = f.el(leitura, "Abrir", "Button", 1)
    assert rodar(f.sonda.clicar(f.hwnd, segundo, None)) is True  # RuntimeId distingue os dois; o outro não é tocado
    time.sleep(0.5)
    assert len(f.log()) == 1 and f.log()[0].startswith("clique:Abrir:")


@WIN
def test_digitar_escreve_sem_enter_e_recusa_controle_e_senha(form_novo):
    f = form_novo
    leitura = rodar(f.sonda.ler(f.hwnd))
    busca = f.el(leitura, "Pesquisar")
    assert rodar(f.sonda.digitar(f.hwnd, busca, "sora no kanata", None)) is True
    f.comando("dump")
    assert (f.pasta / "dump.txt").read_text() == "sora no kanata"
    assert not any(l.startswith("enter") for l in f.log())
    assert rodar(f.sonda.digitar(f.hwnd, busca, "a\nb", None)) is False
    assert rodar(f.sonda.digitar(f.hwnd, f.el(leitura, "Senha"), "x", None)) is False


@WIN
def test_digitar_acrescentando_mantem_o_texto_que_ja_esta(form_novo):
    f = form_novo
    busca = f.el(rodar(f.sonda.ler(f.hwnd)), "Pesquisar")
    assert rodar(f.sonda.digitar(f.hwnd, busca, "oi tudo bem", None)) is True
    assert rodar(f.sonda.digitar(f.hwnd, busca, "frase", None, acrescentar=True)) is True
    f.comando("dump")
    assert (f.pasta / "dump.txt").read_text().splitlines() == ["oi tudo bem", "frase"]


@WIN
def test_buscar_fora_do_primeiro_plano_nao_age(form_novo):
    f = form_novo
    leitura = rodar(f.sonda.ler(f.hwnd))
    f.comando("fundo")
    assert rodar(f.sonda.primeiro_plano()) != f.hwnd
    assert rodar(f.sonda.buscar(f.hwnd, f.el(leitura, "Pesquisar"), "kanata", None)) is False
    f.comando("dump")
    assert (f.pasta / "dump.txt").read_text() == "" and f.log() == []


@WIN
@pytest.mark.skipif(not os.environ.get("GROOV_TESTE_TECLADO"), reason="rouba o foco e injeta uma tecla: só com GROOV_TESTE_TECLADO=1, "
                    "sem ninguém (nem outro agente) usando o teclado")
def test_buscar_escreve_e_da_enter(form_frente):
    f = form_frente
    time.sleep(1.5)  # o WPF so entrega teclas ~1 s depois do 1o foco num TextBox
    assert rodar(f.sonda.primeiro_plano()) == f.hwnd
    leitura = rodar(f.sonda.ler(f.hwnd))
    assert rodar(f.sonda.buscar(f.hwnd, f.el(leitura, "Pesquisar"), "sora", None)) is True
    time.sleep(0.5)
    assert f.log() == ["enter:sora"]


@WIN
def test_envio_le_os_campos_reais(form):
    e = rodar(form.sonda.envio(form.hwnd))
    assert e == pc.Envio(destino="ana@example.com", texto="chego as 8", anexos=0, cc="")


@WIN
def test_janela_do_groov_sai_de_janelas_e_nao_e_lida(form):
    groov = Sonda(titulo_groov="Janela de teste pc", processos_extras=("powershell",))  # o título que tela.titulo_da_janela daria
    assert form.hwnd not in rodar(groov.janelas())
    with pytest.raises(ErroSonda, match="janela_nao_permitida"):
        rodar(groov.ler(form.hwnd))
    assert form.hwnd in rodar(form.sonda.janelas())  # com outro título, a mesma janela entra


# --- ramo Chrome da sonda, contra um chrome.exe de mentira (cópia do powershell com a janela de teste) ---

@WIN
def test_chrome_le_so_o_document_e_o_endereco(form_chrome):
    f = form_chrome
    leitura = rodar(f.sonda.ler(f.hwnd))
    assert leitura.endereco == "exemplo.com/a"
    nomes = {e.nome for e in leitura.elementos}
    assert {"Abrir", "Pesquisar", "Voltar"} <= nomes and "Barra de endereco e de pesquisa" not in nomes
    assert [e.nome for e in leitura.elementos].count("Voltar") == 1  # so o da pagina; o da moldura nao e do Document


@WIN
def test_chrome_acao_confere_o_endereco(form_chrome):
    f = form_chrome
    leitura = rodar(f.sonda.ler(f.hwnd))
    abrir = f.el(leitura, "Abrir")
    assert rodar(f.sonda.clicar(f.hwnd, abrir, None)) is False  # sem endereco lido: nao age
    assert rodar(f.sonda.clicar(f.hwnd, abrir, "")) is False
    f.comando("endereco")  # a aba navegou entre ler e clicar
    assert rodar(f.sonda.clicar(f.hwnd, abrir, "exemplo.com/a")) is False
    time.sleep(0.5)
    assert f.log() == []


@WIN
def test_chrome_acao_com_endereco_certo_age(form_chrome):
    f = form_chrome
    leitura = rodar(f.sonda.ler(f.hwnd))
    assert rodar(f.sonda.clicar(f.hwnd, f.el(leitura, "Abrir"), leitura.endereco)) is True
    assert rodar(f.sonda.digitar(f.hwnd, f.el(leitura, "Pesquisar"), "kanata", leitura.endereco)) is True
    f.comando("dump")
    assert (f.pasta / "dump.txt").read_text() == "kanata" and f.log() == ["clique:Abrir:primeiro"]


@WIN
def test_chrome_voltar_nunca_clica_botao_da_pagina(form_chrome):
    f = form_chrome
    assert rodar(f.sonda.voltar(f.hwnd)) is False  # Voltar da moldura desligado: o "Voltar" da pagina nao serve
    time.sleep(0.5)
    assert f.log() == []
    f.comando("voltar_on")
    assert rodar(f.sonda.voltar(f.hwnd)) is True
    time.sleep(0.5)
    assert f.log() == ["clique:Voltar:frame"]


@WIN
def test_chrome_rolar_e_janelas_nao_quebram(form_chrome):
    f = form_chrome
    assert isinstance(rodar(f.sonda.rolar(f.hwnd, "baixo")), bool)
    assert isinstance(rodar(f.sonda.janelas()), frozenset)



def test_elemento_ancestral_nulo():
    from src.conversa.pc import _elemento
    base = {"id": 1, "nome": "x", "tipo": "Hyperlink"}
    assert _elemento({**base, "ancestrais": [None]}).ancestrais == ()
    assert _elemento({**base, "ancestrais": [None, "x", ""]}).ancestrais == ("x",)
    assert _elemento({**base, "ancestrais": "Unico"}).ancestrais == ("Unico",)
    from src.conversa.regras_pc import classificar_clique
    classificar_clique(_elemento({**base, "ancestrais": [None]}), "g1.globo.com", "abre o g1", "g1")


def test_controlar_midia_manda_a_acao():
    chamado = {}
    async def _chamar(op, teto=None, **dados):
        chamado.update(op=op, **dados)
        return {"ok": True}
    s = Sonda()
    s._chamar = _chamar
    assert rodar(s.controlar_midia("pausar")) is True and chamado == {"op": "midia_controle", "acao": "pausar", "preferir": ""}
    assert rodar(resposta({"ok": False}).controlar_midia("tocar")) is False


def test_tocar_prefere_o_app_que_o_groov_pausou():
    """Rodada de 09/11: "continua" despausou o vídeo do navegador em vez do Spotify que o "pausa" tinha pausado."""
    enviados = []
    async def _chamar(op, teto=None, **dados):
        enviados.append(dados)
        return {"ok": True, "app": "SpotifyAB.SpotifyMusic_x!Spotify"}
    s = Sonda()
    s._chamar = _chamar
    rodar(s.controlar_midia("pausar"))
    rodar(s.controlar_midia("tocar"))
    assert enviados[1] == {"acao": "tocar", "preferir": "SpotifyAB.SpotifyMusic_x!Spotify"}
    rodar(s.controlar_midia("tocar"))  # já voltou a tocar: a preferência acabou
    assert enviados[2] == {"acao": "tocar", "preferir": ""}


def test_controlar_midia_com_sonda_quebrada_e_nao_agiu():
    async def _chamar(op, teto=None, **dados):
        raise pc.ErroSonda("midia_controle: estourou o teto")
    s = Sonda()
    s._chamar = _chamar
    assert rodar(s.controlar_midia("tocar")) is False


def test_falso_grava_controlar_midia():
    f = Falso(agir=False)
    assert rodar(f.controlar_midia("proxima")) is False and f.chamadas == [("controlar_midia", "proxima")]


def test_sonda_ps1_so_ascii():
    pc.SONDA_PS1.read_bytes().decode("ascii")  # o PowerShell 5.1 lê sem BOM como ANSI


def test_aba_duas_janelas_no_mesmo_site_pega_a_da_frente():
    """Aba aberta pelo Playwright: o select traz a janela dela para a frente, mesmo com outra do usuário no mesmo site/título."""
    class PorJanela(Falso):
        async def ler(self, hwnd):
            return Leitura(hwnd, "www.netflix.com/browse", "Netflix", "x", (), False)
    fb = PorJanela(janelas=[frozenset({1, 2})], plano=2)
    assert rodar(janela_da_aba(fb, frozenset({1, 2}), "netflix.com", prazo=0.05, passo=0, assentar=0)) == 2


# --- visão: olhar, clicar_ponto, tecla ---

def test_olhar_decodifica():
    import base64
    png = base64.b64encode(b"PNG").decode()
    s = resposta({"retangulo": [0, 0, 800, 600], "linhas": [{"texto": "Pular anúncio", "caixa": [10, 20, 90, 30]}],
                  "png_b64": png, "escala": 1.0})
    assert rodar(s.olhar(5)) == pc.Olhar(retangulo=(0, 0, 800, 600), linhas=(pc.LinhaOcr("Pular anúncio", (10, 20, 90, 30)),),
                                         png=b"PNG", escala=1.0)


def test_olhar_falha_vira_none():
    assert rodar(resposta({"erro": "X"}).olhar(5)) is None


def test_clicar_ponto_manda_retangulo():
    codigo = ("import sys,json; d=json.loads(sys.stdin.buffer.read().decode('utf-8'));"
              "print(json.dumps({'ok': d['op']=='clicar_ponto' and d['x']==7 and d['y']==9 and d['retangulo']==[1,2,3,4] and d['hwnd']==5}))")
    assert rodar(fake(codigo).clicar_ponto(5, 7, 9, (1, 2, 3, 4))) is True


def test_tecla_fora_da_lista_nao_chama():
    s = fake()
    chamou = []

    async def espiao(*a, **k):
        chamou.append(a)
        return {"ok": True}
    s._chamar = espiao
    assert rodar(s.tecla(1, "alt+f4")) is False and chamou == []


def test_tecla_da_lista_chama():
    codigo = ("import sys,json; d=json.loads(sys.stdin.buffer.read().decode('utf-8'));"
              "print(json.dumps({'ok': d['op']=='tecla' and d['tecla']=='espaco'}))")
    assert rodar(fake(codigo).tecla(5, "espaco")) is True


def test_teclas_da_sonda_iguais():
    import re
    from src.conversa import regras_pc
    ps1 = pc.SONDA_PS1.read_text(encoding="ascii")
    linha = re.search(r"\$TECLAS = @\{([^}]*)\}", ps1).group(1)
    assert set(re.findall(r"'([a-z_]+)'\s*=", linha)) == set(regras_pc.TECLAS)


def test_falso_visao_grava():
    f = Falso()
    f.olhares = [None]
    rodar(f.olhar(3))
    rodar(f.clicar_ponto(3, 1, 2, (0, 0, 9, 9)))
    rodar(f.tecla(3, "k"))
    assert f.chamadas == [("olhar", 3), ("clicar_ponto", 3, 1, 2), ("tecla", 3, "k")]


def test_focar_decodifica_e_lista_o_processo():
    s = resposta({"hwnd": 77, "processo": "Discord"})
    assert rodar(s.focar("discord")) == 77 and "Discord" in s.listadas


def test_procurar_nao_seleciona_e_devolve_titulo():
    codigo = ("import sys,json; d=json.loads(sys.stdin.buffer.read().decode('utf-8'));"
              "print(json.dumps({'hwnd': 77 if d['selecionar'] is False else 0, 'titulo': 'Netflix', 'processo': 'chrome'}))")
    assert rodar(fake(codigo).procurar("netflix")) == (77, "Netflix")


def test_focar_nao_achou_e_none():
    assert rodar(resposta({"hwnd": None, "achadas": 2}).focar("netflix")) is None


def test_focar_nome_invalido_nem_chama():
    s = fake()

    async def espiao(*a, **k):
        raise AssertionError("não devia chamar a sonda")
    s._chamar = espiao
    assert rodar(s.focar("../x")) is None and rodar(s.focar("")) is None
