# ScreenTranslator（翻译）

Windows 本地**离线**托盘工具：截屏翻译、划词翻译、窗口/区域实时翻译。

| 能力 | 技术 |
|------|------|
| 界面 | Python + PySide6 |
| OCR | PaddleOCR（默认 PP-OCRv6） |
| 翻译 | 本机 `llama-server` + 混元 **HY-MT1.5** GGUF |

源码在本仓库；**大模型与 OCR 权重不进 Git**（体积约 2GB+），需本机准备或脚本下载。

---

## 一、运行需要什么条件

要跑起来，机器上必须同时满足下面几类条件。

### 1. 系统

| 条件 | 说明 |
|------|------|
| **Windows 10 / 11，64 位** | 当前只按这个环境开发与测试 |
| 管理员权限 | **一般不需要**；若杀软拦截 `llama-server` / 热键，再自行放行 |
| 磁盘空闲 | 建议 **≥ 5GB**（venv + 模型 + OCR + 日志） |

### 2. Python（必须）

| 条件 | 说明 |
|------|------|
| **Python 3.11～3.13** | **推荐 3.12**（本仓库按 3.12 验证） |
| **不要用 3.14** | 飞桨（Paddle）Windows 轮子通常还没有，**OCR 装不上** |

说明：

- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) 官方是 `requires-python >= 3.8`，列出到约 3.13，**不是「只能 3.12」**。
- 真正卡版本的是底层 **`paddlepaddle` / `paddlepaddle-gpu` 的 pip 包**，太新的 Python 会 `No matching distribution`。
- **Python 版本**和 **CUDA 12/13** 是两回事：前者给本程序和 OCR，后者只影响 GPU 版 llama 二进制。

安装示例：

```powershell
winget install Python.Python.3.12
py -0p   # 应能看到 3.12
```

### 3. 硬件（二选一即可）

| 配置 | 能否用 | 体验 |
|------|--------|------|
| **NVIDIA 独显** + 较新驱动 | 推荐 | OCR / 翻译都可走 GPU，更快 |
| **仅核显 / 无独显** | 可以 | 用 CPU 版 Paddle + `n_gpu_layers=0`，能跑但更慢 |
| 内存 | 建议 **16GB+** | 模型约 1GB，CPU 推理还要余量 |

### 4. 本程序依赖的三块「大文件」（必须有）

仓库**不包含**这些文件，装好后目录应类似：

```text
ScreenTranslator/
  runtime/
    models/HY-MT1.5-1.8B-Q4_K_M.gguf   ← 翻译模型 ~1.1GB
    llama/llama-server.exe + *.dll       ← 推理服务
    paddlex/official_models/...          ← OCR 权重（也可首次识别时自动下）
  venv/                                  ← Python 依赖（本机安装生成）
  config.json                            ← 本机配置（由脚本从模板生成）
```

| 资源 | 作用 | 官方来源 |
|------|------|----------|
| HY-MT GGUF | 翻译 | https://huggingface.co/tencent/HY-MT1.5-1.8B-GGUF |
| llama-server | 跑模型 | https://github.com/ggml-org/llama.cpp/releases |
| OCR 模型 | 认字 | 装好 Paddle 后首次 OCR 自动下载；或见 `runtime/README.md` |

### 5. 网络（仅安装阶段）

| 阶段 | 是否要网 |
|------|----------|
| `pip` 装依赖、下 Paddle | 要 |
| 下载 GGUF / llama 压缩包 | 要（或 U 盘拷贝） |
| **日常翻译** | **不要**（本机 `127.0.0.1`） |

---

## 二、新电脑 / 别人机器怎么自己配

下面按「从 GitHub 克隆到能开托盘」写。路径以项目根目录为准。

### 步骤 A：拿到源码

```powershell
git clone <本仓库地址> ScreenTranslator
cd ScreenTranslator
```

或下载 Source zip 解压。

### 步骤 B：一键安装（推荐）

在项目根打开 PowerShell：

```powershell
# 若提示无法运行脚本：
# Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# 有 NVIDIA：建 venv、装依赖、写 config、尝试下载模型+llama
.\setup.ps1 -DownloadRuntime

# 没有独显 / GPU 装失败：
.\setup.ps1 -CpuOnly -DownloadRuntime
```

脚本会：

