# -*- coding: utf-8 -*-
"""启动入口：python run.py

先设置便携 runtime 环境变量，再进入主程序。
"""

from app.paths import setup_runtime_env

setup_runtime_env()

from app.main import main

if __name__ == "__main__":
    raise SystemExit(main())
