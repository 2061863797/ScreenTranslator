# -*- coding: utf-8 -*-
"""由 setup.ps1 调用：合并 example + 本机 GPU/线程，写出 config.json。"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 5:
        print(
            "用法: setup_config.py <root> <use_gpu:0|1> <threads> <n_gpu_layers>",
            file=sys.stderr,
        )
        return 2

    root = Path(sys.argv[1])
    use_gpu = sys.argv[2] == "1"
    threads = int(sys.argv[3])
    ngl = int(sys.argv[4])

    cfg_path = root / "config.json"
    example = root / "config.example.json"

    defaults: dict = {
        "llama_dir": "runtime/llama",
        "model_path": "runtime/models/HY-MT1.5-1.8B-Q4_K_M.gguf",
        "server_host": "127.0.0.1",
        "server_port": 8080,
        "n_gpu_layers": ngl,
        "threads": threads,
        "ctx_size": 2048,
        "batch_size": 512,
        "ubatch_size": 256,
        "parallel_slots": 1,
        "flash_attn": True,
        "mlock": False,
        "cache_type_k": "q8_0",
        "cache_type_v": "q8_0",
        "target_language": "简体中文",
        "max_tokens": 512,
        "history_enabled": True,
        "ocr_lang": None,
        "ocr_max_side": 1600,
        "ocr_score_min": 0.45,
        "hotkey_screenshot": "<alt>+q",
        "hotkey_word": "<alt>+w",
        "hotkey_window": "<alt>+e",
        "hotkey_silent_ocr": "<alt>+s",
        "hotkey_region_watch": "<alt>+r",
        "window_watch_interval_ms": 800,
        "window_watch_diff_threshold": 0.9,
        "window_watch_annotate": False,
        "window_annotate_skip_target_lang": False,
        "region_watch_interval_ms": 800,
        "region_watch_diff_threshold": 0.9,
        "region_watch_annotate": True,
        "region_annotate_skip_target_lang": False,
    }
    if example.is_file():
        try:
            raw = json.loads(example.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                defaults.update(raw)
        except (OSError, json.JSONDecodeError):
            pass

    cfg = dict(defaults)
    if cfg_path.is_file():
        try:
            raw = json.loads(cfg_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                cfg.update(raw)
        except (OSError, json.JSONDecodeError):
            pass

    # setup 职责：便携路径 + 本机算力参数
    cfg["llama_dir"] = "runtime/llama"
    # 保留设置页选择的模型；首次安装或无效配置仍使用默认模型。
    if not isinstance(cfg.get("model_path"), str) or not cfg["model_path"].strip():
        cfg["model_path"] = "runtime/models/HY-MT1.5-1.8B-Q4_K_M.gguf"
    cfg["n_gpu_layers"] = ngl
    cfg["threads"] = threads

    tmp = cfg_path.with_name(cfg_path.name + ".tmp")
    tmp.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(tmp, cfg_path)
    print(f"n_gpu_layers={ngl} threads={threads} use_gpu={use_gpu}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
