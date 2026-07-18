# -*- coding: utf-8 -*-
"""启动器：双击"翻译.exe"后用旁边的 venv 无窗口启动主程序。

打包后 exe 与 venv/、app/、run.py 同目录，整个文件夹即软件本体。
"""

import subprocess
import sys
from pathlib import Path


def main():
    base = Path(sys.executable).resolve().parent  # exe 所在目录
    pythonw = base / "venv" / "Scripts" / "pythonw.exe"
    run_py = base / "run.py"
    if not pythonw.exists() or not run_py.exists():
        import ctypes

        ctypes.windll.user32.MessageBoxW(
            0,
            f"未找到运行环境：\n{pythonw}\n{run_py}\n"
            "请保持 翻译.exe 与 venv、app、run.py 在同一目录。",
            "翻译",
            0x10,
        )
        return 1
    subprocess.Popen(
        [str(pythonw), str(run_py)],
        cwd=str(base),
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
