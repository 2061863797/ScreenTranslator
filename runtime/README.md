# runtime

| 目录 | 是否随源码 | 说明 |
|------|------------|------|
| `paddlex/official_models` | 是 | OCR 模型 |
| `models/` | 否 | 翻译用 GGUF，见 Releases **models** 包 |
| `llama/` | 否 | llama-server + DLL，见 Releases **llama** 包 |

`config.json` 为本机文件，不进仓库；用 `.\setup.ps1` 生成或复制 `config.example.json`。

## Releases 两个压缩包

1. 下载 **models**、**llama** 各一个 zip（不要再找整包 `runtime-*.zip`）。
2. 解压到**项目根**（与 `run.py` 同级），结果应是：

```text
runtime\models\HY-MT1.5-1.8B-Q4_K_M.gguf   （或其它量化）
runtime\llama\llama-server.exe             （与 DLL 同目录）
```

若 zip 内层是 `models\` / `llama\` 文件夹，解到 `runtime\` 下即可；若已是文件列表，分别放进上述两目录。

## 备选（无 Release 时）

项目根：

```powershell
.\setup.ps1 -DownloadRuntime
# 或
.\scripts\download_runtime.ps1
```

| 资源 | 地址 |
|------|------|
| 模型 | https://huggingface.co/tencent/HY-MT1.5-1.8B-GGUF |
| llama | https://github.com/ggml-org/llama.cpp/releases |

llama 的 exe 与 dll **平铺**进 `runtime\llama\`。

检查：`.\setup.ps1 -Check`

**说明可能由 AI 生成，请自行核对。**
