# runtime

Model + llama + OCR (~2GB).

## Get files

1. Repo **Releases** → **`runtime-*.zip`**  
2. Extract to **project root** (next to `run.py`)  

Expect: `runtime\models\*.gguf`, `runtime\llama\llama-server.exe`, `runtime\paddlex\`.

Fallback: `.\setup.ps1 -DownloadRuntime`, or:

| Asset | URL |
|-------|-----|
| Model | https://huggingface.co/tencent/HY-MT1.5-1.8B-GGUF |
| llama | https://github.com/ggml-org/llama.cpp/releases |

Flatten llama exe + DLLs into `runtime\llama\`.

Check: `.\setup.ps1 -Check`

**Docs may be AI-generated; verify yourself.**
