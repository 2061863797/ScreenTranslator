# ScreenTranslator（翻译）

Windows 本地**离线**托盘工具：截屏翻译、划词翻译、窗口/区域实时翻译。

**License:** [Apache License 2.0](./LICENSE)（源码；模型等第三方见 [NOTICE](./NOTICE)）

**English:** [README.en.md](./README.en.md) · [Settings (EN)](./SETTINGS.en.md) · [runtime/README.en.md](./runtime/README.en.md)

**单独玩 llama-server 图形启动器：** 根目录双击 [`启动llama.bat`](./启动llama.bat)（说明见 [LLAMA启动器说明.md](./LLAMA启动器说明.md)）。日常翻译请用 `翻译.exe` / `run.py`。

| 能力 | 技术 |
|------|------|
| 界面 | Python + PySide6 |
| OCR | PaddleOCR（默认 PP-OCRv6） |
| 翻译 | 本机 `llama-server` + 混元 **HY-MT1.5** GGUF |

---

## 一、运行需要什么条件

### 1. 系统与硬件

| 条件 | 说明 |
|------|------|
| **Windows 10 / 11，64 位** | 当前仅支持此环境 |
| 磁盘空闲 | 建议 **≥ 5GB**（程序 + 模型 + 环境） |
| **NVIDIA 独显**（可选） | 有则更快；没有可用 CPU（较慢） |
| 内存 | 建议 **16GB+** |
| 管理员权限 | 一般不需要 |

### 2. Python（必须）

| 条件 | 说明 |
|------|------|
| **Python 3.11～3.13** | **推荐 3.12** |
| **不要用 3.14** | 飞桨（Paddle）在 Windows 上常装不上，OCR 无法用 |

```powershell
winget install Python.Python.3.12
py -0p
```

说明：Python 是解释器（给本软件和 OCR）；**CUDA 12/13** 只影响 GPU 版 llama，两回事。

### 3. 需要准备的文件

装好后目录应类似：

```text
ScreenTranslator/
  app/  run.py  setup.ps1  …
  runtime/
    models/HY-MT1.5-1.8B-Q4_K_M.gguf   ← 翻译模型 ~1.1GB
    llama/llama-server.exe + *.dll       ← 推理服务 ~0.8GB
    paddlex/official_models/...          ← OCR 权重 ~0.15GB
  venv/                                  ← 安装脚本生成
  config.json                            ← 安装脚本生成
```

| 部分 | 从哪来 |
|------|--------|
| 程序源码 | 本仓库 **Source / Code** 下载，或 `git clone` |
| **runtime**（模型等，约 2GB） | 仓库 **Releases** 里的 **`runtime-*.zip`**（推荐）；或安装脚本自动下；或见 [runtime/README.md](./runtime/README.md) |

### 4. 若「直接下载 zip」——还要满足什么

只下压缩包、不用 git 也可以，请分清两种 zip：

| 你下载的 | 里面有什么 | 还要做什么 |
|----------|------------|------------|
| **源码 zip**（Code → Download ZIP / Source code） | 只有程序与说明，**没有**模型 | 再下 **Release 的 `runtime-*.zip`**，解压到同一项目根；并安装 Python，运行 `setup.ps1` |
| **runtime-*.zip**（Releases 附件） | 模型 + llama + OCR | 解压到**已有源码的项目根**，不要单独当完整软件用 |
| 若作者提供「完整包」 | 以 Release 说明为准 | 仍建议本机跑一次 `setup.ps1` 生成 `venv`（Python 环境通常需本机安装） |

**直接下 zip 的最低条件：**

1. Windows 10/11 64 位  
2. 已安装 **Python 3.12**（或 3.11 / 3.13）  
3. 源码目录 + **`runtime` 已解压到位**（见上表）  
4. 能访问外网完成一次 `pip` / Paddle 安装（之后翻译可离线）  
5. 磁盘约 **5GB+** 空闲  

解压 runtime 后应存在：`项目根\runtime\models\*.gguf` 与 `项目根\runtime\llama\llama-server.exe`。  
勿解压成 `runtime\runtime\...`。

### 5. 网络

| 阶段 | 是否要网 |
|------|----------|
| 下载源码 / runtime 压缩包 | 要 |
| 首次 `setup.ps1` 装依赖 | 要 |
| **日常翻译** | **不要**（本机 `127.0.0.1`） |

---

## 二、安装与启动

路径均以**项目根目录**（含 `run.py` 的那一层）为准。

