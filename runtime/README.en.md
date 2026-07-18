# runtime directory

Model + llama + OCR ≈ **2 GB**. **Not stored in Git.** Get them from **GitHub Releases** (recommended), scripts, or official sites.

## Get runtime

| Priority | Method |
|----------|--------|
| **Recommended** | Repo **Releases** → download **`runtime-*.zip`** → extract into **project root** (next to `run.py`) |
| Alternative | `.\scripts\download_runtime.ps1` or `.\setup.ps1 -DownloadRuntime` |
| Alternative | Manual links below |

## Layout

| Path | Content | Size |
|------|---------|------|
| `models\HY-MT1.5-1.8B-Q4_K_M.gguf` | Translation model | ~1.1 GB |
| `llama\llama-server.exe` + `*.dll` | Local inference | ~0.8 GB |
| `paddlex\official_models\...` | OCR weights | ~0.13 GB |

Still run `setup.ps1` for `venv` and `config.json`.  
**Source code zips do not include models.**

## Release zip

1. Open the repo → **Releases**  
2. Download `runtime-*.zip`  
3. Extract into `ScreenTranslator\`  

You should see:

```text
ScreenTranslator\runtime\models\*.gguf
ScreenTranslator\runtime\llama\llama-server.exe
ScreenTranslator\runtime\paddlex\...
```

Avoid `runtime\runtime\`.

## Verify

```powershell
Get-Item .\runtime\models\*.gguf | Format-Table Name, Length
.\setup.ps1 -Check
```

GGUF should be ~1 GB.

Optional: root `启动llama.bat` (see `LLAMA启动器说明.md`).

## Manual URLs

| Asset | URL |
|-------|-----|
| Model | https://huggingface.co/tencent/HY-MT1.5-1.8B-GGUF |
| llama | https://github.com/ggml-org/llama.cpp/releases |

Flatten server + DLLs into `runtime\llama\`. Do not mix CUDA 12 and 13.

Chinese: [README.md](./README.md).

---

## Disclaimer

Download/setup notes here were **AI-generated** and **may be wrong**. Verify Release assets and paths yourself.
