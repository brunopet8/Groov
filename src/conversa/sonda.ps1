# Sonda de UI Automation do controle do PC: UMA operacao por execucao, escrita do zero (nada do probe.ps1).
# Entrada: JSON UTF-8 no stdin (nunca na linha de comando). Saida: JSON UTF-8 sem BOM no stdout.
# Nunca imprime texto de janela fora do JSON; em erro devolve so o nome do tipo da excecao.
# So ASCII: o PowerShell 5.1 le .ps1 sem BOM como ANSI.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
$AE = [System.Windows.Automation.AutomationElement]
$TS = [System.Windows.Automation.TreeScope]
$CT = [System.Windows.Automation.ControlType]

$entrada = New-Object System.IO.StreamReader([Console]::OpenStandardInput(), (New-Object System.Text.UTF8Encoding($false)))
$req = $entrada.ReadToEnd() | ConvertFrom-Json

function Sair($obj) {
    $json = ConvertTo-Json -InputObject $obj -Compress -Depth 8
    $bytes = (New-Object System.Text.UTF8Encoding($false)).GetBytes($json)
    $o = [Console]::OpenStandardOutput(); $o.Write($bytes, 0, $bytes.Length); $o.Flush()
}

Add-Type -Namespace W -Name U -MemberDefinition @'
[DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
[DllImport("user32.dll")] public static extern IntPtr GetAncestor(IntPtr h, uint f);
[DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra);
[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);
'@
# Com a tela apagada o Chrome esconde a pagina da UIA (prova de 07/11): ES_DISPLAY_REQUIRED acende antes de ler.
function Acender-Tela { [void][W.U]::SetThreadExecutionState(0x2) }

$MAX_NOS = 6000        # teto de nos percorridos por leitura
$MAX_ELEMENTOS = 250   # decisao provisoria (a revisar): controles com id por leitura
$MAX_MS = 4500         # a leitura para sozinha antes do teto de 8 s do Python
$TIPOS_INT = @('Button', 'Hyperlink', 'Edit', 'ComboBox', 'ListItem', 'DataItem', 'TabItem', 'CheckBox', 'RadioButton', 'MenuItem', 'SplitButton', 'TreeItem')
$TIPOS_TEXTO = @('Text', 'Image')
$NOME_BARRA = 'Barra de endere|Address and search'

function Curto([string]$s, [int]$n) { if ($s.Length -gt $n) { $s.Substring(0, $n) } else { $s } }
function Tipo($e) { $e.Current.ControlType.ProgrammaticName.Substring(12) }  # tira 'ControlType.'
function Rid($e) { ($e.GetRuntimeId()) -join '.' }

function Nome-Processo([int]$id) { try { (Get-Process -Id $id).ProcessName } catch { '' } }

# Janela UWP (Seguranca do Windows, Configuracoes) tem dono ApplicationFrameHost: pelo titulo vira o processo proibido dela.
function Processo-Efetivo($j) {
    $nome = Nome-Processo $j.Current.ProcessId
    if ($nome -eq 'ApplicationFrameHost') {
        $t = [string]$j.Current.Name
        foreach ($p in @($req.titulos_proibidos)) { if ($t -like "*$p*") { return 'SecHealthUI' } }
    }
    $nome
}

# Janela do pedido: qualquer processo lido, menos os proibidos (sistema/seguranca) e a do GROOV. Devolve $null se nao serve.
function Janela-Valida([long]$hwnd) {
    $j = $AE::FromHandle([IntPtr]$hwnd)
    $nome = Processo-Efetivo $j
    if (-not $nome -or ($req.proibidos -contains $nome)) { return $null }
    if ($req.titulo_groov -and $j.Current.Name -ceq $req.titulo_groov) { return $null }
    [pscustomobject]@{ el = $j; chrome = ($nome -eq 'chrome') }
}

function Documento($janela) {
    $c = New-Object System.Windows.Automation.PropertyCondition($AE::ControlTypeProperty, $CT::Document)
    $janela.FindFirst($TS::Descendants, $c)
}

# Endereco so para a sonda e o PC: nunca vira controle. Chrome apenas.
function Endereco($janela) {
    $c = New-Object System.Windows.Automation.PropertyCondition($AE::ControlTypeProperty, $CT::Edit)
    foreach ($e in $janela.FindAll($TS::Descendants, $c)) {
        if ($e.Current.Name -match $NOME_BARRA -or $e.Current.ClassName -ceq 'OmniboxViewViews') {
            $p = $null
            if ($e.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern, [ref]$p)) { return [string]$p.Current.Value }
        }
    }
    return $null
}

function Valor($e) {
    $p = $null
    if ($e.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern, [ref]$p)) { return [string]$p.Current.Value }
    if ($e.TryGetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern, [ref]$p)) { return [string]$p.DocumentRange.GetText(2000) }
    return ''
}

function Limpar-Texto([string]$t) {
    $t = $t.Replace([string][char]0xFFFC, '').Replace([string][char]0x200B, '')
    $t = $t -replace '[\x00-\x08\x0B\x0C\x0E-\x1F]', ''
    $t = $t -replace '[ \t]+', ' '
    ($t -replace '(\s*\r?\n\s*)+', "`n").Trim()
}

# ---- Leitura: percorre so a raiz (Document da aba no Chrome; janela inteira nos apps) com cache de propriedades ----
$CR = New-Object System.Windows.Automation.CacheRequest
foreach ($p in @($AE::NameProperty, $AE::ControlTypeProperty, $AE::LocalizedControlTypeProperty, $AE::IsPasswordProperty)) { $CR.Add($p) }
$WK = [System.Windows.Automation.TreeWalker]::ControlViewWalker
$script:lista = New-Object System.Collections.ArrayList
$script:nos = 0
$script:cortado = $false
$script:rel = [Diagnostics.Stopwatch]::StartNew()