### 1. 获取程序

- GitHub：**Code → Download ZIP**，解压；或  
- `git clone <本仓库地址>`  

### 2. 获取 runtime（推荐 Release）

1. 打开本仓库 **Releases**  
2. 下载 **`runtime-*.zip`**（名称以页面为准）  
3. **解压到项目根**，与 `run.py` 同级  

备选：在项目根执行 `.\scripts\download_runtime.ps1` 或 `.\setup.ps1 -DownloadRuntime`；或按 [runtime/README.md](./runtime/README.md) 从官网手动下载。

### 3. 安装环境

```powershell
# 若不能运行脚本：
# Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

.\setup.ps1              # 有 NVIDIA 时
.\setup.ps1 -CpuOnly     # 无独显时
.\setup.ps1 -Check       # 检查是否齐全
```

脚本会：创建 `venv`、安装依赖、按显卡安装 Paddle、生成/合并 `config.json`。

### 4. 启动

```powershell
venv\Scripts\pythonw.exe run.py
```

可选：`.\build.ps1` 生成 `翻译.exe`（仍依赖同目录的 `venv` 与程序文件）。

### 5. 常见配置（可选）

编辑 `config.json` 或使用托盘 **设置**：

| 项 | 说明 |
|----|------|
| `n_gpu_layers` | 无独显 / 显存不足 → **`0`** |
| `threads` | CPU 线程数 |
| `ui_language` | `zh` / `en` 界面语言 |
| 热键 | 支持键盘与鼠标侧键（`mouse.x1` / `mouse.x2`） |
| `annotate_text_color` | 备注译文颜色，如 `#00F0FF` |

---

## 三、功能与默认热键

| 功能 | 默认热键 |
|------|----------|
| 截屏翻译 | Alt+Q |
| 划词翻译 | Alt+W |
| 窗口持续翻译 | Alt+E |
| 区域实时翻译 | Alt+R |
| 截图取字 | Alt+S |

托盘：历史、设置、打开日志、退出。  
持续翻译同时只能开一个；运行中可在控制条切换 **字幕 ↔ 备注**。

---

## 四、故障简表

| 现象 | 处理 |
|------|------|
| 没有模型 / 翻译起不来 | 确认已解压 **Release 的 runtime zip** 到项目根 |
| 只有源码没有 runtime | 源码包不含模型，请再下 Releases 附件 |
| `No matching distribution for paddlepaddle` | 换 **Python 3.12**，不要用 3.14 |
| llama / GPU 失败 | `n_gpu_layers: 0` 或换 CPU 版 llama |
| 热键无效 | 设置里重设；侧键可试 `mouse.x1` |
| 提示已在运行 | 托盘区已有实例 |

日志：`app.log`（托盘 → 打开日志）。

---

## 五、常用命令

```powershell
.\setup.ps1                      # 环境 + 配置
.\setup.ps1 -DownloadRuntime     # 补下模型/llama（无 Release zip 时）
.\setup.ps1 -CpuOnly             # 强制 CPU 版 Paddle
.\setup.ps1 -Check               # 检查
.\scripts\download_runtime.ps1   # 只下 runtime
.\build.ps1                      # 生成 翻译.exe
venv\Scripts\pythonw.exe run.py  # 启动
.\启动llama.bat                  # 仅图形启动 llama-server（可选）
```

版本号见 `app/__init__.py`。

### 文档索引

| 文件 | 内容 |
|------|------|
| [README.md](./README.md) | 中文总说明（本文件） |
| [README.en.md](./README.en.md) | English |
| [SETTINGS.en.md](./SETTINGS.en.md) | Settings keys (EN) |
| [LLAMA启动器说明.md](./LLAMA启动器说明.md) | llama 图形启动器 |
| [runtime/README.md](./runtime/README.md) | runtime 资源说明 |
| [LICENSE](./LICENSE) / [NOTICE](./NOTICE) | 协议与第三方 |

---

## 开源协议

- **本仓库源代码**：[Apache License 2.0](./LICENSE)  
- **第三方与模型**：见 [NOTICE](./NOTICE)。HY-MT 等权重以官方模型许可为准，**不等于**本仓库 Apache-2.0。

---

## 免责说明

本说明中的**下载、安装与配置教程由 AI 生成**，步骤、路径、版本号等**可能有误或过时**。  
请以实际发布文件、Release 附件名与本机环境为准，**自行核对后再操作**；因照做教程导致的问题需自行排查。
