# -*- coding: utf-8 -*-
"""PaddleOCR 封装：输入图像，输出文字 + 坐标框。

PP-OCRv6（及兼容流水线）支持中英日韩等多文种混排，无需指定源语言，
与 HY-MT 的「源语言自动识别」策略一致。
"""

import threading
from dataclasses import dataclass

import numpy as np

from .applog import get_logger

_log = get_logger("ocr")


@dataclass
class OcrLine:
    text: str
    score: float
    box: tuple[int, int, int, int]  # 轴对齐外接框 (x1, y1, x2, y2)


class OcrEngine:
    """OCR 引擎。支持启动时 preload，避免首次截屏/划词才加载 Paddle 模型。"""

    def __init__(self, cfg: dict):
        self._cfg = cfg
        self._ocr = None
        self._lock = threading.Lock()
        # Paddle 推理对象不在多个 Qt/Python 工作线程之间并发使用。
        self._predict_lock = threading.Lock()

    def preload(self) -> None:
        """后台预热：导入 PaddleOCR 并初始化模型。"""
        self._ensure_loaded()

    def _ensure_loaded(self):
        # 双检锁：已就绪则快速返回
        if self._ocr is not None:
            return
        with self._lock:
            if self._ocr is not None:
                return
            # 必须在 import paddle 之前把缓存指到项目 runtime/paddlex
            from .paths import RUNTIME_PADDLEX, setup_runtime_env

            setup_runtime_env()
            from paddleocr import PaddleOCR

            kwargs = {
                # 屏幕截图都是摆正的，关掉方向分类和矫正以降低延迟
                "use_doc_orientation_classify": False,
                "use_doc_unwarping": False,
                "use_textline_orientation": False,
            }
            if self._cfg.get("ocr_lang"):
                kwargs["lang"] = self._cfg["ocr_lang"]
            _log.info(
                "初始化 PaddleOCR kwargs=%s paddlex=%s",
                kwargs,
                RUNTIME_PADDLEX,
            )
            self._ocr = PaddleOCR(**kwargs)
            _log.info("PaddleOCR 初始化完成")

    def _prepare_image(self, image: np.ndarray) -> tuple[np.ndarray, float]:
        """过大截屏缩小后再识别；返回 (送检图, 坐标还原倍率)。"""
        max_side = int(self._cfg.get("ocr_max_side") or 0)
        if max_side <= 0 or image is None or image.size == 0:
            return image, 1.0
        h, w = image.shape[:2]
        m = max(h, w)
        if m <= max_side:
            return image, 1.0
        scale = max_side / float(m)
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        try:
            import cv2

            # INTER_AREA 适合缩小，文字边缘更干净
            out = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_AREA)
        except Exception:
            # 无 cv2 时用最近邻简易缩放（少见）
            ys = (np.linspace(0, h - 1, nh)).astype(np.int32)
            xs = (np.linspace(0, w - 1, nw)).astype(np.int32)
            out = image[ys][:, xs]
        inv = 1.0 / scale
        _log.debug("OCR 缩放 %dx%d → %dx%d scale=%.3f", w, h, nw, nh, scale)
        return out, inv

    def recognize(self, image: np.ndarray) -> list[OcrLine]:
        """image：BGR 或 RGB 的 HxWx3 数组。返回按阅读顺序排列的文本行。

        坐标始终映射回原图像素，便于备注叠层对齐。
        """
        self._ensure_loaded()
        work, inv = self._prepare_image(image)
        score_min = float(self._cfg.get("ocr_score_min") or 0.0)
        with self._predict_lock:
            results = self._ocr.predict(work)
        lines: list[OcrLine] = []
        for res in results:
            texts = res.get("rec_texts", [])
            scores = res.get("rec_scores", [])
            polys = res.get("rec_polys", res.get("dt_polys", []))
            for text, score, poly in zip(texts, scores, polys):
                if not text.strip():
                    continue
                sc = float(score)
                if score_min > 0 and sc < score_min:
                    continue
                pts = np.asarray(poly, dtype=np.float64)
                if inv != 1.0:
                    pts = pts * inv
                x1, y1 = pts.min(axis=0).astype(int)
                x2, y2 = pts.max(axis=0).astype(int)
                lines.append(OcrLine(
                    text=text, score=sc,
                    box=(int(x1), int(y1), int(x2), int(y2)),
                ))
        return lines

    @staticmethod
    def lines_to_text(lines: list[OcrLine]) -> str:
        return "\n".join(ln.text for ln in lines)
