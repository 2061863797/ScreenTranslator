# -*- coding: utf-8 -*-
"""后台任务线程：OCR 与翻译都不能跑在 UI 线程里。"""

import time
import traceback

import numpy as np
from PySide6.QtCore import QThread, Signal

from .applog import get_logger
from .ocr_engine import OcrEngine
from .translator import Translator

_log = get_logger("worker")


class OcrTranslateWorker(QThread):
    """一次性任务：OCR（可选）→ 翻译（可选），用于截屏/划词/静默取字。

    finished_ok(source_text, translation)
    """

    finished_ok = Signal(str, str)
    failed = Signal(str)

    def __init__(self, ocr: OcrEngine, translator: Translator, cfg: dict,
                 image: np.ndarray | None = None,
                 text: str | None = None,
                 do_translate: bool = True,
                 target_language: str | None = None):
        super().__init__()
        self._ocr = ocr
        self._translator = translator
        self._image = image
        self._text = text
        self._do_translate = do_translate
        self._target = target_language or cfg["target_language"]

    def run(self):
        t0 = time.time()
        try:
            if self._text is not None:
                source = self._text.strip()
                _log.info("worker 文本路径 chars=%d translate=%s", len(source), self._do_translate)
            else:
                lines = self._ocr.recognize(self._image)
                source = OcrEngine.lines_to_text(lines)
                _log.info(
                    "worker OCR 行数=%d chars=%d translate=%s",
                    len(lines), len(source), self._do_translate,
                )

            if not source:
                _log.warning("worker 未识别到文字")
                self.failed.emit("未识别到文字")
                return

            translation = ""
            if self._do_translate:
                translation = self._translator.translate(source, self._target)

            _log.info("worker 完成 %.2fs", time.time() - t0)
            self.finished_ok.emit(source, translation)
        except Exception:
            _log.exception("worker 失败")
            self.failed.emit(traceback.format_exc(limit=3))
