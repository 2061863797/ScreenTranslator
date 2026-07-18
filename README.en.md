# ScreenTranslator

Windows **offline** tray app: screenshot translation, selection translate, window / region live translation.

**License:** [Apache License 2.0](./LICENSE) (source; third-party/models: [NOTICE](./NOTICE))

**中文说明：** [README.md](./README.md) · Settings: [SETTINGS.en.md](./SETTINGS.en.md)

**Optional llama-server GUI:** root `启动llama.bat` (see [LLAMA启动器说明.md](./LLAMA启动器说明.md)). Daily use: `run.py` / `翻译.exe`.

| Feature | Stack |
|---------|--------|
| UI | Python + PySide6 |
| OCR | PaddleOCR (PP-OCRv6) |
| Translation | Local `llama-server` + **HY-MT1.5** GGUF |

---

## 1. Requirements

### System & hardware

| Need | Notes |
|------|--------|
| **Windows 10/11 64-bit** | Only supported OS |
| Disk | **≥ 5 GB** free recommended |
| **NVIDIA GPU** (optional) | Faster; CPU works but slower |
| RAM | **16 GB+** recommended |
| Admin | Usually not required |

### Python (required)

| Need | Notes |
|------|--------|
| **Python 3.11–3.13** | **3.12 recommended** |
| **Not 3.14** | Paddle wheels often missing → OCR will not install |

```powershell
winget install Python.Python.3.12
py -0p
```

Python ≠ CUDA: Python runs the app/OCR; CUDA 12/13 only affects GPU llama builds.

### Files you need

```text
ScreenTranslator/
  app/  run.py  setup.ps1  …
  runtime/
    models/…gguf
    llama/llama-server.exe + *.dll
    paddlex/…
  venv/           ← created by setup
  config.json     ← created by setup
```

| Part | Where from |
|------|------------|
| App source | **Source / Code** ZIP or `git clone` |
| **runtime** (~2 GB) | **Releases** asset **`runtime-*.zip`** (recommended), or download scripts / manual (see [runtime/README.en.md](./runtime/README.en.md)) |

### If you only download ZIPs

| Download | Contains | You still need |
|----------|----------|----------------|
| **Source code ZIP** | App + docs, **no** models | **Release `runtime-*.zip`** extracted to the same project root; Python 3.12; run `setup.ps1` |
| **runtime-*.zip** | Models + llama + OCR | Extract into the **source** folder root (not a complete app by itself) |
| Full bundle (if provided) | See that Release’s notes | Often still need local `setup.ps1` for `venv` |

**Minimum for “ZIP only” install:**

1. Windows 10/11 64-bit  
2. **Python 3.12** (or 3.11 / 3.13) installed  
3. Source folder + **runtime** extracted correctly  
4. Network once for `pip` / Paddle  
5. ~**5 GB** free disk  

After extract you should have `runtime\models\*.gguf` and `runtime\llama\llama-server.exe` under the project root. Avoid `runtime\runtime\...`.

### Network

| Step | Online? |
|------|---------|
| Download source / runtime zip | Yes |
| First `setup.ps1` | Yes |
| Daily translation | **No** (localhost) |

---

## 2. Install & run

All paths are relative to the **project root** (folder that contains `run.py`).

### 1. Get the app

- GitHub: **Code → Download ZIP**, or  
- `git clone <repo-url>`

### 2. Get runtime (recommended: Release)

1. Open **Releases** on this repo  
2. Download **`runtime-*.zip`**  
3. Extract into the **project root** (same level as `run.py`)

Alternative: `.\scripts\download_runtime.ps1` or `.\setup.ps1 -DownloadRuntime`.

### 3. Install environment

```powershell
# Set-ExecutionPolicy -Scope CurrentUser RemoteSigned   # if needed

.\setup.ps1              # with NVIDIA
.\setup.ps1 -CpuOnly     # no discrete GPU
.\setup.ps1 -Check
```

### 4. Start

```powershell
venv\Scripts\pythonw.exe run.py
```

Optional: `.\build.ps1` → `翻译.exe`.

### 5. Optional config

| Key | Notes |
|-----|--------|
| `n_gpu_layers` | Use `0` without NVIDIA |
| `ui_language` | `zh` / `en` |
| Hotkeys | Keyboard or `mouse.x1` / `mouse.x2` |

See [SETTINGS.en.md](./SETTINGS.en.md).

---

## 3. Features & default hotkeys

| Action | Default |
|--------|---------|
| Screenshot translate | Alt+Q |
| Selection translate | Alt+W |
| Window live translate | Alt+E |
| Region live translate | Alt+R |
| Screenshot OCR | Alt+S |

One continuous session at a time; switch **Subtitle ↔ Annotation** on the floating bar while running.

---

## 4. Troubleshooting

| Issue | Fix |
|-------|-----|
| No model / server fails | Extract **Release runtime zip** to project root |
| Source only | Source zip has no models — also get `runtime-*.zip` |
| No paddlepaddle wheel | Use **Python 3.12**, not 3.14 |
| GPU / llama fails | `n_gpu_layers: 0` |
| Hotkeys dead | Rebind in Settings |

Log: `app.log`.

---

## 5. Commands

```powershell
.\setup.ps1
.\setup.ps1 -DownloadRuntime
.\setup.ps1 -CpuOnly
.\setup.ps1 -Check
venv\Scripts\pythonw.exe run.py
```

Version: `app/__init__.py`.

---

## License

- **Source code:** [Apache License 2.0](./LICENSE)  
- **Third-party & models:** [NOTICE](./NOTICE). Model weights use their own licenses.

---

## Disclaimer

Download/setup docs may be **AI-generated** and **wrong or outdated**. Verify Release names and your environment yourself before running commands.
