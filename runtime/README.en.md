# runtime

Translation model + llama-server (~2GB) + OCR models.

- **OCR (`paddlex/official_models`)**: included in the source repo.  
- **Translation model / llama**: still from Releases or the URLs below.

## Get files (model + llama)

1. Repo **Releases** → **`runtime-*.zip`**  
2. Extract to **project root** (next to `run.py`)  

Expect: `runtime\models\*.gguf`, `runtime\llama\llama-server.exe`; OCR at `runtime\paddlex\official_models\` (ships with source).

Fallback: `.\setup.ps1 -DownloadRuntime`, or:

| Asset | URL |
|-------|-----|
| Model | https://huggingface.co/tencent/HY-MT1.5-1.8B-GGUF |
| llama | https://github.com/ggml-org/llama.cpp/releases |

Flatten llama exe + DLLs into `runtime\llama\`.

Check: `.\setup.ps1 -Check`

**Docs may be AI-generated; verify yourself.**
