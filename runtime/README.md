# runtime

翻译模型 + llama-server（约 2GB）+ OCR 模型。

- **OCR（`paddlex/official_models`）**：随源码仓库提供，clone 后即可用。  
- **翻译模型 / llama**：仍从 Releases 或下方地址获取。

## 怎么拿（模型 + llama）

1. 仓库 **Releases** → 下载 **`runtime-*.zip`**  
2. 解压到**项目根**（与 `run.py` 同级）  

应出现：`runtime\models\*.gguf`、`runtime\llama\llama-server.exe`；OCR 在 `runtime\paddlex\official_models\`（源码已带）。

备选：项目根 `.\setup.ps1 -DownloadRuntime`，或：

| 资源 | 地址 |
|------|------|
| 模型 | https://huggingface.co/tencent/HY-MT1.5-1.8B-GGUF |
| llama | https://github.com/ggml-org/llama.cpp/releases |

llama 的 exe 与 dll 平铺进 `runtime\llama\`。

检查：`.\setup.ps1 -Check`

**说明可能由 AI 生成，请自行核对。**
