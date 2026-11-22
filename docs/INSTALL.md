# Install

Groov runs on Windows 10 or 11 with an NVIDIA GPU. Run every command from the repository folder, in your own PowerShell.

## 1. Get the code

```powershell
git clone https://github.com/brunopet8/Groov.git
cd Groov
```

## 2. Conversation environment (`.venv-conversa`)

```powershell
py -3.12 -m venv .venv-conversa
.venv-conversa\Scripts\python -m pip install -r requirements-conversa.txt
.venv-conversa\Scripts\python -m pip uninstall -y onnxruntime
.venv-conversa\Scripts\python -m pip install onnxruntime-gpu==1.24.4
```

pipecat installs the CPU build of onnxruntime. The GPU build replaces it: both use the same module name.

## 3. Voice environment (`.venv-qwen`)

```powershell
uv venv --python 3.12 .venv-qwen
uv pip install -p .venv-qwen\Scripts\python.exe -r requirements-qwen.txt
.venv-qwen\Scripts\python -c "from huggingface_hub import snapshot_download as s; s('Qwen/Qwen3-TTS-12Hz-0.6B-Base', revision='5d83992436eae1d760afd27aff78a71d676296fc')"
```

The last command downloads about 2.5 GB of weights once. After that the voice server runs offline. Groov starts it by itself (`src/voz_servidor.py`, `127.0.0.1` only).

## 4. Your voice

Groov speaks with a voice cloned from a short reference recording.

1. Record 7 to 15 seconds of clear speech in Portuguese. Use your own voice, or a voice you have the right to use.
2. Save it as `hermes/voz/ref_qwen.wav`.
3. Write the exact words of the recording in `hermes/voz/ref_qwen.txt`.

`hermes/voz/` is git-ignored: your voice never goes to the repository.

## 5. Wake-word model

```powershell
mkdir hermes\wake
.venv-conversa\Scripts\python -c "import openwakeword.utils as u; u.download_models(['hey_jarvis']); u.download_models(['hey_jarvis'], target_directory='hermes/wake')"
```

This puts `hermes/wake/hey_jarvis_v0.1.onnx` in place. The model is CC BY-NC-SA 4.0: personal, non-commercial use only.

## 6. Claude Code CLI

Install the [Claude Code CLI](https://docs.claude.com/en/docs/claude-code) and run `claude` once to sign in with your own Claude Pro or Max plan. Groov finds `claude` on your PATH or in `%USERPROFILE%\.local\bin` and uses that sign-in. It never asks for an API key.

## 7. Your settings

```powershell
mkdir privado
copy .env.example privado\.env
notepad privado\.env
```

Fill in what you want; empty values keep the neutral default. `privado/` is git-ignored.

| Setting | Effect when empty |
|---|---|
| `GROOV_NOME_USUARIO` | Groov does not use your name. |
| `GROOV_CIDADE`, `GROOV_LAT`, `GROOV_LON` | No weather; Groov says the city is missing. |
| `GROOV_MAR` (`place;lat;lon`) | The briefing skips the sea. |
| `GROOV_VAULT` | The vault lives in `vault/` inside the repository. |
| `GROOV_PERFIL_NETFLIX` | Groov asks which Netflix profile to pick. |
| `GROOV_FRASES_EXTRA` | Only the built-in wake phrases. |
| `GROOV_HOTWORDS_EXTRA` | Whisper gets only the built-in names to listen for. |
| `GROOV_WORKSPACES_EXTRA` | Tier-3 work only in the vault and your Claude Code folders. |
| `TYPESAFE_API_KEY` | No Jev triage: everything goes to Haiku. |
| `GOOGLE_API_KEY` | No web research. |
| `TRELLO_KEY`, `TRELLO_TOKEN`, `TRELLO_QUADROS` | No Trello. |
| `TRELLO_QUADROS_CONTAGEM` | Every board in `TRELLO_QUADROS` is treated as a task board. |
| `PLAYWRIGHT_MCP_EXTENSION_TOKEN` | Pages are read through UI Automation (step 9). |

## 8. Briefing phrases (optional)

The morning briefing plays phrases recorded with your Groov voice. Record them once, and again after you change `GROOV_MAR`:

```powershell
.venv-conversa\Scripts\python scripts\gerar_frases.py
```

The voice server must be running (step 10 starts it).

## 9. Page probe (optional)

The PC-control loop reads pages in Chrome better through the Playwright MCP server:

```powershell
cd ferramentas\navegador
npm ci
cd ..\..
```

It also needs the "Playwright Extension" in Chrome and its token in `PLAYWRIGHT_MCP_EXTENSION_TOKEN`. Without them, Groov reads pages through UI Automation.

## 10. Run

```powershell
.venv-conversa\Scripts\python -m src.conversa.servidor
```

In a second PowerShell, open the window:

```powershell
.venv-conversa\Scripts\python -m src.conversa.abrir_janela
```

Say "Hey JARVIS". The window shows full screen on your 2nd monitor while Groov is awake (on the main one if you have only one).

To start Groov with Windows, run `scripts\conversa_no_inicio.ps1` once.

## 11. Tests (optional)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest tests
.venv-conversa\Scripts\python -m pytest tests
node --test "tests/janela/*.test.js"
```

Tests never read your `privado/.env`.
