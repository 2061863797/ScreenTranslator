# runtime 资源目录（不进 Git）

本目录放**运行所需大文件**。克隆仓库后需自行下载或运行项目根目录：

```powershell
.\setup.ps1 -DownloadRuntime
# 或
.\scripts\download_runtime.ps1
```

## 需要齐的三样

| 路径 | 内容 | 从哪来 |
|------|------|--------|
| `models\HY-MT1.5-1.8B-Q4_K_M.gguf` | 翻译模型 ~1.1GB | https://huggingface.co/tencent/HY-MT1.5-1.8B-GGUF |
| `llama\llama-server.exe` + 同目录全部 `.dll` | 推理服务 | https://github.com/ggml-org/llama.cpp/releases |
| `paddlex\official_models\...` | OCR 权重 | 装好 Paddle 后**首次识别**自动下；或 `download_runtime.ps1 -WarmOcr` |

## llama 包怎么选

| 电脑 | Releases 里选 |
|------|----------------|
| 有 NVIDIA | Windows **CUDA 12** 或 **CUDA 13** zip（成套，勿混版本） |
| 无独显 | **CPU** x64 zip |

解压后把 exe 与 dll **平铺**到 `runtime\llama\`（不要只放一层子目录找不到 exe）。

## 和 Python 的关系

- **Python 3.12** → 给本软件 + PaddleOCR  
- **CUDA 12/13** → 只影响 GPU 版 llama 二进制  
两回事，不要混着改。

## 检查

在项目根：

```powershell
.\setup.ps1 -Check
```
