# ScreenTranslator

Windows **offline** tray app: screenshot translation, selection (word) translation, window / region live translation.

| Feature | Stack |
|---------|--------|
| UI | Python + PySide6 |
| OCR | PaddleOCR (PP-OCRv6 by default) |
| Translation | Local `llama-server` + Tencent **HY-MT1.5** GGUF |

**中文说明：** [README.md](./README.md) · Settings: [SETTINGS.en.md](./SETTINGS.en.md)

**Optional llama-server GUI (tinker only):** root `启动llama.bat` → `runtime\llama\llama启动.exe` (doc: [LLAMA启动器说明.md](./LLAMA启动器说明.md), Chinese). For daily translation use `run.py` / `翻译.exe`.

---

## What’s in this repo

| Content | How to get it |
|---------|----------------|
| **Source code** | `git clone` / Source zip |
| **runtime (~2 GB)** model + llama + OCR | **Recommended: GitHub Release asset** `runtime-*.zip` |

| Path | Content | Size |
|------|---------|------|
| `runtime/models/` | `HY-MT1.5-1.8B-Q4_K_M.gguf` | ~1.1 GB |
| `runtime/llama/` | `llama-server.exe` + DLLs | ~0.8 GB |
| `runtime/paddlex/` | OCR weights | ~0.13 GB |

### Get runtime (pick one)

| Method | Notes |
|--------|--------|
| **① Release zip (recommended)** | Open **[Releases](../../releases)**, download `runtime-*.zip`, **extract into the project root** → `runtime\models`, `runtime\llama`, `runtime\paddlex` |
| ② Script | `.\scripts\download_runtime.ps1` or `.\setup.ps1 -DownloadRuntime` |
| ③ Manual | See [runtime/README.en.md](./runtime/README.en.md) |

**Large files are not in Git** (no Git LFS).  
**Not in the zip / not in Git:** `venv/`, `config.json`, history DB, logs — create with `setup.ps1` on each PC.

---

## 1. Requirements

### System

| Need | Notes |
|------|--------|
| **Windows 10/11 64-bit** | Only target platform |
| Disk | **≥ 5 GB** free recommended |
| Admin | Usually **not** required |

### Python (required)

| Need | Notes |
|------|--------|
| **Python 3.11–3.13** | **3.12 recommended** |
| **Not 3.14** | Paddle Windows wheels often missing → OCR install fails |

[PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) supports a range of Python versions; the hard limit is **Paddle wheels**, not “3.12 only”.

**Python ≠ CUDA:** Python runs the app/OCR; CUDA 12/13 is only for GPU `llama-server` builds.

```powershell
winget install Python.Python.3.12
py -0p
```

### Hardware

| Setup | Works? | Notes |
|-------|--------|--------|
| NVIDIA GPU + recent driver | Best | GPU OCR + translation |
| iGPU / no discrete GPU | Yes | CPU Paddle + `n_gpu_layers: 0` (slower) |
| RAM | 16 GB+ recommended | |

### Runtime files

Prefer the **Release `runtime-*.zip`**. Still need `venv` + `config.json` via `setup.ps1`.

### Network

| Step | Online? |
|------|---------|
| `git clone` source | Yes |
| Download Release runtime zip (~2 GB) | Yes (recommended) |
| `pip` / Paddle | Yes |
| Daily translation | **No** (localhost) |

---

## 2. Setup on a new PC

```powershell
git clone <repo-url> ScreenTranslator
cd ScreenTranslator
# Download runtime-*.zip from Releases → extract into this folder
# (you should see .\runtime\models\*.gguf)

# Allow scripts if needed:
# Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

.\setup.ps1              # NVIDIA
.\setup.ps1 -CpuOnly     # no discrete GPU
# Only if runtime still missing:
.\setup.ps1 -DownloadRuntime

.\setup.ps1 -Check
venv\Scripts\pythonw.exe run.py
```

Optional launcher: `.\build.ps1` → `翻译.exe`.

### Manual runtime (no Release zip)

1. HuggingFace: **`HY-MT1.5-1.8B-Q4_K_M.gguf`** → `runtime\models\`
2. [llama.cpp Releases](https://github.com/ggml-org/llama.cpp/releases) → `runtime\llama\`
3. `.\setup.ps1` / first OCR for paddlex  
Details: [runtime/README.en.md](./runtime/README.en.md)

### Config tips (`config.json`)

| Key | When |
|-----|------|
| `n_gpu_layers` | Set `0` without NVIDIA / OOM |
| `threads` | CPU cores (`setup` estimates) |
| `ui_language` | `zh` / `en` — **Settings UI language** |
| Hotkeys | Settings → Hotkeys; mouse side buttons: `mouse.x1` / `mouse.x2` |

Do **not** copy someone else’s `venv` across machines; re-run `setup.ps1`.

English guide to each setting: **[SETTINGS.en.md](./SETTINGS.en.md)**.

---

## 3. Features & default hotkeys

| Action | Default |
|--------|---------|
| Screenshot translate | Alt+Q |
| Selection translate | Alt+W |
| Window live translate | Alt+E |
| Region live translate | Alt+R |
| Screenshot OCR only | Alt+S |

Tray: history, settings, log, quit.  
Only **one** continuous session at a time; switch **Subtitle ↔ Annotation** from the floating bar while running.

---

## 4. Troubleshooting

| Issue | Fix |
|-------|-----|
| Model file only a few KB | Download **Release `runtime-*.zip`** into project root |
| Missing runtime | Releases asset, not “Source code” zip |
| No paddlepaddle wheel | Use Python **3.12**, not 3.14 |
| llama fails on GPU | `n_gpu_layers: 0` or CPU llama build |
| Hotkeys dead | Rebind in Settings; try `mouse.x1` |

Log: `app.log` (tray → Open log).

---

## 5. Commands

```powershell
.\setup.ps1
.\setup.ps1 -DownloadRuntime
.\setup.ps1 -CpuOnly
.\setup.ps1 -Check
.\scripts\download_runtime.ps1
.\build.ps1
venv\Scripts\pythonw.exe run.py
```

Version: `app/__init__.py`.

---

## Disclaimer

The **download and setup instructions** in this document were **generated with AI** and **may be wrong or outdated**.  
Always verify against the actual repo, Release asset names, and your machine. You are responsible for checking steps before running them.
