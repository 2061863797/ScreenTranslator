# runtime 资源目录

本目录的大文件（模型 / llama / OCR）通过 **Git LFS** 随仓库分发。

| 路径 | 内容 | 大约 |
|------|------|------|
| `models\HY-MT1.5-1.8B-Q4_K_M.gguf` | 翻译模型 | ~1.1GB |
| `llama\llama-server.exe` + `*.dll` | 推理服务（CUDA/CPU 依赖 DLL） | ~0.8GB |
| `paddlex\official_models\...` | OCR 权重 | ~0.13GB |

## 克隆后若文件是「指针」或很小

```powershell
git lfs install
git lfs pull
```

## 手动补齐 / 换版本

```powershell
# 项目根
.\scripts\download_runtime.ps1
# 或
.\setup.ps1 -DownloadRuntime
```

| 资源 | 官方 |
|------|------|
| 模型 | https://huggingface.co/tencent/HY-MT1.5-1.8B-GGUF |
| llama | https://github.com/ggml-org/llama.cpp/releases（CUDA 12/13 或 CPU） |

llama：exe 与 dll **平铺**在 `runtime\llama\`。CUDA 12 与 13 勿混用。

## 检查

```powershell
.\setup.ps1 -Check
```
