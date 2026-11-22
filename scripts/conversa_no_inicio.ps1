# Liga a conversa do GROOV ao entrar no Windows: um atalho sobe o servidor (src.conversa.servidor) e outro abre a janela
# no Chrome assim que a porta 7860 responde. Já inicia os dois agora (feche antes o servidor e a janela atuais).
# A janela sobe oculta (sem botão na barra de tarefas) e só aparece, em tela cheia no 2º monitor, quando o GROOV acorda (src/conversa/tela.py);
# o perfil e as opções do Chrome ficam em src/conversa/abrir_janela.py.
# Rode no SEU PowerShell, fora do app Claude (o app redireciona gravações em AppData).
# Para desfazer: apague os atalhos "GROOV conversa" e "GROOV janela" da pasta Inicializar
# (ou desative em Gerenciador de Tarefas > Aplicativos de inicialização) e, se quiser, a pasta %LOCALAPPDATA%\GROOV.
$raiz = Split-Path $PSScriptRoot -Parent
$inicio = [Environment]::GetFolderPath('Startup')
$chrome = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
if (-not (Test-Path $chrome)) { throw "Chrome não encontrado em $chrome" }
$shell = New-Object -ComObject WScript.Shell
'JARVIS conversa.lnk', 'JARVIS janela.lnk' | ForEach-Object { Remove-Item (Join-Path $inicio $_) -ErrorAction SilentlyContinue }  # legado: atalhos com o nome antigo

$servidor = $shell.CreateShortcut((Join-Path $inicio 'GROOV conversa.lnk'))
$servidor.TargetPath = Join-Path $raiz '.venv-conversa\Scripts\pythonw.exe'
$servidor.Arguments = '-m src.conversa.servidor'
$servidor.WorkingDirectory = $raiz
$servidor.Description = 'Conversa por voz do GROOV (servidor local)'
$servidor.Save()

$janela = $shell.CreateShortcut((Join-Path $inicio 'GROOV janela.lnk'))
$janela.TargetPath = Join-Path $raiz '.venv-conversa\Scripts\pythonw.exe'
$janela.Arguments = '-m src.conversa.abrir_janela'
$janela.WorkingDirectory = $raiz
$janela.Description = 'Janela do GROOV: sobe escondida e aparece em tela cheia no 2o monitor quando ele acorda'
$janela.Save()

Invoke-Item (Join-Path $inicio 'GROOV conversa.lnk')
Invoke-Item (Join-Path $inicio 'GROOV janela.lnk')
Write-Output "Atalhos criados em $inicio e conversa iniciada (a janela abre oculta quando o servidor responder; com perfil novo, abra-a uma vez à mão com chrome --app=http://localhost:7860/ --user-data-dir=$env:LOCALAPPDATA\GROOV\chrome e permita o microfone)."
