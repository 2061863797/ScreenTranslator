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
