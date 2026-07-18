# ScreenTranslator

Windows offline tray app: screenshot / selection / window·region live translation.  
OCR = PaddleOCR · Translation = local llama-server + HY-MT1.5.

**License:** [Apache-2.0](./LICENSE) (source) · third-party: [NOTICE](./NOTICE)  
**中文:** [README.md](./README.md)

---

## Requirements

| Need | Notes |
|------|--------|
| Windows 10/11 64-bit | |
| **Python 3.12** (3.11/3.13 OK) | **Not 3.14** (Paddle often fails) |
| ~5GB+ disk | |
| NVIDIA GPU | Optional; CPU works (slower) |

---

## Install

### 1. Get source

**Code → Download ZIP**, or `git clone` this repo.

### 2. Get models (~2GB)

**Releases** → download **`runtime-*.zip`** → extract into the **project root** (same folder as `run.py`).

You should see:

```text
ScreenTranslator\
  run.py
  runtime\models\*.gguf
  runtime\llama\llama-server.exe
  runtime\paddlex\...
```

> Source code ZIP has **no models**. Always get the Release runtime package too.

Fallback: [runtime/README.en.md](./runtime/README.en.md) or `.\setup.ps1 -DownloadRuntime`.

### 3. Environment

```powershell
.\setup.ps1            # NVIDIA
.\setup.ps1 -CpuOnly   # no GPU
.\setup.ps1 -Check
```

### 4. Run

```powershell
venv\Scripts\pythonw.exe run.py
```

---

## Default hotkeys

| Action | Key |
|--------|-----|
| Screenshot translate | Alt+Q |
| Selection translate | Alt+W |
| Window live | Alt+E |
| Region live | Alt+R |
| Screenshot OCR | Alt+S |

Tray: settings, history, log. One continuous session at a time.

Config tips: `n_gpu_layers: 0` without GPU; `ui_language` = `zh`/`en`. See [SETTINGS.en.md](./SETTINGS.en.md).

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| No model | Extract Release `runtime-*.zip` to project root |
| Paddle install fails | Use Python 3.12 |
| GPU fails | Set `n_gpu_layers: 0` |
| Already running | Check system tray |

Log: `app.log`.

---

## Other

- Optional llama GUI: `启动llama.bat`  
- Model licenses: [NOTICE](./NOTICE)  

**Setup docs may be AI-generated; verify paths and Release names yourself.**
