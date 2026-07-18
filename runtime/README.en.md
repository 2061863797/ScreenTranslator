# runtime directory

Large files (model + llama + OCR) total about **2 GB**. Get them by **any one** of:

| Priority | Method |
|----------|--------|
| **Recommended** | Download **`runtime-*.zip`** from this repo’s **[GitHub Releases](../../releases)**, extract into the **project root** (next to `run.py`) so you get this `runtime\` folder |
| Alternative | Git LFS: `git lfs pull` |
| Alternative | From repo root: `.\scripts\download_runtime.ps1` or `.\setup.ps1 -DownloadRuntime` |
| Alternative | Manual downloads below |

## Layout

| Path | Content | Size |
|------|---------|------|
| `models\HY-MT1.5-1.8B-Q4_K_M.gguf` | Translation model | ~1.1 GB |
| `llama\llama-server.exe` + `*.dll` | Local inference | ~0.8 GB |
| `paddlex\official_models\...` | OCR weights | ~0.13 GB |

Still run `setup.ps1` for `venv` and `config.json`. **Source code** zips do **not** include real model blobs.

## Using the Release zip

1. Open the repo → **Releases**  
2. Download the runtime asset (e.g. `runtime-v1.1.0.zip`)  
3. Extract into `ScreenTranslator\`  

You should have:

```text
ScreenTranslator\runtime\models\*.gguf
ScreenTranslator\runtime\llama\llama-server.exe
ScreenTranslator\runtime\paddlex\...
```

Avoid double nesting (`runtime\runtime\`).

## Verify

```powershell
# repo root
Get-Item .\runtime\models\*.gguf | Format-Table Name, Length
.\setup.ps1 -Check
```

GGUF should be ~1 GB, not ~100 bytes (LFS pointer).

Optional llama GUI: root `启动llama.bat` (see `LLAMA启动器说明.md`).

## Manual sources

| Asset | URL |
|-------|-----|
| Model | https://huggingface.co/tencent/HY-MT1.5-1.8B-GGUF |
| llama | https://github.com/ggml-org/llama.cpp/releases |

Flatten `llama-server.exe` + DLLs into `runtime\llama\`. Do not mix CUDA 12 and 13.

Chinese: [README.md](./README.md).
