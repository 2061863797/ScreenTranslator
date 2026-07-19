# -*- coding: utf-8 -*-
"""持续翻译监视线程：定时捕获目标（窗口或屏幕区域）→ OCR → 差异检测 → 翻译。"""

import hashlib
import threading
import time
import traceback
from difflib import SequenceMatcher

import numpy as np
from PySide6.QtCore import QThread, Signal

from . import capture
from .applog import get_logger
from .ocr_engine import OcrEngine
from .textlang import is_already_target_language
from .translator import Translator

# 备注缓存哨兵：已是目标语，跳过翻译且不叠标签
_SKIP_TARGET = "\x00SKIP_TARGET"

_log = get_logger("watch")


def _is_invalid_window_handle_error(exc: BaseException) -> bool:
    """目标窗在检查与截图之间关闭时，pywin32 返回错误 1400。"""
    code = getattr(exc, "winerror", None)
    if code is None and exc.args:
        code = exc.args[0]
    return code == 1400


def _image_fingerprint(img: np.ndarray) -> bytes:
    """轻量画面指纹：降采样 + 粗量化，画面几乎不变时跳过 OCR。"""
    if img is None or img.size == 0:
        return b""
    # 取灰度近似并缩到 32x32
    small = img[:: max(1, img.shape[0] // 32), :: max(1, img.shape[1] // 32)]
    if small.ndim == 3:
        gray = small.mean(axis=2).astype(np.uint8)
    else:
        gray = small.astype(np.uint8)
    # 再量化，忽略轻微抗锯齿/光标闪烁
    quant = (gray // 16).astype(np.uint8)
    return hashlib.blake2b(quant.tobytes(), digest_size=16).digest()


class WindowWatcher(QThread):
    """文字有实质变化才重新翻译，避免每帧都压 OCR/LLM。

    监视源二选一：hwnd（窗口，含被遮挡部分）或 region（屏幕区域 x,y,w,h）。

    subtitle_ready(translation)      译文更新（字幕条模式）
    annotations_ready(items)         逐行 [(box, 译文), ...]（备注模式）
    history_ready(source, translation, mode)  有实质新译文时写入历史
    window_moved(x, y, w, h)         目标位置变化
    stopped(reason)                  监视结束
    """

    subtitle_ready = Signal(str)
    annotations_ready = Signal(list)
    history_ready = Signal(str, str, str)
    window_moved = Signal(int, int, int, int)
    stopped = Signal(str)

    def __init__(self, ocr: OcrEngine, translator: Translator, cfg: dict,
                 hwnd: int | None = None,
                 region: tuple[int, int, int, int] | None = None,
                 display_mode: str = "subtitle",
                 profile: str = "window"):
        """profile: \"window\" | \"region\"，决定读哪套间隔/阈值配置。"""
        super().__init__()
        assert (hwnd is None) != (region is None), "hwnd 与 region 必须二选一"
        assert profile in ("window", "region"), "profile 须为 window 或 region"
        self._hwnd = hwnd
        self._region = region
        self._region_lock = threading.Lock()
        self._ocr = ocr
        self._translator = translator
        self._cfg = cfg
        self._display_mode = display_mode
        self._profile = profile
        self._running = True
        self._last_text = ""
        self._last_rect = None
        self._last_fp: bytes | None = None
        # 备注模式：原文→译文，画面只变几行时只重译变化行
        self._line_tr_cache: dict[str, str] = {}
        self._last_skip_target: bool | None = None

    def set_display_mode(self, mode: str):
        if mode not in ("subtitle", "annotate"):
            return
        self._display_mode = mode
        self._last_text = ""
        self._last_fp = None
        self._line_tr_cache.clear()
        self._last_skip_target = None

    def set_region(self, region: tuple[int, int, int, int] | None):
        """区域监视时拖动选区后更新（线程安全）。"""
        with self._region_lock:
            self._region = region
        self._last_fp = None
        self._last_text = ""
        # 选区变了，旧行框可能失效，但同文案译文仍可复用

    def stop(self):
        self._running = False

    def _grab(self):
        if self._region is not None:
            with self._region_lock:
                region = self._region
            if region is None:
                return None, None
            x, y, w, h = region
            if w <= 0 or h <= 0:
                return None, None
            return region, capture.grab_region(x, y, w, h)
        rect = capture.get_window_rect(self._hwnd)
        return rect, capture.grab_window(self._hwnd)

    def run(self):
        _log.info(
            "监视线程启动 profile=%s mode=%s hwnd=%s region=%s",
            self._profile, self._display_mode, self._hwnd, self._region,
        )
        try:
            while self._running:
                # 窗口 / 区域各自一套间隔与文本变化阈值
                p = self._profile
                interval = self._cfg[f"{p}_watch_interval_ms"] / 1000.0
                threshold = float(self._cfg[f"{p}_watch_diff_threshold"])
                target = self._cfg["target_language"]
                # 备注「跳过目标语」开关变化：立刻清空缓存并强制重跑一帧
                if self._display_mode == "annotate":
                    skip_key = f"{self._profile}_annotate_skip_target_lang"
                    skip_now = bool(self._cfg.get(skip_key))
                    if skip_now != self._last_skip_target:
                        self._last_skip_target = skip_now
                        self._line_tr_cache.clear()
                        self._last_text = ""
                        self._last_fp = None
                t0 = time.time()

                try:
                    rect, img = self._grab()
                except Exception as e:
                    if not _is_invalid_window_handle_error(e):
                        raise
                    _log.info("监视目标窗口已关闭 hwnd=%s", self._hwnd)
                    self.stopped.emit("目标窗口已关闭")
                    return
                if img is None:
                    _log.warning("监视目标无法捕获，结束")
                    self.stopped.emit("监视目标已关闭或无法捕获")
                    return
                if rect != self._last_rect:
                    self._last_rect = rect
                    self.window_moved.emit(*rect)

                # 画面几乎没变：跳过 OCR/翻译，省 GPU
                fp = _image_fingerprint(img)
                if self._last_fp is not None and fp == self._last_fp:
                    remaining = max(0.02, interval - (time.time() - t0))
                    end = time.time() + remaining
                    while self._running and time.time() < end:
                        time.sleep(min(0.02, max(0.001, end - time.time())))
                    continue
                self._last_fp = fp

                lines = self._ocr.recognize(img)
                text = "\n".join(ln.text for ln in lines)

                if text.strip():
                    sim = SequenceMatcher(None, self._last_text, text).ratio()
                    if sim < threshold:
                        self._last_text = text
                        mode_tag = (
                            f"{self._profile}_annotate"
                            if self._display_mode == "annotate"
                            else f"{self._profile}_subtitle"
                        )
                        if self._display_mode == "annotate":
                            items, translation = self._annotate_translate(
                                lines, target
                            )
                            if self._running:
                                self.annotations_ready.emit(items)
                                if translation:
                                    self.history_ready.emit(text, translation, mode_tag)
                        else:
                            translation = self._translator.translate(text, target)
                            if self._running:
                                self.subtitle_ready.emit(translation)
                                if translation:
                                    self.history_ready.emit(text, translation, mode_tag)
                        _log.info(
                            "监视重译 mode=%s chars=%d elapsed=%.2fs",
                            self._display_mode, len(text), time.time() - t0,
                        )

                remaining = max(0.02, interval - (time.time() - t0))
                end = time.time() + remaining
                while self._running and time.time() < end:
                    time.sleep(min(0.02, max(0.001, end - time.time())))

            _log.info("监视线程正常停止")
            self.stopped.emit("已停止监视")
        except Exception:
            _log.exception("监视线程异常")
            self.stopped.emit("监视出错：\n" + traceback.format_exc(limit=3))

    def _annotate_translate(self, lines, target: str):
        """备注：按行增量翻译，稳定原文走缓存，只请求变化行。

        可选跳过已是目标语言的行（不调模型、不叠标签）。
        """
        skip_key = f"{self._profile}_annotate_skip_target_lang"
        skip_target = bool(self._cfg.get(skip_key))

        srcs = [ln.text.strip() for ln in lines]
        todo_text: list[str] = []
        skipped = 0
        for s in srcs:
            if not s:
                continue
            if s in self._line_tr_cache:
                continue
            if skip_target and is_already_target_language(s, target):
                self._line_tr_cache[s] = _SKIP_TARGET
                skipped += 1
                continue
            todo_text.append(s)

        if todo_text and self._running:
            unique = list(dict.fromkeys(todo_text))
            trs = self._translator.translate_lines(unique, target)
            for s, tr in zip(unique, trs):
                if tr:
                    self._line_tr_cache[s] = tr
            if len(self._line_tr_cache) > 400:
                alive = set(srcs)
                self._line_tr_cache = {
                    k: v for k, v in self._line_tr_cache.items() if k in alive
                }

        items = []
        parts = []
        for ln, s in zip(lines, srcs):
            if not s:
                continue
            tr = self._line_tr_cache.get(s, "")
            if not tr or tr == _SKIP_TARGET:
                continue
            items.append((ln.box, tr))
            parts.append(tr)
        _log.info(
            "备注增量译 total=%d new=%d skip_target=%d cache=%d skip_on=%s",
            len([s for s in srcs if s]),
            len(todo_text),
            skipped,
            len(self._line_tr_cache),
            skip_target,
        )
        return items, "\n".join(parts)
