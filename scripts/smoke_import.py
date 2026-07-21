# -*- coding: utf-8 -*-
"""由 setup.ps1 调用：冒烟导入。"""

from __future__ import annotations

import argparse
import sys
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.paths import resolve_path, runtime_status  # noqa: E402
from app import config  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-runtime-assets",
        action="store_true",
        help="仅用于源码 CI：检查导入和依赖，不加载 Release 运行资源",
    )
    args = parser.parse_args(argv)
    installed = {dist.metadata["Name"].lower().replace("_", "-") for dist in metadata.distributions()}
    banned = {
        "paddlepaddle", "paddlepaddle-gpu", "paddleocr", "paddlex",
        "pandas", "modelscope", "pyside6", "pyside6-addons",
    }
    found = sorted(name for name in installed if name in banned or name.startswith("nvidia-"))
    if found:
        raise RuntimeError(f"精简环境仍含禁用依赖：{', '.join(found)}")
    # 安装脚本必须检查真实运行依赖，而不是只导入轻量路径模块。
    import mss  # noqa: F401
    import cv2  # noqa: F401
    import onnxruntime as ort
    import pyclipper  # noqa: F401
    import pynput  # noqa: F401
    import requests  # noqa: F401
    import win32gui  # noqa: F401
    from PySide6 import QtCore  # noqa: F401
    import app.main  # noqa: F401

    providers = ort.get_available_providers()
    if "CPUExecutionProvider" not in providers:
        raise RuntimeError(f"ONNX Runtime 缺少 CPU Provider：{providers}")
    st = runtime_status()
    cfg = config.load()
    if not args.skip_runtime_assets:
        from app.ocr_engine import OcrEngine

        cpu_cfg = dict(cfg)
        cpu_cfg["ocr_provider"] = "cpu"
        cpu_ocr = OcrEngine(cpu_cfg)
        cpu_ocr.preload()
        if cpu_ocr.provider != "CPUExecutionProvider":
            raise RuntimeError(f"OCR CPU 回退不可用：{cpu_ocr.provider}")
    print("version ok")
    print("runtime", st)
    print("onnx providers", providers)
    print(
        "runtime assets skipped"
        if args.skip_runtime_assets
        else "ocr cpu fallback ok"
    )
    print("llama", resolve_path(cfg["llama_dir"]))
    print("model", resolve_path(cfg["model_path"]))
    print("ngl", cfg.get("n_gpu_layers"), "threads", cfg.get("threads"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
