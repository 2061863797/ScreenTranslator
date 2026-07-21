# LocalScreen Translator runtime assets

The `runtime` directory has three parts:

| Folder | Supplied by | Content |
|--------|-------------|---------|
| `ocr\` | Release **ocr** asset | PP-OCRv6 ONNX models, character table, and integrity manifest |
| `models\` | Release **models** asset | HY-MT GGUF translation model |
| `llama\` | Release **llama** asset | `llama-server.exe` and its DLLs |

`config.json` and `venv` are generated locally on each PC and are not runtime Release assets.

## Default Release setup

Releases provide three archives: **ocr**, **models**, and **llama**.

The **llama** asset contains both CPU and NVIDIA CUDA backends. Every PC uses the same asset; compatible GPUs do not require a separate CUDA Toolkit installation.

The archives' top-level folders must be `ocr\`, `models\`, and `llama\`, respectively. Extract all three into the project's `runtime\` directory and allow your archive tool to merge or replace files; the resulting layout must be:

```text
runtime\models\HY-MT1.5-1.8B-Q4_K_M.gguf
runtime\llama\llama-server.exe
runtime\llama\*.dll
runtime\ocr\manifest.json
runtime\ocr\det.onnx
runtime\ocr\rec.onnx
runtime\ocr\characters.txt
```

Check the assets with:

```powershell
.\setup.ps1 -Check
```

## Multiple translation models

`runtime\models\` may contain multiple `.gguf` files. Download additional models yourself and place them directly in this folder. Then choose one under Tray → Settings → Advanced → Model & generation, save, and restart the app.

The settings list accepts only files with a valid GGUF header. A custom model must still be compatible with the bundled `llama.cpp`; verify its translation behavior, prompt format, license, and hardware requirements yourself.

## CPU and translation device

Without an NVIDIA GPU, extract the same **llama** asset. Auto selects the CPU; you can also select CPU under Settings → Advanced → Translation device and restart the app.

See the root [README.en.md](../README.en.md) for the complete installation guide.