# Devolve o texto dos Text/Image descendentes (o "texto interno" do controle). Tudo o mais vai para [void].
function Andar($pai, $anc) {
    $dentro = New-Object System.Text.StringBuilder
    $f = $WK.GetFirstChild($pai, $CR)
    while ($null -ne $f) {
        if ($script:nos -ge $MAX_NOS -or $script:lista.Count -ge $MAX_ELEMENTOS -or $script:rel.ElapsedMilliseconds -gt $MAX_MS) { $script:cortado = $true; break }
        $script:nos++
        $nome = [string]$f.Cached.Name
        $tipo = $f.Cached.ControlType.ProgrammaticName.Substring(12)
        $reg = $null
        if ($nome -and ($TIPOS_INT -contains $tipo) -and -not ($tipo -eq 'Edit' -and $nome -match $NOME_BARRA)) {
            $reg = [ordered]@{
                id = $script:lista.Count + 1; nome = (Curto $nome 200); tipo = $tipo; papel = [string]$f.Cached.LocalizedControlType
                texto_interno = ''; ancestrais = @($anc); senha = [bool]$f.Cached.IsPassword; runtime_id = (Rid $f); host_do_link = $null
            }
            if ($tipo -eq 'Hyperlink') {
                try {
                    $vp = $null
                    if ($f.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern, [ref]$vp)) {
                        $u = [string]$vp.Current.Value
                        if ($u -match '^https?://') { $reg.host_do_link = ([Uri]$u).Host }
                    }
                } catch {}
            }
            [void]$script:lista.Add($reg)
        }
        if ($nome -and ($TIPOS_TEXTO -contains $tipo)) { [void]$dentro.Append($nome).Append(' ') }
        $novo = if ($nome) { @((@($anc) + (Curto $nome 80)) | Select-Object -Last 8) } else { @($anc) }
        $sub = Andar $f $novo
        if ($sub) { [void]$dentro.Append($sub).Append(' ') }
        if ($reg) { $reg.texto_interno = Curto (([string]$sub -replace '\s+', ' ').Trim()) 200 }
        $f = $WK.GetNextSibling($f, $CR)
    }
    $dentro.ToString()
}

function Op-Ler {
    $v = Janela-Valida $req.hwnd
    if (-not $v) { return @{ erro = 'janela_nao_permitida' } }
    Acender-Tela
    $j = $v.el
    $endereco = $null; $raiz = $j; $titulo = [string]$j.Current.Name
    if ($v.chrome) {
        $raiz = Documento $j
        $endereco = Endereco $j
        if ($raiz) { $titulo = [string]$raiz.Current.Name }  # titulo so da aba lida, nunca o da janela (que cita outras abas)
    }
    $texto = ''
    if ($raiz) {
        $doc = if ($v.chrome) { $raiz } else { Documento $j }
        $limite = [int]$req.max_chars
        if ($doc) {
            $p = $null
            if ($doc.TryGetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern, [ref]$p)) {
                $bruto = [string]$p.DocumentRange.GetText($limite * 4)
                $texto = Limpar-Texto $bruto
                if ($bruto.Length -ge $limite * 4) { $script:cortado = $true }
            }
        }
        $inner = Andar $raiz @()
        if (-not $texto) { $texto = Limpar-Texto $inner }
        if ($texto.Length -gt $limite) { $texto = $texto.Substring(0, $limite); $script:cortado = $true }
    }
    @{ hwnd = [long]$req.hwnd; endereco = $endereco; titulo = $titulo; texto = $texto; elementos = @($script:lista); cortado = $script:cortado }
}

# ---- Conferencia no ato: janela, endereco, RuntimeId, nome e tipo no MESMO processo, logo antes de agir ----
function Alvo-Conferido($v) {
    $raiz = $v.el
    if ($v.chrome) {
        $raiz = Documento $v.el
        if (-not $raiz) { return @{ motivo = 'sem_documento' } }
    }
    if ($v.chrome) {
        if (-not $req.endereco) { return @{ motivo = 'sem_endereco' } }  # Chrome sem endereco lido: nao age sem conferir
        if ((Endereco $v.el) -cne $req.endereco) { return @{ motivo = 'mudou' } }
    }
    if (-not $req.runtime_id) { return @{ motivo = 'sem_runtime_id' } }
    $ids = [int[]]($req.runtime_id -split '\.')
    $c = New-Object System.Windows.Automation.PropertyCondition($AE::RuntimeIdProperty, $ids)
    $ach = @($raiz.FindAll($TS::Descendants, $c))
    if ($ach.Count -eq 0) { return @{ motivo = 'nao_achou' } }
    if ($ach.Count -gt 1) { return @{ motivo = 'varios' } }
    $e = $ach[0]
    if ((Curto ([string]$e.Current.Name) 200) -cne $req.nome -or (Tipo $e) -cne $req.tipo) { return @{ motivo = 'mudou' } }
    if (-not $e.Current.IsEnabled) { return @{ motivo = 'desligado' } }
    @{ el = $e; raiz = $raiz }
}

function Em-Primeiro-Plano([long]$hwnd) {
    $fg = [W.U]::GetForegroundWindow()
    $raiz = [W.U]::GetAncestor($fg, 2)
    ($fg.ToInt64() -eq $hwnd) -or ($raiz.ToInt64() -eq $hwnd)
}

function Tem-Controle([string]$t) { $t -match '[\x00-\x1F\x7F]' }

