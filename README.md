# ScreenTranslator（翻译）

Windows 离线托盘工具：截屏 / 划词 / 窗口·区域实时翻译。  
OCR = PaddleOCR · 翻译 = 本机 llama-server + HY-MT1.5。

协议：[Apache-2.0](./LICENSE)（源码）· 第三方见 [NOTICE](./NOTICE)  
English: [README.en.md](./README.en.md)

---

## 运行条件

| 需要 | 说明 |
|------|------|
| Windows 10/11 64 位 | |
| **Python 3.12**（3.11/3.13 也可） | **不要用 3.14**（Paddle 常装不上） |
| 磁盘约 5GB+ | |
| NVIDIA 显卡 | 可选；没有也能跑（更慢） |

---

## 安装

### 1. 下载源码

GitHub → **Code → Download ZIP** 并解压，或 `git clone` 本仓库。

### 2. 下载翻译模型与 llama（约 2GB）

| 资源 | 从哪来 |
|------|--------|
| OCR（`runtime\paddlex\`） | **已随源码**，不用另下 |
| 配置 `config.json` | 本机生成：`.\setup.ps1` 或复制 `config.example.json` |
| 翻译模型、llama-server | GitHub **Releases** 两个压缩包 |

Releases 下载并解压到源码根（与 `run.py` 同级），使目录成为：

```text
ScreenTranslator\
  run.py
  runtime\models\*.gguf          ← models 压缩包
  runtime\llama\llama-server.exe ← llama 压缩包
  runtime\paddlex\official_models\...  ← 源码已带
```

> 只下「Source code」**没有**翻译模型 / llama。没有 Release 时见 [runtime/README.md](./runtime/README.md)，或 `.\setup.ps1 -DownloadRuntime`。

### 3. 安装环境

在项目根 PowerShell：

```powershell
# 如无法运行脚本：Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\setup.ps1            # 有 NVIDIA
.\setup.ps1 -CpuOnly   # 无独显
.\setup.ps1 -Check
```

### 4. 启动

```powershell
venv\Scripts\pythonw.exe run.py
```

可选：`.\build.ps1` 生成 `翻译.exe`。

---

## 默认热键

| 功能 | 热键 |
|------|------|
| 截屏翻译 | Alt+Q |
| 划词翻译 | Alt+W |
| 窗口持续 | Alt+E |
| 区域实时 | Alt+R |
| 截图取字 | Alt+S |

托盘可改设置、看历史与日志。持续翻译同时只能开一个。

常见配置：`n_gpu_layers`（无独显改 `0`）、`ui_language`（`zh`/`en`）。详见设置页 / [SETTINGS.en.md](./SETTINGS.en.md)。

---

## 故障

| 现象 | 处理 |
|------|------|
| 没有翻译模型 / llama | 解压 Release 的 **models**、**llama** 两个包到项目根 |
| paddle 装不上 | 换 Python 3.12 |
| GPU 起不来 | `config.json` 里 `n_gpu_layers: 0` |
| 提示已在运行 | 托盘里已有实例 |

日志：`app.log`。

---

## 其它

- 模型等第三方许可见 [NOTICE](./NOTICE)  

**本安装说明可能由 AI 生成，请自行核对路径与 Release 文件名后再操作。**
