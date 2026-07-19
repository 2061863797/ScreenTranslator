# runtime 资源说明

`runtime` 分为三部分：

| 目录 | 来源 | 内容 |
|------|------|------|
| `paddlex\official_models\` | 源码包自带 | PaddleOCR 检测和识别模型 |
| `models\` | Releases 的 **models** 附件 | HY-MT GGUF 翻译模型 |
| `llama\` | Releases 的 **llama** 附件 | `llama-server.exe` 及依赖 DLL |

`config.json` 和 `venv` 由每台电脑在本机生成，不属于 runtime 发布附件。

## 默认 Release 方案

Releases 只提供 **models**、**llama** 两个附件；PaddleX OCR 模型已经包含在源码包中，不需要重复下载。

当前 `llama` 附件是 NVIDIA CUDA 13 版本，适合 NVIDIA 显卡和可正常工作的较新驱动。附件已包含 CUDA 运行库 DLL，无需另装 CUDA Toolkit。

把 **models**、**llama** 两个附件都解压到当前 `runtime\` 目录后，应得到：

```text
runtime\models\HY-MT1.5-1.8B-Q4_K_M.gguf
runtime\llama\llama-server.exe
runtime\llama\*.dll
runtime\paddlex\official_models\PP-OCRv6_medium_det\
runtime\paddlex\official_models\PP-OCRv6_medium_rec\
```

检查资源：

```powershell
.\setup.ps1 -Check
```

## 放置多个翻译模型

`runtime\models\` 可以同时放置多个 `.gguf` 文件。额外模型需要自行下载，并直接放在该目录顶层；随后在“托盘 → 设置 → 高级 → 模型与生成”中选择，保存并重启软件后生效。

设置列表只识别文件头有效的 GGUF。自定义模型仍需兼容当前 `llama.cpp`，并自行确认翻译能力、提示格式、许可和硬件需求。

## CPU 或缺少 Release 附件

没有 NVIDIA 显卡时，使用 CPU 版 llama：

```powershell
.\setup.ps1 -CpuOnly -DownloadRuntime
```

已经解压过默认 CUDA llama 时，可用 CPU 包替换：

```powershell
.\scripts\download_runtime.ps1 -CpuOnly -SkipModel -Force
.\setup.ps1 -CpuOnly
```

有 NVIDIA 但缺少 Release 附件时：

```powershell
.\setup.ps1 -DownloadRuntime
```

自动下载来源：

| 资源 | 官方地址 |
|------|----------|
| HY-MT GGUF | https://huggingface.co/tencent/HY-MT1.5-1.8B-GGUF |
| llama.cpp | https://github.com/ggml-org/llama.cpp/releases |

完整安装步骤见项目根目录的 [README.md](../README.md)。
