# runtime

模型 + llama + OCR（约 2GB）。

## 怎么拿

1. 仓库 **Releases** → 下载 **`runtime-*.zip`**  
2. 解压到**项目根**（与 `run.py` 同级）  

应出现：`runtime\models\*.gguf`、`runtime\llama\llama-server.exe`、`runtime\paddlex\`。

备选：项目根 `.\setup.ps1 -DownloadRuntime`，或：

| 资源 | 地址 |
|------|------|
| 模型 | https://huggingface.co/tencent/HY-MT1.5-1.8B-GGUF |
| llama | https://github.com/ggml-org/llama.cpp/releases |

llama 的 exe 与 dll 平铺进 `runtime\llama\`。

检查：`.\setup.ps1 -Check`

**说明可能由 AI 生成，请自行核对。**