1. 寻找 Python 3.12（没有则试 3.13、3.11）  
2. 创建 `venv\` 并安装 `requirements.txt`  
3. 按有无 NVIDIA 安装 **paddlepaddle-gpu** 或 **paddlepaddle（CPU）**  
4. 从 `config.example.json` 生成/合并 `config.json`（路径指向 `runtime/`，线程数按 CPU）  
5. 可选：下载模型与 llama 到 `runtime/`  
6. OCR 可在首次识别时自动拉到 `runtime/paddlex`

检查是否齐：

```powershell
.\setup.ps1 -Check
```

### 步骤 C：外网下不动资源时（手动）

1. 从 HuggingFace 下载 **`HY-MT1.5-1.8B-Q4_K_M.gguf`**  
   → 放到 `runtime\models\`
2. 从 llama.cpp Releases 下载 Windows 包：  
   - 有 NVIDIA：选 **CUDA 12 或 13** 的 zip（成套 DLL，不要混 12+13）  
   - 无独显：选 **CPU** zip  
   → 把 `llama-server.exe` 和全部 `.dll` **平铺**进 `runtime\llama\`
3. 再执行：

```powershell
.\setup.ps1          # 或 .\setup.ps1 -CpuOnly
```

4. 启动后做一次截屏识别，OCR 权重会进 `runtime\paddlex`（需能访问模型源）

更细的放置说明见 **`runtime/README.md`**。  
也可只下资源：`.\scripts\download_runtime.ps1`。

### 步骤 D：启动

```powershell
venv\Scripts\pythonw.exe run.py
```

可选：生成托盘启动器（仍依赖同目录 `venv` + `app`）：

```powershell
.\build.ps1
# 双击 翻译.exe
```

### 步骤 E：换机后常见要改的配置

编辑 `config.json`（设置页也会改一部分）：

| 项 | 何时改 |
|----|--------|
| `n_gpu_layers` | 无独显 / 显存不够 → 设为 **`0`** |
| `threads` | CPU 核心数，setup 会估一个 |
| `model_path` / `llama_dir` | 默认 `runtime/...` 一般不用改 |
| `server_port` | 8080 被占用时改掉 |
| 热键 | 设置 → 热键；支持 **鼠标侧键**（`mouse.x1` / `mouse.x2`） |

**不要**把别人的整个 `venv\` 拷过来当通用方案——路径和二进制常不通用；在新机器重新 `.\setup.ps1` 更稳。

---

## 三、本机已配好时

若已有 `venv` + `runtime` + `config.json`：

```powershell
venv\Scripts\pythonw.exe run.py
```

---

## 四、功能与默认热键

| 功能 | 默认热键 |
|------|----------|
| 截屏翻译 | Alt+Q |
| 划词翻译 | Alt+W |
| 窗口持续翻译 | Alt+E |
| 区域实时翻译 | Alt+R |
| 截图取字 | Alt+S |

托盘：历史、设置、打开日志、退出。  
持续翻译**同时只能开一个**；运行中可在控制条切换 **字幕 ↔ 备注**。

---

## 五、仓库里有什么 / 没有什么

### 会进 Git 的（源码）

- `app/`、`run.py`、`launcher.py`、`scripts/`
- `setup.ps1`、`build.ps1`、`requirements.txt`
- `config.example.json`、`README.md`、`runtime/README.md`、`icon.ico` 等

### 不要提交（已在 `.gitignore`）

| 路径 | 原因 |
|------|------|
| `venv/` | 本机环境 |
| `config.json` | 本机配置 |
| `runtime/models/`、`runtime/llama/`、`runtime/paddlex/` | 大文件 |
| `*.db`、`app.log` | 用户数据 / 日志 |
| `翻译.exe`、`build/`、`dist/` | 可本地生成 |
| `__pycache__/`、`.codegraph/` | 缓存 |

克隆后用 **步骤 B/C** 在本机生成被忽略的部分。

---

## 六、故障简表

| 现象 | 处理 |
|------|------|
| `No matching distribution for paddlepaddle` | 换 Python **3.12**，不要 3.14 |
| llama 起不来 / 占 GPU 失败 | `n_gpu_layers: 0` 或换 CPU 版 llama 包 |
| OCR 首次很慢 / 下载失败 | 检查网络；或手动准备 `runtime/paddlex` |
| 热键无效 | 设置里重设；侧键写 `mouse.x1`；看是否被其它软件占用 |
| 提示已在运行 | 托盘区已有实例，勿重复开 |

日志：`app.log`（托盘 → 打开日志）。

---

## 七、常用命令

```powershell
.\setup.ps1                      # 环境 + 配置
.\setup.ps1 -DownloadRuntime     # 再加下载模型/llama
.\setup.ps1 -CpuOnly             # 强制 CPU 版 Paddle
.\setup.ps1 -Check               # 检查
.\scripts\download_runtime.ps1   # 只下 runtime
.\build.ps1                      # 生成 翻译.exe
venv\Scripts\pythonw.exe run.py  # 启动
```

版本号见 `app/__init__.py`。
