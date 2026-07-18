# runtime 资源目录

本目录的大文件与源码**一起推送**到 GitHub，使用 **[Git LFS](https://git-lfs.com)**（规则在仓库根目录 `.gitattributes`）。

## 目录说明

| 路径 | 内容 | 大约体积 | 是否 LFS |
|------|------|----------|----------|
| `models\HY-MT1.5-1.8B-Q4_K_M.gguf` | 混元翻译模型 | ~1.1 GB | 是 |
| `llama\llama-server.exe` + 同目录 `*.dll` | 本机推理服务 | ~0.8 GB | 是 |
| `paddlex\official_models\...` | PaddleOCR 权重 | ~0.13 GB | 是 |

**合计约 2 GB。** 克隆仓库后应直接可用；`venv/` 与 `config.json` 仍需在本机用 `setup.ps1` 生成。

## 克隆后请确认

```powershell
# 在仓库根目录
git lfs install
git lfs pull

# 真文件应约 1GB；若只有一百多字节，说明还是指针，LFS 未拉下
Get-Item .\models\*.gguf | Format-Table Name, Length
```

未装 Git LFS 时，GitHub 网页下的 Source zip **通常只有指针、没有模型本体**。

## LFS 拉失败 / 想自己换版本

在项目根执行：

```powershell
.\scripts\download_runtime.ps1
# 或
.\setup.ps1 -DownloadRuntime
```

| 资源 | 官方下载 |
|------|----------|
| 模型 | https://huggingface.co/tencent/HY-MT1.5-1.8B-GGUF （推荐 `…Q4_K_M.gguf`） |
| llama | https://github.com/ggml-org/llama.cpp/releases（Windows：CUDA 12/13 或 CPU） |

- llama：把 `llama-server.exe` 与全部 `.dll` **平铺**到本目录下的 `llama\`  
- CUDA 12 与 13 的 DLL **不要混用**  
- 与 Python 版本无关（Python 给 OCR/界面，CUDA 给 GPU 版 llama）

## 检查是否齐

```powershell
# 项目根
.\setup.ps1 -Check
```