function Op-Clicar {
    $v = Janela-Valida $req.hwnd
    if (-not $v) { return @{ ok = $false; motivo = 'janela_nao_permitida' } }
    $a = Alvo-Conferido $v
    if (-not $a.el) { return @{ ok = $false; motivo = $a.motivo } }
    $p = $null
    if ($a.el.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern, [ref]$p)) { $p.Invoke(); return @{ ok = $true } }
    if ($a.el.TryGetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern, [ref]$p)) { $p.Select(); return @{ ok = $true } }
    @{ ok = $false; motivo = 'sem_padrao' }
}

# buscar: foco no campo, ValuePattern, foco conferido, Enter como UMA tecla. digitar: so ValuePattern, sem Enter.
function Op-Escrever([bool]$enter) {
    $v = Janela-Valida $req.hwnd
    if (-not $v) { return @{ ok = $false; motivo = 'janela_nao_permitida' } }
    $texto = [string]$req.texto
    if (-not $texto -or (Tem-Controle $texto)) { return @{ ok = $false; motivo = 'texto_invalido' } }
    if ($enter -and -not (Em-Primeiro-Plano $req.hwnd)) { return @{ ok = $false; motivo = 'segundo_plano' }  }  # nao rouba o foco
    $a = Alvo-Conferido $v
    if (-not $a.el) { return @{ ok = $false; motivo = $a.motivo } }
    $e = $a.el
    if ($e.Current.IsPassword) { return @{ ok = $false; motivo = 'senha' } }
    $vp = $null
    if (-not $e.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern, [ref]$vp) -or $vp.Current.IsReadOnly) { return @{ ok = $false; motivo = 'sem_valor' } }
    if ($enter) { $e.SetFocus() }
    if ($req.acrescentar) {  # nunca apaga o que ja esta: valor atual + linha nova + texto
        $atual = [string]$vp.Current.Value
        if ($atual) { $texto = $atual + [Environment]::NewLine + $texto }
    }
    $vp.SetValue($texto)
    if ($enter) {
        Start-Sleep -Milliseconds 150
        # HasKeyboardFocus do proprio campo; FocusedElement sozinho devolveu o Pane da janela no WPF (e funcionou no Spotify, prova 5)
        $foco = $AE::FocusedElement
        $focado = $e.Current.HasKeyboardFocus -or ($null -ne $foco -and (Rid $foco) -ceq (Rid $e))
        if (-not $focado -or -not (Em-Primeiro-Plano $req.hwnd)) { return @{ ok = $false; motivo = 'foco' } }
        # Enter sem scan code e sem pausa entre baixo e cima nao chegou ao WPF (medido): 0x1C e 50 ms
        [W.U]::keybd_event(0x0D, 0x1C, 0, [UIntPtr]::Zero)
        Start-Sleep -Milliseconds 50
        [W.U]::keybd_event(0x0D, 0x1C, 2, [UIntPtr]::Zero)
    }
    @{ ok = $true }
}

function Op-Rolar {
    $v = Janela-Valida $req.hwnd
    if (-not $v) { return @{ ok = $false; motivo = 'janela_nao_permitida' } }
    $raiz = $v.el
    if ($v.chrome) { $raiz = Documento $v.el; if (-not $raiz) { return @{ ok = $false; motivo = 'sem_documento' } } }
    $alvo = $null
    if ($raiz.GetCurrentPropertyValue($AE::IsScrollPatternAvailableProperty)) { $alvo = $raiz }
    else { $alvo = $raiz.FindFirst($TS::Descendants, (New-Object System.Windows.Automation.PropertyCondition($AE::IsScrollPatternAvailableProperty, $true))) }
    if (-not $alvo) { return @{ ok = $false; motivo = 'sem_rolagem' } }
    $sp = $alvo.GetCurrentPattern([System.Windows.Automation.ScrollPattern]::Pattern)
    $N = [System.Windows.Automation.ScrollAmount]
    $d = if (@('cima', 'up') -contains [string]$req.direcao) { $N::LargeDecrement } else { $N::LargeIncrement }
    $sp.Scroll($N::NoAmount, $d)
    @{ ok = $true }
}

# Botao Voltar do Chrome: uso interno do laco, nunca exposto ao modelo.
function Op-Voltar {
    $v = Janela-Valida $req.hwnd
    if (-not $v -or -not $v.chrome) { return @{ ok = $false; motivo = 'janela_nao_permitida' } }
    # So a moldura do Chrome: botao dentro do Document e controle da pagina (nome controlado por ela), nunca clicado aqui.
    $doc = Documento $v.el
    if (-not $doc) { return @{ ok = $false; motivo = 'sem_documento' } }
    $c = New-Object System.Windows.Automation.PropertyCondition($AE::ControlTypeProperty, $CT::Button)
    foreach ($b in $v.el.FindAll($TS::Descendants, $c)) {
        if ($b.Current.Name -notmatch '^(Voltar|Back)$') { continue }
        $pai = $WK.GetParent($b); $da_pagina = $false
        while ($null -ne $pai) { if ([System.Windows.Automation.Automation]::Compare($pai, $doc)) { $da_pagina = $true; break }; $pai = $WK.GetParent($pai) }
        if ($da_pagina -or -not $b.Current.IsEnabled) { continue }
        $p = $null
        if ($b.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern, [ref]$p)) { $p.Invoke(); return @{ ok = $true } }
    }
    @{ ok = $false; motivo = 'nao_achou' }
}

