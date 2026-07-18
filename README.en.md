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

The repo includes **source code and large runtime files** via **[Git LFS](https://git-lfs.com)** (GitHub 100 MB file limit):

| Path | Content | Size (approx.) |
|------|---------|----------------|
| `runtime/models/` | `HY-MT1.5-1.8B-Q4_K_M.gguf` | ~1.1 GB |
| `runtime/llama/` | `llama-server.exe` + CUDA/CPU DLLs | ~0.8 GB |
| `runtime/paddlex/` | OCR weights (PP-OCRv6 medium) | ~0.13 GB |
| **Total** | | **~2 GB** |

**When cloning:**

1. Install Git LFS: `git lfs install` ([git-lfs.com](https://git-lfs.com) or `winget install GitHub.GitLFS`)
2. `git clone …` then `git lfs pull`
3. Confirm the GGUF is ~1 GB, not a few‑KB pointer file

**When pushing:** LFS uploads ~2 GB. Free GitHub LFS quota may be insufficient; you may need a [Data Pack](https://docs.github.com/en/billing/managing-billing-for-git-large-file-storage) or host binaries as Release assets.

If LFS fails: `.\scripts\download_runtime.ps1` or see [runtime/README.en.md](./runtime/README.en.md).

**Not in Git:** `venv/`, `config.json`, history DB, logs — create on each machine.

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

After a full LFS clone you should have `runtime/models`, `runtime/llama`, `runtime/paddlex`.  
Still need: `venv` via `setup.ps1`, and `config.json` generated from `config.example.json`.

### Network

| Step | Online? |
|------|---------|
| `git clone` / `git lfs pull` | Yes |
| `pip` / Paddle install | Yes |
| Daily translation | **No** (localhost only) |

---

## 2. Setup on a new PC

```powershell
git lfs install
git clone <repo-url> ScreenTranslator
cd ScreenTranslator
git lfs pull

# Allow scripts if needed:
# Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

.\setup.ps1              # NVIDIA
.\setup.ps1 -CpuOnly     # no discrete GPU
# If runtime incomplete:
.\setup.ps1 -DownloadRuntime

.\setup.ps1 -Check
venv\Scripts\pythonw.exe run.py
```

Optional launcher: `.\build.ps1` → `翻译.exe` (still needs local `venv` + `app`).

### Manual runtime (if LFS/download fails)

1. HuggingFace: **`HY-MT1.5-1.8B-Q4_K_M.gguf`** → `runtime\models\`
2. [llama.cpp Releases](https://github.com/ggml-org/llama.cpp/releases): CUDA 12/13 or CPU zip → flatten `llama-server.exe` + DLLs into `runtime\llama\`
3. `.\setup.ps1` then first OCR may fill `runtime\paddlex`

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
| Model file only a few KB | `git lfs install` + `git lfs pull` |
| LFS quota on push | Buy LFS data pack or use Release assets |
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
