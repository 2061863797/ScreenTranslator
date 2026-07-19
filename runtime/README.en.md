# runtime assets

The `runtime` directory has three parts:

| Folder | Supplied by | Content |
|--------|-------------|---------|
| `paddlex\official_models\` | Source package | PaddleOCR detection and recognition models |
| `models\` | Release **models** asset | HY-MT GGUF translation model |
| `llama\` | Release **llama** asset | `llama-server.exe` and its DLLs |

`config.json` and `venv` are generated locally on each PC and are not runtime Release assets.

## Default Release setup

Releases provide only the **models** and **llama** assets. The PaddleX OCR models already ship with the source package and do not need a separate download.

The current `llama` asset is the NVIDIA CUDA 13 build. It is intended for an NVIDIA GPU with a recent working driver. CUDA runtime DLLs are included; installing the CUDA Toolkit separately is not required.

After extracting both the **models** and **llama** assets into the current `runtime\` directory, the layout must be:

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

## CPU setup or missing Release assets

Without an NVIDIA GPU, download and use the CPU llama build:

```powershell
.\setup.ps1 -CpuOnly -DownloadRuntime
```

If the default CUDA llama asset was already extracted, replace it with the CPU build:

```powershell
.\scripts\download_runtime.ps1 -CpuOnly -SkipModel -Force
.\setup.ps1 -CpuOnly
```

With NVIDIA but without the Release assets:

```powershell
.\setup.ps1 -DownloadRuntime
```

Automatic downloads use these official sources:

| Asset | Official URL |
|-------|--------------|
| HY-MT GGUF | https://huggingface.co/tencent/HY-MT1.5-1.8B-GGUF |
| llama.cpp | https://github.com/ggml-org/llama.cpp/releases |

See the root [README.en.md](../README.en.md) for the complete installation guide.
