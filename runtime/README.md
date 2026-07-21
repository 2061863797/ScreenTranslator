# 本地屏译 runtime 资源说明

`runtime` 分为三部分：

| 目录 | 来源 | 内容 |
|------|------|------|
| `ocr\` | Releases 的 **ocr** 附件 | PP-OCRv6 ONNX 模型、字符表和校验清单 |
| `models\` | Releases 的 **models** 附件 | HY-MT GGUF 翻译模型 |
| `llama\` | Releases 的 **llama** 附件 | `llama-server.exe` 及依赖 DLL |

`config.json` 和 `venv` 由每台电脑在本机生成，不属于 runtime 发布附件。

## 默认 Release 方案

Releases 提供 **ocr**、**models**、**llama** 三个压缩包。

其中 **llama** 附件同时包含 CPU 与 NVIDIA CUDA 后端。所有电脑使用同一个附件；有兼容显卡时无需另装 CUDA Toolkit。

三个压缩包内第一层应分别为 `ocr\`、`models\`、`llama\`。把它们都解压到项目的 `runtime\` 目录并允许合并或替换同名文件后，应得到：

```text
runtime\models\HY-MT1.5-1.8B-Q4_K_M.gguf
runtime\llama\llama-server.exe
runtime\llama\*.dll
runtime\ocr\manifest.json
runtime\ocr\det.onnx
runtime\ocr\rec.onnx
runtime\ocr\characters.txt
```

检查资源：

```powershell
.\setup.ps1 -Check
```

## 放置多个翻译模型

`runtime\models\` 可以同时放置多个 `.gguf` 文件。额外模型需要自行下载，并直接放在该目录顶层；随后在“托盘 → 设置 → 高级 → 模型与生成”中选择，保存并重启软件后生效。

设置列表只识别文件头有效的 GGUF。自定义模型仍需兼容当前 `llama.cpp`，并自行确认翻译能力、提示格式、许可和硬件需求。

## CPU 与翻译设备

没有 NVIDIA 显卡时也解压同一个 **llama** 附件。软件的“自动”翻译设备会使用 CPU；也可以在“设置 → 高级 → 翻译设备”中选择 CPU，重启后生效。

完整安装步骤见项目根目录的 [README.md](../README.md)。
