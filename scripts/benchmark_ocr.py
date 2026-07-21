# -*- coding: utf-8 -*-
"""对固定图片运行 OCR，输出可比较的 JSON 基准。"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import config  # noqa: E402
from app.ocr_engine import OcrEngine  # noqa: E402


def _load_image(path: Path) -> np.ndarray:
    import cv2

    data = np.fromfile(path, dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"无法读取图片：{path}")
    return image


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--provider", choices=("auto", "dml", "cpu"), default="auto")
    parser.add_argument(
        "--max-p95-ms",
        type=float,
        help="整体 P95 超过该毫秒数时返回失败，便于本机验收",
    )
    args = parser.parse_args()

    cfg = config.load()
    cfg["ocr_provider"] = args.provider
    engine = OcrEngine(cfg)
    started = time.perf_counter()
    engine.preload()
    load_ms = (time.perf_counter() - started) * 1000

    cases = []
    all_timings = []
    for raw_path in args.images:
        path = raw_path.resolve()
        image = _load_image(path)
        timings = []
        lines = []
        for _ in range(max(1, args.repeat)):
            started = time.perf_counter()
            lines = engine.recognize(image)
            timings.append((time.perf_counter() - started) * 1000)
        all_timings.extend(timings)
        cases.append({
            "image": path.name,
            "width": int(image.shape[1]),
            "height": int(image.shape[0]),
            "latency_ms": {
                "samples": [round(value, 2) for value in timings],
                "median": round(statistics.median(timings), 2),
                "p95": round(float(np.percentile(timings, 95)), 2),
                "max": round(max(timings), 2),
            },
            "lines": [
                {"text": line.text, "score": round(line.score, 6), "box": list(line.box)}
                for line in lines
            ],
        })

    report = {
        "engine": type(engine).__name__,
        "provider": engine.provider,
        "load_ms": round(load_ms, 2),
        "latency_ms": {
            "samples": len(all_timings),
            "median": round(statistics.median(all_timings), 2),
            "p95": round(float(np.percentile(all_timings, 95)), 2),
            "max": round(max(all_timings), 2),
        },
        "cases": cases,
    }
    encoded = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    if args.max_p95_ms is not None and report["latency_ms"]["p95"] > args.max_p95_ms:
        print(
            f"OCR P95 {report['latency_ms']['p95']:.2f} ms 超过限制 "
            f"{args.max_p95_ms:.2f} ms",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
