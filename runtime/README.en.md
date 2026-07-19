# runtime

| Folder | In source repo? | Notes |
|--------|-----------------|--------|
| `paddlex/official_models` | Yes | OCR models |
| `models/` | No | GGUF — Releases **models** zip |
| `llama/` | No | llama-server + DLLs — Releases **llama** zip |

`config.json` is local (not in git). Create with `.\setup.ps1` or copy `config.example.json`.

## Two Release packages

1. Download the **models** and **llama** zips (not a single full `runtime-*.zip`).
2. Extract into the **project root** (next to `run.py`) so you have:

```text
runtime\models\HY-MT1.5-1.8B-Q4_K_M.gguf
runtime\llama\llama-server.exe   (DLLs alongside)
```

If the zip already contains a `models\` / `llama\` folder, extract under `runtime\`.

## Fallback (no Release)

```powershell
.\setup.ps1 -DownloadRuntime
# or
.\scripts\download_runtime.ps1
```

| Asset | URL |
|-------|-----|
| Model | https://huggingface.co/tencent/HY-MT1.5-1.8B-GGUF |
| llama | https://github.com/ggml-org/llama.cpp/releases |

Flatten llama exe + DLLs into `runtime\llama\`.

Check: `.\setup.ps1 -Check`

**Docs may be AI-generated; verify yourself.**
