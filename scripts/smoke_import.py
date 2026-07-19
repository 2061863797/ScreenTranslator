# -*- coding: utf-8 -*-
"""由 setup.ps1 调用：冒烟导入。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.paths import resolve_path, runtime_status, setup_runtime_env  # noqa: E402
from app import config  # noqa: E402


def main() -> int:
    setup_runtime_env()
    # 安装脚本必须检查真实运行依赖，而不是只导入轻量路径模块。
    import mss  # noqa: F401
    import paddle
    import paddleocr  # noqa: F401
    import pynput  # noqa: F401
    import requests  # noqa: F401
    import win32gui  # noqa: F401
    from PySide6 import QtCore  # noqa: F401
    import app.main  # noqa: F401

    compiled_cudnn = str(paddle.version.cudnn() or "")
    runtime_cudnn = paddle.device.get_cudnn_version()
    if compiled_cudnn and runtime_cudnn:
        cm = tuple(int(x) for x in compiled_cudnn.split(".")[:2])
        rm = (int(runtime_cudnn) // 10000, (int(runtime_cudnn) % 10000) // 100)
        if cm != rm:
            raise RuntimeError(
                f"cuDNN 版本不匹配：Paddle 编译={compiled_cudnn}，运行时={rm[0]}.{rm[1]}"
            )
    st = runtime_status()
    cfg = config.load()
    print("version ok")
    print("runtime", st)
    print("llama", resolve_path(cfg["llama_dir"]))
    print("model", resolve_path(cfg["model_path"]))
    print("ngl", cfg.get("n_gpu_layers"), "threads", cfg.get("threads"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
