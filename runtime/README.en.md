# runtime directory

Large files are shipped **with the repo** via **[Git LFS](https://git-lfs.com)** (see root `.gitattributes`).

| Path | Content | Size | LFS |
|------|---------|------|-----|
| `models\HY-MT1.5-1.8B-Q4_K_M.gguf` | Translation model | ~1.1 GB | Yes |
| `llama\llama-server.exe` + `*.dll` | Local inference | ~0.8 GB | Yes |
| `paddlex\official_models\...` | OCR weights | ~0.13 GB | Yes |

**Total ~2 GB.** After clone + LFS pull, paths should be ready. Still run `setup.ps1` for `venv` and `config.json`.

## Verify LFS

```powershell
# From repo root (ScreenTranslator\), not inside runtime\
git lfs install
git lfs pull
Get-Item .\runtime\models\*.gguf | Format-Table Name, Length
# Length should be ~1e9, not ~130 bytes
```

Optional GUI for llama-server only: root `启动llama.bat` (see `LLAMA启动器说明.md`, Chinese).

GitHub **Source zip** usually has **pointers only**, not real models.

## Manual download

From repo root:

```powershell
.\scripts\download_runtime.ps1
# or
.\setup.ps1 -DownloadRuntime
```

| Asset | Source |
|-------|--------|
| Model | https://huggingface.co/tencent/HY-MT1.5-1.8B-GGUF |
| llama | https://github.com/ggml-org/llama.cpp/releases (Windows CUDA 12/13 or CPU) |

Flatten `llama-server.exe` and all DLLs into `runtime\llama\`. Do not mix CUDA 12 and 13 DLLs.

## Check

```powershell
.\setup.ps1 -Check
```

Chinese: [README.md](./README.md) in this folder.
