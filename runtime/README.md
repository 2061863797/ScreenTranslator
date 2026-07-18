# runtime 资源目录

模型 / llama / OCR 体积约 **2GB**。获取方式（任选）：

| 优先级 | 方式 |
|--------|------|
| **推荐** | 本仓库 **GitHub Releases** 里下载 **`runtime-*.zip`**，解压到**项目根目录**（与 `run.py` 同级），得到本 `runtime\` |
| 备选 | Git LFS：`git lfs pull` |
| 备选 | 项目根：`.\scripts\download_runtime.ps1` 或 `.\setup.ps1 -DownloadRuntime` |
| 备选 | 下方官网手动下载 |

## 目录说明

| 路径 | 内容 | 大约体积 |
|------|------|----------|
| `models\HY-MT1.5-1.8B-Q4_K_M.gguf` | 混元翻译模型 | ~1.1 GB |
| `llama\llama-server.exe` + 同目录 `*.dll` | 本机推理服务 | ~0.8 GB |
| `paddlex\official_models\...` | PaddleOCR 权重 | ~0.13 GB |

`venv/` 与 `config.json` 仍须在本机用 `setup.ps1` 生成，**不要**指望 Source code zip 里带模型。

## Release 压缩包怎么解

1. 打开仓库页面 → **Releases**  
2. 下载附件（如 `runtime-v1.1.0.zip`，以页面实际文件名为准）  
3. 解压到 `ScreenTranslator\` 根目录  

解压后应存在：

```text
ScreenTranslator\runtime\models\*.gguf
ScreenTranslator\runtime\llama\llama-server.exe
ScreenTranslator\runtime\paddlex\...
```

若 zip 内已经带一层 `runtime\`，不要解成 `runtime\runtime\`。

## 检查是否齐

```powershell
# 项目根
Get-Item .\runtime\models\*.gguf | Format-Table Name, Length
.\setup.ps1 -Check
```

模型真文件约 1GB；若只有一百多字节，说明是 LFS 指针，请改用 **Release zip**。

图形启动 llama-server（可选）：项目根 **`启动llama.bat`**，见 **`LLAMA启动器说明.md`**。

## 手动从官网下（无 Release 时）

| 资源 | 地址 |
|------|------|
| 模型 | https://huggingface.co/tencent/HY-MT1.5-1.8B-GGUF （推荐 `…Q4_K_M.gguf`） |
| llama | https://github.com/ggml-org/llama.cpp/releases（Windows：CUDA 12/13 或 CPU） |

- llama：exe 与 dll **平铺**到 `runtime\llama\`  
- CUDA 12 与 13 **不要混用**  