# Abas do Chrome: os TabItem da moldura (os de dentro do Document sao controles da pagina e nao contam).
function Abas-Chrome($janela) {
    $doc = Documento $janela
    $c = New-Object System.Windows.Automation.PropertyCondition($AE::ControlTypeProperty, $CT::TabItem)
    $lista = New-Object System.Collections.ArrayList
    foreach ($t in $janela.FindAll($TS::Descendants, $c)) {
        $pai = $WK.GetParent($t); $da_pagina = $false
        while ($doc -and $null -ne $pai) { if ([System.Windows.Automation.Automation]::Compare($pai, $doc)) { $da_pagina = $true; break }; $pai = $WK.GetParent($pai) }
        if (-not $da_pagina) { [void]$lista.Add($t) }
    }
    ,$lista
}

# Quem e a janela (processo, abas, se e a do GROOV). Nao filtra: quem decide e regras_pc.decidir_janela.
function Op-JanelaInfo {
    $j = $AE::FromHandle([IntPtr][long]$req.hwnd)
    $nome = Processo-Efetivo $j
    $groov = [bool]($req.titulo_groov -and $j.Current.Name -ceq $req.titulo_groov)
    $abas = 0
    if ($nome -eq 'chrome') { $abas = @(Abas-Chrome $j).Count }
    @{ processo = $nome; abas = $abas; groov = $groov }
}

# Fecha a aba ativa: botao de fechar dentro do TabItem selecionado, por InvokePattern (nunca tecla).
function Op-FecharAba {
    $v = Janela-Valida $req.hwnd
    if (-not $v -or -not $v.chrome) { return @{ ok = $false; motivo = 'janela_nao_permitida' } }
    $c = New-Object System.Windows.Automation.PropertyCondition($AE::ControlTypeProperty, $CT::Button)
    foreach ($t in @(Abas-Chrome $v.el)) {
        $s = $null
        if (-not $t.TryGetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern, [ref]$s) -or -not $s.Current.IsSelected) { continue }
        foreach ($b in $t.FindAll($TS::Descendants, $c)) {
            $p = $null
            if ($b.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern, [ref]$p)) { $p.Invoke(); return @{ ok = $true } }
        }
        return @{ ok = $false; motivo = 'sem_botao' }
    }
    @{ ok = $false; motivo = 'sem_aba_ativa' }
}

# Campos reais de um envio (e-mail ou chat), relidos pela UIA. Falta destino ou texto: $null (o PC nao oferece enviar).
# decisao provisoria (a revisar): nomes de campo de Gmail/WhatsApp Web de memoria, nao medidos; destinatario em chips cai em $null (falha fechada).
function Op-Envio {
    $v = Janela-Valida $req.hwnd
    if (-not $v) { return @{ erro = 'janela_nao_permitida' } }
    $raiz = $v.el
    if ($v.chrome) { $raiz = Documento $v.el }
    if (-not $raiz) { return @{ envio = $null } }
    $destino = ''; $texto = ''; $cc = ''; $anexos = 0
    $c = New-Object System.Windows.Automation.OrCondition(
        (New-Object System.Windows.Automation.PropertyCondition($AE::ControlTypeProperty, $CT::Edit)),
        (New-Object System.Windows.Automation.PropertyCondition($AE::ControlTypeProperty, $CT::ComboBox)),
        (New-Object System.Windows.Automation.PropertyCondition($AE::ControlTypeProperty, $CT::Button)),
        (New-Object System.Windows.Automation.PropertyCondition($AE::ControlTypeProperty, $CT::ListItem)),
        (New-Object System.Windows.Automation.PropertyCondition($AE::ControlTypeProperty, $CT::Hyperlink)))
    foreach ($e in $raiz.FindAll($TS::Descendants, $c)) {
        $n = [string]$e.Current.Name
        $t = Tipo $e
        if ($t -eq 'Edit' -or $t -eq 'ComboBox') {
            if ($n -match '^(Cc|Cco|Bcc)\b') { $cc = (($cc + ' ' + (Valor $e)).Trim()) }
            elseif ($n -match '^(Para|To)\b') { $destino = (Valor $e) }
            elseif ($n -match 'Corpo da mensagem|Message Body|Digite uma mensagem|Type a message') { $texto = (Valor $e) }
        } elseif ($n -match '^(Anexo|Attachment)') { $anexos++ }
    }
    if (-not $destino.Trim() -or -not $texto.Trim()) { return @{ envio = $null } }
    @{ envio = @{ destino = (Limpar-Texto $destino); texto = (Limpar-Texto $texto); anexos = $anexos; cc = (Limpar-Texto $cc) } }
}

# ---- Janelas de nivel superior de Chrome (sem a do GROOV) e dos apps da lista ----
function Op-Janelas {
    $mapa = @{}
    foreach ($p in Get-Process) { $mapa[[int]$p.Id] = $p.ProcessName }
    $hw = New-Object System.Collections.ArrayList
    foreach ($j in $AE::RootElement.FindAll($TS::Children, (New-Object System.Windows.Automation.PropertyCondition($AE::IsControlElementProperty, $true)))) {
        $h = [long]$j.Current.NativeWindowHandle
        if ($h -eq 0) { continue }
        $nome = $mapa[[int]$j.Current.ProcessId]
        if (-not ($req.listadas -contains $nome)) { continue }
        if ($req.titulo_groov -and $j.Current.Name -ceq $req.titulo_groov) { continue }
        if ($nome -eq 'chrome' -and $j.Current.ClassName -cne 'Chrome_WidgetWin_1') { continue }
        if (-not $j.Current.Name) { continue }
        [void]$hw.Add($h)
    }
    @{ janelas = @($hw) }
}

