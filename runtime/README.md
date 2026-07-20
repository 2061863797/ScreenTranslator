# runtime 资源说明

`runtime` 分为三部分：

| 目录 | 来源 | 内容 |
|------|------|------|
| `paddlex\official_models\` | Releases 的完整 **runtime** 附件 | PaddleOCR 检测和识别模型 |
| `models\` | Releases 的完整 **runtime** 附件 | HY-MT GGUF 翻译模型 |
| `llama\` | Releases 的完整 **runtime** 附件 | `llama-server.exe` 及依赖 DLL |

`config.json` 和 `venv` 由每台电脑在本机生成，不属于 runtime 发布附件。

## 默认 Release 方案

Releases 提供一个完整的 **runtime** 压缩包，其中同时包含 PaddleX OCR 模型、HY-MT 翻译模型和 llama-server。

完整附件中的 `runtime\llama` 是 NVIDIA CUDA 13 版本，适合 NVIDIA 显卡和可正常工作的较新驱动。附件已包含 CUDA 运行库 DLL，无需另装 CUDA Toolkit。

压缩包内第一层应为 `runtime\`。把它解压到项目根目录并允许合并或替换同名文件后，应得到：

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

## CPU 或缺少完整 runtime 附件

没有 NVIDIA 显卡但已经解压完整 **runtime** 附件时，保留其中的模型和 OCR，并把 CUDA llama 替换为 CPU 版：

```powershell
.\scripts\download_runtime.ps1 -CpuOnly -SkipModel -Force
.\setup.ps1 -CpuOnly
```

没有完整 **runtime** 附件时，也可以尝试由脚本下载所需资源：

```powershell
.\setup.ps1 -CpuOnly -DownloadRuntime
```

有 NVIDIA 但缺少完整 **runtime** 附件时：

```powershell
.\setup.ps1 -DownloadRuntime
```

自动下载来源：

| 资源 | 官方地址 |
|------|----------|
| HY-MT GGUF | https://huggingface.co/tencent/HY-MT1.5-1.8B-GGUF |
| llama.cpp | https://github.com/ggml-org/llama.cpp/releases |

完整安装步骤见项目根目录的 [README.md](../README.md)。
