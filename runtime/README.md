# runtime 资源目录

模型 / llama / OCR 约 **2GB**，**不进 Git 仓库**。请从本仓库 **GitHub Releases** 下载压缩包，或用脚本/官网补齐。

## 获取方式（任选）

| 优先级 | 方式 |
|--------|------|
| **推荐** | 仓库 **Releases** → 下载 **`runtime-*.zip`** → 解压到**项目根**（与 `run.py` 同级） |
| 备选 | 项目根：`.\scripts\download_runtime.ps1` 或 `.\setup.ps1 -DownloadRuntime` |
| 备选 | 下方官网手动下载 |

## 目录说明

| 路径 | 内容 | 大约体积 |
|------|------|----------|
| `models\HY-MT1.5-1.8B-Q4_K_M.gguf` | 混元翻译模型 | ~1.1 GB |
| `llama\llama-server.exe` + 同目录 `*.dll` | 本机推理服务 | ~0.8 GB |
| `paddlex\official_models\...` | PaddleOCR 权重 | ~0.13 GB |

`venv/` 与 `config.json` 用 `setup.ps1` 在本机生成。  
**Source code zip 不含模型。**

## Release 压缩包怎么解

1. 打开仓库 → **Releases**  
2. 下载 `runtime-*.zip`（以页面实际文件名为准）  
3. 解压到 `ScreenTranslator\` 根目录  

应出现：

```text
ScreenTranslator\runtime\models\*.gguf
ScreenTranslator\runtime\llama\llama-server.exe
ScreenTranslator\runtime\paddlex\...
```

勿解成 `runtime\runtime\`。

## 检查

```powershell
# 项目根
Get-Item .\runtime\models\*.gguf | Format-Table Name, Length
.\setup.ps1 -Check
```

模型文件应约 **1GB**。

可选：项目根 **`启动llama.bat`** 单独起 llama-server，见 **`LLAMA启动器说明.md`**。

## 官网手动下

| 资源 | 地址 |
|------|------|
| 模型 | https://huggingface.co/tencent/HY-MT1.5-1.8B-GGUF （推荐 `…Q4_K_M.gguf`） |
| llama | https://github.com/ggml-org/llama.cpp/releases（Windows CUDA 12/13 或 CPU） |

llama：exe 与 dll **平铺**到 `runtime\llama\`；CUDA 12/13 勿混用。
