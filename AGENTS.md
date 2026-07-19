# ScreenTranslator — 项目规则

全局行为见 **`~/.grok/AGENTS.md`**。本文件只补充本仓库约定。

## 项目画像

- **定位**：Windows 本地离线截屏 / 划词 / 窗口·区域实时翻译托盘工具。
- **协议**：源码 **Apache-2.0**（`LICENSE`）；第三方/模型见 `NOTICE`。
- **栈**：Python 3.11～3.13（推荐 3.12）+ PySide6；OCR = PaddleOCR；翻译 = 本机 `llama-server` + HY-MT1.5。
- **入口**：`run.py` → `app.main.main`；启动器 `launcher.py` / `翻译.exe`（`build.ps1`）。
- **路径**：`app/paths.py`；`runtime/paddlex` 随源码；`models` / `llama` 用 **Release 两个压缩包**（不传整包 runtime，不传 config.json）。
- **配置**：本机 `config.json`（gitignore）+ `config.example.json`；缺省见 `DEFAULTS`。
- **安装**：`setup.ps1` / `scripts/download_runtime.ps1`。用户说明以 **`README.md`** / **`README.en.md`** 为准。
- **CodeGraph**：`projectPath` = 本仓库根；排除 `venv/`、大模型目录、`*.db`。

## 易混点

- Python 版本 ≠ CUDA 12/13；Paddle 在 **3.14** 上通常装不上。
- 用户向文档避免「进不进 Git」表述；写「源码包 / Release 附件 / 本机生成」即可。

## 改动约定

- 调度在 `app/main.py`；OCR / 翻译 / 捕获 / 监视 / 热键 / 存储分文件；UI 在 `app/ui/`。
- UI 更新经信号槽回主线程；翻译 HTTP 仅本机 llama。
- 新配置写入 `DEFAULTS` 与 `config.example.json`，并更新 README。
- **先问再做**：删数据、改模型路径、杀进程、覆盖 exe、**git push / 强推**。

## 验证

1. `venv\Scripts\python.exe` 相关 import 冒烟。  
2. 无测试时给手测步骤。  
3. 涉及 OCR/llama 时说明本机是否已就绪。
