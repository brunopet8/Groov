# Liga o servidor de voz do GROOV ao entrar no Windows (atalho na pasta Inicializar) e já o inicia.
# Rode no SEU PowerShell, fora do app Claude (o app redireciona gravações em AppData).
# Para desfazer: apague o atalho "GROOV voz" (ou desative em Gerenciador de Tarefas > Aplicativos de inicialização).
$raiz = Split-Path $PSScriptRoot -Parent
Remove-Item (Join-Path ([Environment]::GetFolderPath('Startup')) 'JARVIS voz.lnk') -ErrorAction SilentlyContinue  # legado: atalho com o nome antigo
$atalho = Join-Path ([Environment]::GetFolderPath('Startup')) 'GROOV voz.lnk'
$s = (New-Object -ComObject WScript.Shell).CreateShortcut($atalho)
$s.TargetPath = Join-Path $raiz '.venv-qwen\Scripts\pythonw.exe'
$s.Arguments = '"' + (Join-Path $raiz 'src\voz_servidor.py') + '"'
$s.WorkingDirectory = $raiz
$s.Description = 'Servidor de voz local do GROOV (Qwen3-TTS)'
$s.Save()
Invoke-Item $atalho
Write-Output "Atalho criado e servidor iniciado: $atalho (carrega em ~1 min; log em $raiz\voz_servidor.log)"