# App por nome: a janela principal do processo, ja aberta ou nova. Zero ou mais de uma: $null.
# O nome vem validado do Python (letras, digitos, espaco, ponto, hifen) e aqui de novo; nunca vira linha de comando.
function Achar-Exe([string]$nome) {
    $menus = @("$env:ProgramData\Microsoft\Windows\Start Menu\Programs", "$env:APPDATA\Microsoft\Windows\Start Menu\Programs")
    $lnk = Get-ChildItem -Path $menus -Filter '*.lnk' -Recurse -ErrorAction SilentlyContinue | Where-Object { $_.BaseName -ieq $nome } | Select-Object -First 1
    if ($lnk) { return $lnk.FullName }
    $cmd = Get-Command $nome -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cmd) { return $cmd.Source }
    foreach ($raiz in 'HKLM:', 'HKCU:') {
        $ap = (Get-ItemProperty "$raiz\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\$nome.exe" -ErrorAction SilentlyContinue).'(default)'
        if ($ap) { return ([string]$ap).Trim('"') }
    }
    return $null
}

function Janelas-Dos-Processos($filtro) {
    $ids = New-Object System.Collections.ArrayList
    foreach ($p in @(Get-Process -ErrorAction SilentlyContinue)) {
        if ($p.MainWindowHandle -eq 0 -or ($req.proibidos -contains $p.ProcessName)) { continue }
        if ($req.titulo_groov -and $p.MainWindowTitle -ceq $req.titulo_groov) { continue }
        if ((& $filtro $p) -and -not $ids.Contains([long]$p.MainWindowHandle)) { [void]$ids.Add([long]$p.MainWindowHandle) }
    }
    ,$ids
}

function Op-AbrirApp {
    $nome = [string]$req.processo
    if ($nome -notmatch '^[\p{L}\p{N}][\p{L}\p{N} .\-]*$' -or $nome.Contains('..')) { return @{ hwnd = $null; achadas = 0 } }
    # ja aberto: pelo nome do processo ou, fora o Chrome, pelo titulo da janela (Code: "x - Visual Studio Code")
    $do_app = { param($p) $p.ProcessName -ieq $nome -or $p.ProcessName -ieq ($nome -replace ' ', '') -or ($p.ProcessName -ne 'chrome' -and $p.MainWindowTitle -like "*$nome*") }
    $ja = Janelas-Dos-Processos $do_app
    if ($ja.Count -eq 0) {
        $antes = Janelas-Dos-Processos { $true }
        $exe = if ($req.exe) { [string]$req.exe } else { Achar-Exe $nome }
        if (-not $exe) { return @{ hwnd = $null; achadas = 0 } }
        Set-Location $env:SystemRoot  # caminho relativo nunca resolve na pasta do projeto
        Start-Process -FilePath $exe
        $fim = (Get-Date).AddSeconds(8)
        do {
            $ja = Janelas-Dos-Processos $do_app
            # ForEach-Object desembrulha a lista: sem ele o Where-Object recebia a lista inteira como UM item
            if ($ja.Count -eq 0) { $ja = @(Janelas-Dos-Processos { $true } | ForEach-Object { $_ } | Where-Object { $antes -notcontains $_ }) }
            if ($ja.Count -gt 0) { break }
            Start-Sleep -Milliseconds 300
        } while ((Get-Date) -lt $fim)
    }
    if ($ja.Count -eq 1) { return @{ hwnd = $ja[0] } }
    @{ hwnd = $null; achadas = $ja.Count }
}

# ---- Sessao de midia do Windows (GSMTC) ----
function Sessoes-Midia {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    $asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
    $aguardar = { param($op, [Type]$tipo) $t = $asTask.MakeGenericMethod($tipo).Invoke($null, @($op)); $null = $t.Wait(4000); $t.Result }.GetNewClosure()
    [void][Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager, Windows.Media.Control, ContentType = WindowsRuntime]
    $tm = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]
    $mgr = & $aguardar ($tm::RequestAsync()) $tm
    foreach ($s in $mgr.GetSessions()) {
        $tp = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties]
        $pr = & $aguardar ($s.TryGetMediaPropertiesAsync()) $tp
        $info = $s.GetPlaybackInfo()
        [pscustomobject]@{ sessao = $s; app = [string]$s.SourceAppUserModelId; estado = [string]$info.PlaybackStatus; titulo = [string]$pr.Title; artista = [string]$pr.Artist; proxima = [bool]$info.Controls.IsNextEnabled; aguardar = $aguardar }
    }
}
function Op-Midias {
    @{ midias = @(Sessoes-Midia | ForEach-Object { [ordered]@{ app = $_.app; tocando = ($_.estado -eq 'Playing'); titulo = $_.titulo; artista = $_.artista } }) }
}
function Op-Pausar {
    $s = Sessoes-Midia | Where-Object { $_.app -ceq $req.app } | Select-Object -First 1
    if (-not $s) { return @{ ok = $false } }
    @{ ok = [bool](& $s.aguardar ($s.sessao.TryPauseAsync()) ([bool])) }
}
# acao: pausar (1a sessao Playing), tocar (a Paused do app que o ultimo pausar pausou, senao a 1a Paused),
# proxima (1a Playing que aceita pular, senao a 1a que aceita). Devolve o app da sessao (o PC guarda o do pausar).
function Op-MidiaControle {
    $todas = @(Sessoes-Midia)
    $preferir = [string]$req.preferir
    $s = switch ([string]$req.acao) {
        'pausar' { $todas | Where-Object { $_.estado -eq 'Playing' } | Select-Object -First 1 }
        'tocar' { @($todas | Where-Object { $_.estado -eq 'Paused' -and $preferir -and $_.app -ceq $preferir }) + @($todas | Where-Object { $_.estado -eq 'Paused' }) | Select-Object -First 1 }
        'proxima' { @($todas | Where-Object { $_.estado -eq 'Playing' -and $_.proxima }) + @($todas | Where-Object { $_.proxima }) | Select-Object -First 1 }
    }
    if (-not $s) { return @{ ok = $false } }
    $op = switch ([string]$req.acao) { 'pausar' { $s.sessao.TryPauseAsync() } 'tocar' { $s.sessao.TryPlayAsync() } 'proxima' { $s.sessao.TrySkipNextAsync() } }
    @{ ok = [bool](& $s.aguardar $op ([bool])); app = $s.app }
}

