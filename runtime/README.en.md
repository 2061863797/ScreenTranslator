# runtime assets

The `runtime` directory has three parts:

| Folder | Supplied by | Content |
|--------|-------------|---------|
| `paddlex\official_models\` | Complete Release **runtime** asset | PaddleOCR detection and recognition models |
| `models\` | Complete Release **runtime** asset | HY-MT GGUF translation model |
| `llama\` | Complete Release **runtime** asset | `llama-server.exe` and its DLLs |

`config.json` and `venv` are generated locally on each PC and are not runtime Release assets.

## Default Release setup

Releases provide one complete **runtime** archive containing the PaddleX OCR models, HY-MT translation model, and llama-server.

The `runtime\llama` directory in the complete asset is the NVIDIA CUDA 13 build. It is intended for an NVIDIA GPU with a recent working driver. CUDA runtime DLLs are included; installing the CUDA Toolkit separately is not required.

The archive's top-level folder must be `runtime\`. Extract it into the project root and allow your archive tool to merge or replace files; the resulting layout must be:

```text
runtime\models\HY-MT1.5-1.8B-Q4_K_M.gguf
runtime\llama\llama-server.exe
runtime\llama\*.dll
runtime\paddlex\official_models\PP-OCRv6_medium_det\
runtime\paddlex\official_models\PP-OCRv6_medium_rec\
```

Check the assets with:

```powershell
.\setup.ps1 -Check
```

## Multiple translation models

`runtime\models\` may contain multiple `.gguf` files. Download additional models yourself and place them directly in this folder. Then choose one under Tray → Settings → Advanced → Model & generation, save, and restart the app.

The settings list accepts only files with a valid GGUF header. A custom model must still be compatible with the bundled `llama.cpp`; verify its translation behavior, prompt format, license, and hardware requirements yourself.

## CPU setup or missing complete runtime asset

Without an NVIDIA GPU, if the complete **runtime** asset is already extracted, keep its model and OCR files and replace the CUDA llama with the CPU build:

```powershell
.\scripts\download_runtime.ps1 -CpuOnly -SkipModel -Force
.\setup.ps1 -CpuOnly
```

If the complete **runtime** asset is unavailable, you can instead let the script download the required files:

```powershell
.\setup.ps1 -CpuOnly -DownloadRuntime
```

With NVIDIA but without the complete **runtime** asset:

```powershell
.\setup.ps1 -DownloadRuntime
```

Automatic downloads use these official sources:

| Asset | Official URL |
|-------|--------------|
| HY-MT GGUF | https://huggingface.co/tencent/HY-MT1.5-1.8B-GGUF |
| llama.cpp | https://github.com/ggml-org/llama.cpp/releases |

See the root [README.en.md](../README.en.md) for the complete installation guide.