# ---- Pico de audio por processo (WASAPI), fora o Chrome do GROOV (user-data-dir proprio) e os pids que o PC manda ignorar ----
function Op-Som {
    Add-Type -TypeDefinition @'
using System; using System.Runtime.InteropServices; using System.Collections.Generic;
namespace SondaSom {
[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] class MMDeviceEnumeratorCo {}
[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator { int EnumAudioEndpoints(int f, int m, out IntPtr d); int GetDefaultAudioEndpoint(int f, int r, out IMMDevice d); }
[Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDevice { int Activate(ref Guid iid, int ctx, IntPtr p, [MarshalAs(UnmanagedType.IUnknown)] out object o); }
[Guid("77AA99A0-1BD6-484F-8BC7-2C654C9A9B6F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioSessionManager2 { int GetAudioSessionControl(IntPtr a, int b, out IntPtr c); int GetSimpleAudioVolume(IntPtr a, int b, out IntPtr c); int GetSessionEnumerator(out IAudioSessionEnumerator e); }
[Guid("E2F5BB11-0570-40CA-ACDD-3AA01277DEE8"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioSessionEnumerator { int GetCount(out int n); int GetSession(int i, out IAudioSessionControl2 s); }
[Guid("bfb7ff88-7239-4fc9-8fa2-07c950be9c6d"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioSessionControl2 {
  int GetState(out int s); int GetDisplayName(out IntPtr p); int SetDisplayName(IntPtr a, IntPtr b); int GetIconPath(out IntPtr p);
  int SetIconPath(IntPtr a, IntPtr b); int GetGroupingParam(out Guid g); int SetGroupingParam(IntPtr a, IntPtr b);
  int RegisterAudioSessionNotification(IntPtr a); int UnregisterAudioSessionNotification(IntPtr a);
  int GetSessionIdentifier(out IntPtr p); int GetSessionInstanceIdentifier(out IntPtr p); int GetProcessId(out uint pid);
}
[Guid("C02216F6-8C67-4B5B-9D00-D008E73E0064"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioMeterInformation { int GetPeakValue(out float p); }
public class Pico { public uint Pid; public float Valor; }
public static class Som {
  public static List<Pico> Picos() {
    var en = (IMMDeviceEnumerator)(new MMDeviceEnumeratorCo());
    IMMDevice dev; Marshal.ThrowExceptionForHR(en.GetDefaultAudioEndpoint(0, 0, out dev));
    Guid iid = typeof(IAudioSessionManager2).GUID; object o;
    Marshal.ThrowExceptionForHR(dev.Activate(ref iid, 23, IntPtr.Zero, out o));
    IAudioSessionEnumerator se; Marshal.ThrowExceptionForHR(((IAudioSessionManager2)o).GetSessionEnumerator(out se));
    int n; se.GetCount(out n); var r = new List<Pico>();
    for (int i = 0; i < n; i++) {
      IAudioSessionControl2 s; se.GetSession(i, out s); uint pid; s.GetProcessId(out pid);
      float p; ((IAudioMeterInformation)s).GetPeakValue(out p); r.Add(new Pico { Pid = pid, Valor = p });
    }
    return r;
  }
}}
'@
    $todos = Get-CimInstance Win32_Process -Filter "Name='chrome.exe'"
    $raiz = @($todos | Where-Object { $_.CommandLine -match 'user-data-dir' -and $_.CommandLine -notmatch '--type=' } | ForEach-Object { [int]$_.ProcessId })
    $ignorar = @($todos | Where-Object { $raiz -contains [int]$_.ProcessId -or $raiz -contains [int]$_.ParentProcessId } | ForEach-Object { [int]$_.ProcessId })
    $ignorar += @($req.ignorar_pids | ForEach-Object { [int]$_ })
    $max = @{}
    for ($i = 0; $i -lt [int]$req.amostras; $i++) {
        foreach ($p in [SondaSom.Som]::Picos()) {
            if ($ignorar -contains [int]$p.Pid) { continue }
            if ($p.Pid -eq 0) { continue }  # decisao provisoria (a revisar): sessao 'sistema' (bipes do Windows) nao conta como som
            $nome = Nome-Processo ([int]$p.Pid)
            if (-not $max.ContainsKey($nome) -or $max[$nome] -lt $p.Valor) { $max[$nome] = [math]::Round($p.Valor, 3) }
        }
        Start-Sleep -Milliseconds 80
    }
    @{ picos = @($max.Keys | ForEach-Object { [ordered]@{ processo = $_; pico = $max[$_] } }) }
}

# ---- Visao: olhar (captura + OCR so da janela alvo), clicar num ponto, apertar tecla ----
# Mesma tabela de regras_pc.TECLAS (teste confere): nome -> VK. Sem alt/ctrl/win.
$TECLAS = @{ 'espaco' = 0x20; 'esc' = 0x1B; 'cima' = 0x26; 'baixo' = 0x28; 'esquerda' = 0x25; 'direita' = 0x27; 'pagina_cima' = 0x21; 'pagina_baixo' = 0x22; 'k' = 0x4B; 'j' = 0x4A; 'l' = 0x4C; 'f' = 0x46; 'm' = 0x4D; 'play_pause' = 0xB3; 'proxima' = 0xB0; 'anterior' = 0xB1; 'volume_mais' = 0xAF; 'volume_menos' = 0xAE; 'mudo' = 0xAD }
$TECLAS_ESTENDIDAS = @(0x26, 0x28, 0x25, 0x27, 0x21, 0x22)

function Carregar-Visao {
    Add-Type -AssemblyName System.Drawing
    Add-Type -Namespace W -Name V -MemberDefinition @'
[DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(IntPtr v);
[DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
[DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint f);
[DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
[DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, UIntPtr e);
[DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
public struct RECT { public int Left, Top, Right, Bottom; }
'@
    # px fisicos: com a escala do Windows em 125/150 %, medir e clicar sem isso desloca o clique
    [void][W.V]::SetProcessDpiAwarenessContext([IntPtr](-4))
}

function Retangulo([long]$h) {
    $r = New-Object W.V+RECT
    [void][W.V]::GetWindowRect([IntPtr]$h, [ref]$r)
    @($r.Left, $r.Top, ($r.Right - $r.Left), ($r.Bottom - $r.Top))
}

function Na-Frente([long]$h) { [W.U]::GetAncestor([W.U]::GetForegroundWindow(), 2) -eq [IntPtr]$h }

function Titulo-Proibido($v) {
    $t = ([string]$v.el.Current.Name).ToLower()
    foreach ($p in @($req.titulos_proibidos)) { if ($p -and $t.Contains([string]$p)) { return $true } }
    $false
}

function Preta($bmp) {
    for ($i = 1; $i -le 9; $i++) {
        for ($j = 1; $j -le 9; $j++) {
            $c = $bmp.GetPixel([int]($bmp.Width * $i / 10), [int]($bmp.Height * $j / 10))
            if (($c.R + $c.G + $c.B) -gt 30) { return $false }
        }
    }
    $true
}

function Ler-Ocr($bmp) {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    $asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
    $aguardar = { param($op, [Type]$tipo) $t = $asTask.MakeGenericMethod($tipo).Invoke($null, @($op)); $null = $t.Wait(5000); $t.Result }.GetNewClosure()
    [void][Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
    [void][Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime]
    $OE = [Windows.Media.Ocr.OcrEngine]
    $motor = $OE::TryCreateFromUserProfileLanguages()
    if (-not $motor) { foreach ($l in $OE::AvailableRecognizerLanguages) { $motor = $OE::TryCreateFromLanguage($l); if ($motor) { break } } }
    if (-not $motor) { return @() }
    $fator = 1.0
    $max = [Math]::Max($bmp.Width, $bmp.Height)
    if ($max -gt $OE::MaxImageDimension) { $fator = $OE::MaxImageDimension / $max; $bmp = New-Object System.Drawing.Bitmap($bmp, [int]($bmp.Width * $fator), [int]($bmp.Height * $fator)) }
    $ms = New-Object System.IO.MemoryStream
    $bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
    $ms.Position = 0
    $ras = [System.IO.WindowsRuntimeStreamExtensions]::AsRandomAccessStream($ms)
    $dec = & $aguardar ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($ras)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $sb = & $aguardar ($dec.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
    $res = & $aguardar ($motor.RecognizeAsync($sb)) ([Windows.Media.Ocr.OcrResult])
    $linhas = @()
    foreach ($ln in $res.Lines) {
        $x1 = 1e9; $y1 = 1e9; $x2 = 0; $y2 = 0
        foreach ($w in $ln.Words) {
            $b = $w.BoundingRect
            $x1 = [Math]::Min($x1, $b.X); $y1 = [Math]::Min($y1, $b.Y)
            $x2 = [Math]::Max($x2, $b.X + $b.Width); $y2 = [Math]::Max($y2, $b.Y + $b.Height)
        }
        if ($x2 -le $x1) { continue }
        $linhas += , [ordered]@{ texto = (Curto ([string]$ln.Text) 200)
            caixa = @([int]($x1 / $fator), [int]($y1 / $fator), [int](($x2 - $x1) / $fator), [int](($y2 - $y1) / $fator)) }
        if ($linhas.Count -ge 300) { break }
    }
    , $linhas
}

function Op-Olhar {
    Carregar-Visao
    $v = Janela-Valida $req.hwnd
    if (-not $v -or (Titulo-Proibido $v)) { return @{ erro = 'janela_nao_permitida' } }
    $h = [long]$req.hwnd
    if ([W.V]::IsIconic([IntPtr]$h)) { return @{ erro = 'minimizada' } }
    $ret = Retangulo $h
    if ($ret[2] -le 0 -or $ret[3] -le 0) { return @{ erro = 'sem_tamanho' } }
    $bmp = New-Object System.Drawing.Bitmap($ret[2], $ret[3])
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $hdc = $g.GetHdc()
    $ok = [W.V]::PrintWindow([IntPtr]$h, $hdc, 2)  # PW_RENDERFULLCONTENT: a janela mesmo coberta
    $g.ReleaseHdc($hdc)
    if (-not $ok -or (Preta $bmp)) { if (Na-Frente $h) { $g.CopyFromScreen($ret[0], $ret[1], 0, 0, $bmp.Size) } }
    $g.Dispose()
    $linhas = Ler-Ocr $bmp
    $lado = [int]$req.lado_max
    $escala = [Math]::Min(1.0, $lado / [Math]::Max($ret[2], $ret[3]))
    $png = $bmp
    if ($escala -lt 1.0) { $png = New-Object System.Drawing.Bitmap($bmp, [int]($ret[2] * $escala), [int]($ret[3] * $escala)) }
    $ms = New-Object System.IO.MemoryStream
    $png.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
    @{ retangulo = $ret; linhas = $linhas; png_b64 = [Convert]::ToBase64String($ms.ToArray()); escala = $escala }
}

function Op-ClicarPonto {
    Carregar-Visao
    $v = Janela-Valida $req.hwnd
    if (-not $v -or (Titulo-Proibido $v)) { return @{ ok = $false; motivo = 'janela_nao_permitida' } }
    $h = [long]$req.hwnd
    if (-not (Na-Frente $h)) { return @{ ok = $false; motivo = 'fora_da_frente' } }
    $ret = Retangulo $h
    for ($i = 0; $i -lt 4; $i++) { if ($ret[$i] -ne [int]$req.retangulo[$i]) { return @{ ok = $false; motivo = 'janela_mudou' } } }
    $x = [int]$req.x; $y = [int]$req.y
    if ($x -lt 0 -or $y -lt 0 -or $x -ge $ret[2] -or $y -ge $ret[3]) { return @{ ok = $false; motivo = 'fora_da_janela' } }
    [void][W.V]::SetCursorPos($ret[0] + $x, $ret[1] + $y)
    [W.V]::mouse_event(0x2, 0, 0, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 40
    [W.V]::mouse_event(0x4, 0, 0, 0, [UIntPtr]::Zero)
    @{ ok = $true }
}

function Op-Tecla {
    $vk = $TECLAS[[string]$req.tecla]
    if ($null -eq $vk) { return @{ ok = $false; motivo = 'tecla_nao_permitida' } }
    $v = Janela-Valida $req.hwnd
    if (-not $v -or (Titulo-Proibido $v)) { return @{ ok = $false; motivo = 'janela_nao_permitida' } }
    if (-not (Na-Frente ([long]$req.hwnd))) { return @{ ok = $false; motivo = 'fora_da_frente' } }
    $ext = if ($TECLAS_ESTENDIDAS -contains $vk) { 1 } else { 0 }
    [W.U]::keybd_event([byte]$vk, 0, $ext, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 30
    [W.U]::keybd_event([byte]$vk, 0, ($ext -bor 2), [UIntPtr]::Zero)
    @{ ok = $true }
}

function Sem-Acento([string]$s) {
    $d = $s.Normalize([Text.NormalizationForm]::FormD)
    (-join ($d.ToCharArray() | Where-Object { [Globalization.CharUnicodeInfo]::GetUnicodeCategory($_) -ne 'NonSpacingMark' })).ToLower()
}

# A janela (ou aba do Chrome) ja aberta cujo titulo contem o nome; so devolve se for exatamente uma. A aba e selecionada.
function Op-Focar {
    $nome = Sem-Acento ([string]$req.nome)
    if ($nome -notmatch '^[a-z0-9][a-z0-9 .\-]*$') { return @{ hwnd = $null; achadas = 0 } }
    $achadas = New-Object System.Collections.ArrayList
    foreach ($j in $AE::RootElement.FindAll($TS::Children, (New-Object System.Windows.Automation.PropertyCondition($AE::IsControlElementProperty, $true)))) {
        $h = [long]$j.Current.NativeWindowHandle
        if ($h -eq 0 -or -not $j.Current.Name) { continue }
        $v = Janela-Valida $h
        if (-not $v -or (Titulo-Proibido $v)) { continue }
        if ((Sem-Acento $j.Current.Name).Contains($nome)) { [void]$achadas.Add(@{ hwnd = $h; aba = $null; titulo = [string]$j.Current.Name; processo = (Processo-Efetivo $j) }); continue }
        if ($v.chrome -and $j.Current.ClassName -ceq 'Chrome_WidgetWin_1') {
            foreach ($t in @(Abas-Chrome $j)) {
                if ((Sem-Acento $t.Current.Name).Contains($nome)) { [void]$achadas.Add(@{ hwnd = $h; aba = $t; titulo = [string]$t.Current.Name; processo = 'chrome' }) }
            }
        }
    }
    if ($achadas.Count -ne 1) { return @{ hwnd = $null; achadas = $achadas.Count } }
    $a = $achadas[0]
    # selecionar=false so devolve o titulo: o Python confere o bloqueio antes de a aba vir para a frente
    if ($a.aba -and $req.selecionar) {
        $s = $null
        if (-not $a.aba.TryGetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern, [ref]$s)) { return @{ hwnd = $null; achadas = 1 } }
        $s.Select()
    }
    @{ hwnd = $a.hwnd; processo = $a.processo; titulo = $a.titulo }
}

try {
    $r = switch ([string]$req.op) {
        'janelas' { Op-Janelas }
        'abrir_app' { Op-AbrirApp }
        'ler' { Op-Ler }
        'clicar' { Op-Clicar }
        'buscar' { Op-Escrever $true }
        'digitar' { Op-Escrever $false }
        'rolar' { Op-Rolar }
        'voltar' { Op-Voltar }
        'envio' { Op-Envio }
        'midias' { Op-Midias }
        'pausar' { Op-Pausar }
        'midia_controle' { Op-MidiaControle }
        'som' { Op-Som }
        'janela_info' { Op-JanelaInfo }
        'fechar_aba' { Op-FecharAba }
        'olhar' { Op-Olhar }
        'clicar_ponto' { Op-ClicarPonto }
        'tecla' { Op-Tecla }
        'focar' { Op-Focar }
        default { @{ erro = 'op_desconhecida' } }
    }
    Sair $r
} catch {
    Sair @{ erro = $_.Exception.GetType().Name }
}
