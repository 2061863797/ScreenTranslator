# -*- coding: utf-8 -*-
"""主程序：托盘常驻，热键调度各功能。"""

import sys

from PySide6.QtCore import QSharedMemory, QTimer
from PySide6.QtGui import QAction, QColor, QCursor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QMenu,
    QSystemTrayIcon,
)

from . import capture, config
from . import __version__
from .applog import LOG_PATH, get_logger, setup_logging
from .hotkeys import HotkeyManager
from .llama_server import LlamaServer
from .ocr_engine import OcrEngine
from .paths import ICON_ICO
from .storage import Storage
from .translator import Translator
from .ui.overlays import (
    AnnotateCtrl,
    AnnotationOverlay,
    RegionWatchFrame,
    SubtitleBar,
)
from .ui.region_selector import RegionSelector
from .ui.window_picker import WindowPicker
from .ui.windows import (
    HistoryWindow,
    HotkeyEdit,
    InputTranslateWindow,
    SettingsWindow,
)
from .window_watcher import WindowWatcher
from .workers import OcrTranslateWorker

# 单实例：QSharedMemory 键
_INSTANCE_KEY = "ScreenTranslator_SingleInstance_v1"


def _tray_icon() -> QIcon:
    """优先用打包的 icon.ico，缺失时回退纯色方块。"""
    ico = ICON_ICO
    if ico.exists():
        return QIcon(str(ico))
    pm = QPixmap(32, 32)
    pm.fill(QColor(32, 122, 244))
    return QIcon(pm)


def _hotkey_text(pynput_str: str) -> str:
    """配置里的 pynput 串 → 菜单可读文案（Alt+Q）。"""
    return HotkeyEdit._display(pynput_str)


class App:
    def __init__(self):
        setup_logging()
        self.log = get_logger("app")
        # 减少高分屏/组合窗闪烁（须在创建 QApplication 前尽量设置）
        from PySide6.QtCore import Qt as _Qt

        try:
            QApplication.setHighDpiScaleFactorRoundingPolicy(
                _Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
            )
        except Exception:
            pass
        self.qapp = QApplication.instance() or QApplication(sys.argv)
        self.qapp.setQuitOnLastWindowClosed(False)

        self.cfg = config.load()
        self.log.info(
            "配置已加载 target=%s max_tokens=%s port=%s model=%s",
            self.cfg.get("target_language"),
            self.cfg.get("max_tokens"),
            self.cfg.get("server_port"),
            self.cfg.get("model_path"),
        )
        self.storage = Storage()
        self.server = LlamaServer(self.cfg)
        self.translator = Translator(self.server.base_url, cfg=self.cfg)
        self.ocr = OcrEngine(self.cfg)

        # UI 组件（区域/窗口持续翻译：字幕条 + 备注；区域另有可拖/固定识别框）
        self.selector = RegionSelector()
        self.subtitle = SubtitleBar()
        self.annotation = AnnotationOverlay()
        self.annotation.set_text_color(
            self.cfg.get("annotate_text_color", "#00F0FF")
        )
        self.annotate_ctrl = AnnotateCtrl()
        self.region_frame = RegionWatchFrame()
        self.subtitle.mode_changed.connect(self._on_subtitle_mode_changed)
        self.subtitle.stop_requested.connect(
            lambda: self._stop_continuous_translate("已从字幕条关闭")
        )
        self.subtitle.switch_to_annotate.connect(
            lambda: self._switch_watch_display(True)
        )
        self.annotate_ctrl.stop_requested.connect(
            lambda: self._stop_continuous_translate("已从备注条关闭")
        )
        self.annotate_ctrl.switch_to_subtitle.connect(
            lambda: self._switch_watch_display(False)
        )
        self.annotate_ctrl.skip_target_changed.connect(self._on_annotate_skip_target)
        self.region_frame.region_moved.connect(self._on_region_frame_moved)
        # 当前会话是否备注模式（与 cfg 同步，便于运行中切换）
        self._watch_annotate: bool | None = None

        # 功能窗口（按需显示）
        self.settings_win = SettingsWindow(self.cfg, on_saved=self._on_settings_saved)
        self.translate_win = InputTranslateWindow(
            self.translator, self.cfg, ensure_server=self._ensure_server
        )
        self.history_win = HistoryWindow(
            self.storage,
            on_open=lambda s, t: self.translate_win.show_result(s, t),
        )

        self._workers: list[OcrTranslateWorker] = []  # 防止线程被垃圾回收
        self._watcher: WindowWatcher | None = None
        self._watch_hwnd: int | None = None
        self._watch_region: tuple[int, int, int, int] | None = None  # 区域监视时的选区
        self._watch_rect: tuple[int, int, int, int] | None = None  # 当前监视几何
        self._watch_profile: str | None = None  # "window" | "region"
        self._pending_mode = None  # 当前框选动作的用途（None=非主流程发起）
        self._pending_region = None
        self._window_picker: WindowPicker | None = None  # 选窗对话框（互斥用）
        self._stopping_watch = False  # 停线程时 processEvents 防重入

        self.selector.region_selected.connect(self._on_region)
        self.selector.cancelled.connect(self._on_region_cancelled)

        # 热键
        self.hotkeys = HotkeyManager(self.cfg)
        self.hotkeys.screenshot_triggered.connect(lambda: self._start_select("screenshot"))
        self.hotkeys.word_triggered.connect(self._word_translate)
        self.hotkeys.window_triggered.connect(self._toggle_window_watch)
        self.hotkeys.silent_ocr_triggered.connect(lambda: self._start_select("silent_ocr"))
        self.hotkeys.region_watch_triggered.connect(self._toggle_region_watch)

        self._build_tray()
        # 预创建框选遮罩原生窗口，减轻首次截屏翻译整屏闪一下
        self.selector.prepare()
        # 托盘建好后立刻后台预热：翻译模型 + OCR（二者并行）
        self._preload_models()

    # ---------- 初始化 ----------
    def _build_tray(self):
        self.tray = QSystemTrayIcon(_tray_icon())
        menu = QMenu()
        # 热键菜单项：保存 (action, cfg键, 标题)，便于改配置后刷新文案
        self._tray_hotkey_items: list[tuple[QAction, str, str]] = []
        for cfg_key, title, slot in [
            ("hotkey_screenshot", "截屏翻译", lambda: self._start_select("screenshot")),
            ("hotkey_word", "划词翻译", self._word_translate),
            ("hotkey_window", "窗口持续翻译", self._toggle_window_watch),
            ("hotkey_region_watch", "区域实时翻译", self._toggle_region_watch),
            ("hotkey_silent_ocr", "截图取字", lambda: self._start_select("silent_ocr")),
        ]:
            act = QAction(self._tray_hotkey_label(cfg_key, title), menu)
            act.triggered.connect(slot)
            menu.addAction(act)
            self._tray_hotkey_items.append((act, cfg_key, title))
        menu.addSeparator()
        for label, win in [
            ("翻译历史…", self.history_win),
            ("设置…", self.settings_win),
        ]:
            act = QAction(label, menu)
            act.triggered.connect(lambda _=False, w=win: self._show_window(w))
            menu.addAction(act)
        open_log = QAction("打开日志…", menu)
        open_log.triggered.connect(self._open_log)
        menu.addAction(open_log)
        menu.addSeparator()
        quit_act = QAction("退出", menu)
        quit_act.triggered.connect(self._quit)
        menu.addAction(quit_act)
        # 每次弹出菜单都按当前 cfg 刷新快捷键显示
        menu.aboutToShow.connect(self._refresh_tray_hotkeys)
        self.tray.setContextMenu(menu)
        self._refresh_tray_hotkeys()
        self.tray.show()

    def _tray_hotkey_label(self, cfg_key: str, title: str) -> str:
        return f"{title}（{_hotkey_text(self.cfg[cfg_key])}）"

    def _refresh_tray_hotkeys(self):
        """用当前配置更新托盘菜单热键文案与提示。"""
        for act, cfg_key, title in self._tray_hotkey_items:
            act.setText(self._tray_hotkey_label(cfg_key, title))
        self.tray.setToolTip(
            "翻译  "
            f"截屏 {_hotkey_text(self.cfg['hotkey_screenshot'])} | "
            f"划词 {_hotkey_text(self.cfg['hotkey_word'])} | "
            f"窗口 {_hotkey_text(self.cfg['hotkey_window'])} | "
            f"区域 {_hotkey_text(self.cfg['hotkey_region_watch'])} | "
            f"取字 {_hotkey_text(self.cfg['hotkey_silent_ocr'])}"
        )

    def _ensure_server(self) -> bool:
        """确保翻译服务可用；若启动时预热尚未完成，会等待同一启动过程结束。"""
        if self.server.is_healthy():
            return True
        self.log.info("翻译服务未就绪，开始启动/等待…")
        self.tray.showMessage("翻译", "正在等待翻译模型就绪…")
        try:
            # 与预热共用锁：不会重复拉起第二个 llama-server
            self.server.start()
            self.log.info("翻译服务已就绪")
            return True
        except Exception as e:
            self.log.exception("翻译服务启动失败")
            from .ui.topmost import topmost_message

            topmost_message("critical", "翻译服务启动失败", str(e))
            return False

    def _preload_models(self):
        """启动时并行预热：llama 翻译服务 + PaddleOCR + 一次空转推理。

        首次翻译卡顿常见原因：
        1) 翻译模型还在加载 / 首次 GPU 推理未热身
        2) OCR（Paddle）默认懒加载，第一次截屏/划词才初始化，往往更慢
        """
        import threading

        if getattr(self, "_preload_started", False):
            return
        self._preload_started = True
        self._preload_status = {"llama": "pending", "ocr": "pending"}
        # 启动气泡只在 exec() 弹一次；这里只在「全部就绪」或「失败」时再提示

        def _notify_if_ready():
            st = self._preload_status
            if st["llama"] == "ok" and st["ocr"] == "ok":
                # 仅写日志，不弹托盘气泡
                self.log.info("预热完成：OCR 与翻译模型均已就绪")

        def _set(key: str, value: str, err: str | None = None):
            self._preload_status[key] = value
            if value == "fail" and err:
                name = "翻译模型" if key == "llama" else "OCR"
                self.log.error("预热失败 %s: %s", key, err)
                QTimer.singleShot(
                    0,
                    lambda: self.tray.showMessage(
                        f"翻译：{name}加载失败",
                        err[:200],
                        QSystemTrayIcon.MessageIcon.Warning,
                    ),
                )
            else:
                self.log.info("预热进度 %s=%s", key, value)
                QTimer.singleShot(0, _notify_if_ready)

        def _load_llama():
            try:
                self.log.info("预热：启动 llama-server…")
                self.server.start()
                # /health 就绪后仍做一次极短推理，预热 GPU/CUDA 与首 token 路径
                try:
                    self.translator.translate("ok", "简体中文")
                    self.log.info("预热：翻译空转成功")
                except Exception as e:
                    self.log.warning("预热：翻译空转失败（不阻断）: %s", e)
                _set("llama", "ok")
            except Exception as e:
                _set("llama", "fail", str(e))

        def _load_ocr():
            try:
                self.log.info("预热：加载 PaddleOCR…")
                self.ocr.preload()
                # 用带简单笔画的样例图跑通 predict，更接近真实屏幕
                import numpy as np

                dummy = np.full((120, 320, 3), 255, dtype=np.uint8)
                dummy[40:50, 20:300] = 30  # 一条深色横线当「文字」
                try:
                    self.ocr.recognize(dummy)
                    self.log.info("预热：OCR 空转成功")
                except Exception as e:
                    self.log.warning("预热：OCR 空转失败（不阻断）: %s", e)
                _set("ocr", "ok")
            except Exception as e:
                _set("ocr", "fail", str(e))

        self.log.info("开始后台预热 OCR + 翻译模型")
        threading.Thread(target=_load_llama, daemon=True, name="llama-preload").start()
        threading.Thread(target=_load_ocr, daemon=True, name="ocr-preload").start()

    # ---------- 截屏 / 静默取字 ----------
    def _start_select(self, mode: str):
        self.log.info("开始框选 mode=%s", mode)
        self._pending_mode = mode
        self.selector.start()

    def _on_region(self, x: int, y: int, w: int, h: int):
        if self._pending_mode is None:
            return  # 本次框选由其他功能发起，不在这里处理
        mode, self._pending_mode = self._pending_mode, None
        if mode == "region_watch":
            self._start_region_watch(x, y, w, h)
            return
        self._pending_region = (x, y, w, h)
        # 优先用框选时已截好的静态底图裁切（无二次截屏、减轻闪一下）
        img = self.selector.take_crop()
        if img is None:
            img = capture.grab_region(x, y, w, h)
        do_translate = mode == "screenshot"
        if do_translate and not self._ensure_server():
            return
        worker = OcrTranslateWorker(
            self.ocr, self.translator, self.cfg,
            image=img, do_translate=do_translate,
            target_language=self.translate_win.target_language,
        )
        if mode == "screenshot":
            worker.finished_ok.connect(self._show_screenshot_result)
        else:
            worker.finished_ok.connect(self._finish_silent_ocr)
        worker.failed.connect(self._show_error)
        self._run_worker(worker)

    def _show_screenshot_result(self, source: str, translation: str):
        x, y, w, h = self._pending_region
        self.storage.add_history(source, translation, "screenshot")
        self.translate_win.show_result(source, translation, x, y + h + 8)

    def _finish_silent_ocr(self, source: str, _translation: str):
        QApplication.clipboard().setText(source)
        self.tray.showMessage("截图取字", "已复制到剪贴板：\n" + source[:120])

    # ---------- 划词翻译 ----------
    def _word_translate(self):
        """划词：多路复制（终端常需 Ctrl+Shift+C）→ 剪贴板 → 失败则 OCR。

        终端/部分应用问题：
        - Ctrl+C 是中断不是复制
        - 仅 Ctrl+Shift+C 或「选中即复制」有效
        - 焦点控件需 WM_COPY
        """
        if not self._ensure_server():
            return
        import time as _time

        from . import selection as sel

        self._word_old_clip = QApplication.clipboard().text()
        # 唯一标记：只有剪贴板变成「非标记」才算复制成功
        self._word_marker = f"\u200bST{_time.time_ns()}\u200b"
        QApplication.clipboard().setText(self._word_marker)
        # 复制阶段：wm_copy → ctrl_c → ctrl_shift_c → ctrl_insert
        self._word_copy_phase = 0
        self._word_copy_kinds = (
            "wm_copy", "ctrl_c", "ctrl_shift_c", "ctrl_insert"
        )
        self._word_fire_copy_phase()
        # 每阶段轮询约 350ms，共 4 阶段
        self._word_poll_clipboard(attempts=12)

    def _word_fire_copy_phase(self):
        from . import selection as sel

        kinds = getattr(self, "_word_copy_kinds", ("ctrl_c",))
        i = int(getattr(self, "_word_copy_phase", 0))
        if i < 0 or i >= len(kinds):
            return
        kind = kinds[i]
        self.log.info("划词复制阶段 %s", kind)
        # 每阶段重新写入标记，避免上一阶段残留误判
        marker = getattr(self, "_word_marker", "")
        if marker:
            QApplication.clipboard().setText(marker)
        if kind == "wm_copy":
            sel.try_wm_copy()
        else:
            sel.send_copy_shortcut(kind)

    def _word_clipboard_text(self) -> str:
        """读取剪贴板；若仍是标记或空则返回空串。"""
        marker = getattr(self, "_word_marker", None)
        text = QApplication.clipboard().text()
        if not text:
            return ""
        if marker and text == marker:
            return ""
        return text.strip()

    def _word_poll_clipboard(self, attempts: int):
        """高频轮询；本阶段失败则进入下一复制方式。"""
        text = self._word_clipboard_text()
        if text:
            self._word_finish_with_text(text)
            return
        if attempts > 0:
            QTimer.singleShot(
                30, lambda: self._word_poll_clipboard(attempts - 1)
            )
            return
        # 本阶段超时 → 下一阶段
        phase = int(getattr(self, "_word_copy_phase", 0)) + 1
        kinds = getattr(self, "_word_copy_kinds", ())
        if phase < len(kinds):
            self._word_copy_phase = phase
            self._word_fire_copy_phase()
            self._word_poll_clipboard(attempts=12)
            return
        # 全部复制方式失败
        self._word_finish_with_text("")

    def _word_finish_with_text(self, text: str):
        """有选中文本则译；拿不到则提示（仅划词复制，不做附近 OCR）。"""
        old = getattr(self, "_word_old_clip", "") or ""
        pos = QCursor.pos()
        # 立刻还原用户剪贴板
        try:
            QApplication.clipboard().setText(old)
        except Exception:
            pass

        if not text:
            self.tray.showMessage("划词翻译", "未获取到选中文本")
            return
        self.log.info("划词拿到文本 chars=%d", len(text))
        worker = OcrTranslateWorker(
            self.ocr, self.translator, self.cfg, text=text,
            target_language=self.translate_win.target_language,
        )
        worker.finished_ok.connect(
            lambda s, t: self._show_word_result(pos.x(), pos.y(), s, t)
        )
        worker.failed.connect(self._show_error)
        self._run_worker(worker)

    def _show_word_result(self, x: int, y: int, source: str, translation: str):
        self.storage.add_history(source, translation, "word")
        self.translate_win.show_result(source, translation, x + 12, y + 16)

    # ---------- 窗口 / 区域持续翻译 ----------
    def _is_continuous_active(self) -> bool:
        """是否已有持续翻译会话：监视线程在跑，或任一浮层仍显示。"""
        if self._watcher is not None and self._watcher.isRunning():
            return True
        try:
            if self.subtitle.isVisible():
                return True
        except Exception:
            pass
        try:
            if self.annotation.isVisible():
                return True
        except Exception:
            pass
        try:
            if self.annotate_ctrl.isVisible():
                return True
        except Exception:
            pass
        try:
            if self.region_frame.isVisible():
                return True
        except Exception:
            pass
        return False

    def _is_continuous_selecting(self) -> bool:
        """是否正在选择持续翻译目标（选窗对话框 / 区域框选）。"""
        picker = self._window_picker
        if picker is not None:
            try:
                if picker.isVisible():
                    return True
            except RuntimeError:
                self._window_picker = None
        if self._pending_mode == "region_watch":
            return True
        try:
            # 框选遮罩开着且用途是区域持续翻译
            if self.selector.isVisible() and self._pending_mode == "region_watch":
                return True
        except Exception:
            pass
        return False

    def _cancel_continuous_select(self):
        """取消进行中的选窗 / 区域框选（不动截屏/取字框选）。"""
        if self._pending_mode == "region_watch":
            self._pending_mode = None
            try:
                if self.selector.isVisible():
                    self.selector.cancel()
            except Exception:
                pass
        picker = self._window_picker
        if picker is not None:
            try:
                picker.reject()
            except Exception:
                pass
            self._window_picker = None

    def _on_region_cancelled(self):
        """框选 Esc / 无效框 / 程序 cancel：清掉持续翻译选区状态。"""
        if self._pending_mode == "region_watch":
            self.log.info("区域持续翻译：框选已取消")
            self._pending_mode = None

    def _hide_watch_ui(self):
        """立刻藏起所有持续翻译浮层（不等线程结束）。"""
        try:
            self.subtitle.set_interactive(False)
            self.subtitle.hide()
        except Exception:
            pass
        try:
            self.annotation.hide()
            self.annotation.clear()
        except Exception:
            pass
        try:
            self.annotate_ctrl.hide()
        except Exception:
            pass
        try:
            self.region_frame.hide_frame()
        except Exception:
            pass

    def _disconnect_watcher(self, w) -> None:
        """断开监视线程全部信号，避免停止后仍刷新 UI / 历史。"""
        if w is None:
            return
        for sig in (
            w.stopped,
            w.subtitle_ready,
            w.annotations_ready,
            w.history_ready,
            w.window_moved,
        ):
            try:
                sig.disconnect()
            except (TypeError, RuntimeError):
                pass

    def _join_watcher(self, w, *, label: str = "监视线程") -> None:
        """请求停止并短暂等待；等待期间 processEvents 用标志防重入。"""
        if w is None:
            return
        self._disconnect_watcher(w)
        w.stop()
        was = self._stopping_watch
        self._stopping_watch = True
        try:
            for _ in range(40):
                if not w.isRunning():
                    break
                self.qapp.processEvents()
                w.wait(50)
            if w.isRunning():
                self.log.warning("%s仍在运行（可能卡在翻译请求），UI 已关闭", label)
        finally:
            self._stopping_watch = was

    def _stop_continuous_translate(self, reason: str = "已停止监视"):
        """停止窗口/区域持续翻译：先关 UI，再停线程，避免「关不掉」。"""
        if self._stopping_watch and self._watcher is None:
            # 已在停止流程中，避免 processEvents 重入再开会话
            self._hide_watch_ui()
            self._cancel_continuous_select()
            return
        self.log.info("停止持续翻译: %s", reason)
        # 0) 若还在选窗/框选，一并取消
        self._cancel_continuous_select()
        # 1) 先藏 UI，翻译卡在后台时用户也能马上关掉浮层
        self._hide_watch_ui()
        w = self._watcher
        self._watcher = None
        self._watch_hwnd = None
        self._watch_region = None
        self._watch_rect = None
        self._watch_profile = None
        self._watch_annotate = None
        self._join_watcher(w, label="监视线程")
        # 不弹托盘气泡，写日志即可

    def _toggle_window_watch(self):
        # 停止流程中（等旧线程）不再开新会话，避免叠两个
        if self._stopping_watch:
            self._stop_continuous_translate("已停止窗口持续翻译")
            return
        # 已有会话 或 正在选窗/框选 → 一律只停/取消，不同时开第二个
        if self._is_continuous_active() or self._is_continuous_selecting():
            self._stop_continuous_translate("已停止窗口持续翻译")
            return
        if not self._ensure_server():
            return
        picker = WindowPicker()
        self._window_picker = picker
        try:
            accepted = bool(picker.exec())
            hwnd = picker.selected_hwnd if accepted else None
        finally:
            self._window_picker = None
        if not accepted or hwnd is None:
            return
        if self._stopping_watch:
            self.log.info("停止过程中忽略新的窗口持续翻译启动")
            return
        # 选窗过程中若残留了其它会话，启动前清干净（保证同时只有一个）
        if self._is_continuous_active():
            self._stop_continuous_translate("切换为窗口持续翻译")
        if self._stopping_watch:
            return
        rect = capture.get_window_rect(hwnd)
        annotate = bool(self.cfg.get("window_watch_annotate"))
        self._launch_watcher(
            hwnd=hwnd, rect=rect, annotate=annotate, profile="window"
        )

    def _toggle_region_watch(self):
        """框选屏幕区域持续翻译（显示/间隔在设置里单独配置）。"""
        if self._stopping_watch:
            self._stop_continuous_translate("已停止区域持续翻译")
            return
        # 已有会话 或 正在选 → 只停，不叠第二个
        if self._is_continuous_active() or self._is_continuous_selecting():
            self._stop_continuous_translate("已停止区域持续翻译")
            return
        if not self._ensure_server():
            return
        self._start_select("region_watch")

    def _start_region_watch(self, x: int, y: int, w: int, h: int):
        if self._stopping_watch:
            self.log.info("停止过程中忽略区域持续翻译启动")
            return
        region = (x, y, w, h)
        # 框选完成后若还有旧会话/浮层，先清再启
        if self._is_continuous_active():
            self._stop_continuous_translate("切换为区域持续翻译")
        if self._stopping_watch:
            return
        annotate = bool(self.cfg.get("region_watch_annotate"))
        self._launch_watcher(
            region=region, rect=region, annotate=annotate, profile="region"
        )

    def _launch_watcher(self, rect, annotate: bool,
                        hwnd: int | None = None, region=None,
                        profile: str = "window"):
        if self._stopping_watch:
            self.log.info("停止过程中拒绝启动持续翻译 profile=%s", profile)
            return
        # 硬互斥：启动前停掉旧监视线程，避免两个 WindowWatcher 并行
        old = self._watcher
        self._watcher = None
        if old is not None:
            self.log.info("启动前停止旧监视线程 profile=%s", self._watch_profile)
            self._join_watcher(old, label="旧监视线程")
        if self._stopping_watch:
            return
        # 只取消区域持续翻译的框选，不动截屏/取字
        if self._pending_mode == "region_watch":
            self._pending_mode = None
            try:
                if self.selector.isVisible():
                    self.selector.cancel()
            except Exception:
                pass

        if hwnd is not None:
            self._watch_region = None
            self.region_frame.hide_frame()
        self._watch_hwnd = hwnd
        self._watch_region = region
        self._watch_rect = rect
        self._watch_profile = profile
        annotate = bool(annotate)
        self._watch_annotate = annotate
        # 写回对应 profile 的显示模式（内存；设置页保存才会落盘）
        self.cfg[f"{profile}_watch_annotate"] = annotate
        self.log.info(
            "启动持续翻译 profile=%s annotate=%s hwnd=%s region=%s rect=%s",
            profile, annotate, hwnd, region, rect,
        )
        # 区域翻译：单独识别框，可拖动 / 固定
        if region is not None:
            self.region_frame.show_region(region)
        else:
            self.region_frame.hide_frame()
        # 备注=贴原文旁（窗口/区域相同）；字幕条=外侧，不盖住目标
        self._apply_watch_display(annotate, rect, announce=True)
        display = "annotate" if annotate else "subtitle"
        self._watcher = WindowWatcher(
            self.ocr, self.translator, self.cfg,
            hwnd=hwnd, region=region, display_mode=display,
            profile=profile,
        )
        self._watcher.subtitle_ready.connect(self.subtitle.set_text)
        self._watcher.annotations_ready.connect(self.annotation.set_items)
        self._watcher.history_ready.connect(self._on_watch_history)
        self._watcher.window_moved.connect(self._on_target_window_moved)
        self._watcher.stopped.connect(self._on_watch_stopped)
        self._watcher.start()

    def _on_region_frame_moved(self, x: int, y: int, w: int, h: int):
        """区域识别框被拖动/缩放：同步 OCR 选区与字幕/备注位置。"""
        if self._watch_region is None:
            return
        rect = (x, y, w, h)
        self._watch_region = rect
        self._watch_rect = rect
        if self._watcher and self._watcher.isRunning():
            self._watcher.set_region(rect)
        self.annotation.update_geometry(rect)
        # 跟随模式才重贴；自由/固定保持用户拖好的字幕位置
        if self.subtitle.mode == "follow":
            self.subtitle.attach_below(rect, outside=True)
        if self.annotate_ctrl.isVisible():
            self.annotate_ctrl.place_above(rect)
        self.log.info("区域识别框更新 %s", rect)

    def _on_watch_history(self, source: str, translation: str, mode: str):
        """持续翻译有实质新译文时写入历史。"""
        try:
            self.storage.add_history(source, translation, mode)
        except Exception:
            pass

    def _apply_watch_display(self, annotate: bool, rect, *, announce: bool = False):
        """备注：贴原文旁（窗口/区域同）；字幕条：目标外侧，不遮挡。"""
        if annotate:
            self.subtitle.set_interactive(False)
            self.subtitle.hide()
            self.annotation.update_geometry(rect)
            # 备注层立即占位（有译文后 set_items 再显示）；不 raise 防闪
            if not self.annotation.isVisible():
                self.annotation.show()
            # 备注模式控制条（跳过目标语 + 关闭）；按当前会话 profile 读配置
            self.annotate_ctrl.set_skip_target(
                bool(self.cfg.get(self._annotate_skip_cfg_key()))
            )
            self.annotate_ctrl.place_above(rect)
        else:
            self.annotation.clear()
            try:
                self.annotate_ctrl.hide()
            except Exception:
                pass
            # 外置字幕可缩放；outside=True 永远不盖住目标窗/识别区
            self.subtitle.set_interactive(True)
            self.subtitle.set_mode("follow")
            self.subtitle.attach_below(rect, outside=True)
            self.subtitle.set_text(
                "开始监视，等待识别文字…" if announce else "已切换为字幕条…"
            )

    def _switch_watch_display(self, annotate: bool):
        """运行中切换字幕 ↔ 备注（不停止监视线程）。"""
        if self._stopping_watch:
            return
        if self._watcher is None or not self._watcher.isRunning():
            self.log.info("无进行中的持续翻译，忽略显示模式切换")
            return
        annotate = bool(annotate)
        if self._watch_annotate is not None and bool(self._watch_annotate) == annotate:
            return  # 已是目标模式
        rect = self._watch_rect
        if rect is None:
            if self._watch_region is not None:
                rect = self._watch_region
            elif self._watch_hwnd is not None:
                rect = capture.get_window_rect(self._watch_hwnd)
        if rect is None:
            self.log.warning("切换显示模式失败：无目标区域")
            return
        profile = self._watch_profile
        if profile not in ("window", "region"):
            profile = "region" if self._watch_region is not None else "window"
        self._watch_annotate = annotate
        self.cfg[f"{profile}_watch_annotate"] = annotate
        try:
            config.save(self.cfg)
        except Exception:
            pass
        mode = "annotate" if annotate else "subtitle"
        try:
            self._watcher.set_display_mode(mode)
        except Exception:
            self.log.exception("set_display_mode 失败")
            return
        self._apply_watch_display(annotate, rect, announce=False)
        if annotate:
            # 备注尚无新结果时先空层；下一轮监视会 set_items
            self.annotation.set_items([])
            self.log.info("已切换为备注模式 profile=%s", profile)
        else:
            self.log.info("已切换为字幕条模式 profile=%s", profile)

    def _annotate_skip_cfg_key(self) -> str:
        """当前会话对应的「跳过目标语」配置键。

        注意：self._watch_profile 是 str 属性（window/region），不可再定义同名方法。
        """
        p = self._watch_profile
        if p not in ("window", "region"):
            p = "region" if self._watch_region is not None else "window"
        return f"{p}_annotate_skip_target_lang"

    def _on_annotate_skip_target(self, on: bool):
        """备注条「跳过目标语」：写入当前会话（窗口/区域）各自配置，下轮生效。"""
        on = bool(on)
        key = self._annotate_skip_cfg_key()
        self.cfg[key] = on
        # 去掉旧共用键，避免下次 load 再迁移覆盖
        self.cfg.pop("annotate_skip_target_lang", None)
        try:
            config.save(self.cfg)
        except Exception:
            pass
        self.log.info("备注跳过目标语 %s: %s", key, on)

    def _on_subtitle_mode_changed(self, mode: str):
        """字幕条：跟随 / 自由 / 固定。跟随模式重新吸附到目标外侧。"""
        if mode != "follow":
            return
        if self._watch_hwnd is not None:
            self.subtitle.attach_below(
                capture.get_window_rect(self._watch_hwnd), outside=True
            )
        elif self._watch_region is not None:
            self.subtitle.attach_below(self._watch_region, outside=True)

    def _on_target_window_moved(self, x: int, y: int, w: int, h: int):
        # 区域监视的几何由识别框控制，窗口 rect 信号不改 region
        if self._watch_region is not None:
            return
        rect = (x, y, w, h)
        self._watch_rect = rect
        # 跟随模式才重贴；自由/固定保持用户位置
        if self.subtitle.isVisible() and self.subtitle.mode == "follow":
            self.subtitle.attach_below(rect, outside=True)
        if self.annotation.isVisible():
            self.annotation.update_geometry(rect)
        if self.annotate_ctrl.isVisible():
            self.annotate_ctrl.place_above(rect)

    def _on_watch_stopped(self, reason: str):
        """线程自行结束（目标关闭/出错）时的清理。"""
        self.log.info("持续翻译线程结束: %s", reason.replace("\n", " | ")[:300])
        # 可能已被用户手动停止（_watcher 已置空）
        if self._watcher is not None and not self._watcher.isRunning():
            self._watcher = None
        self._hide_watch_ui()
        self._watch_hwnd = None
        self._watch_region = None
        self._watch_rect = None
        self._watch_profile = None
        self._watch_annotate = None

    # ---------- 公共 ----------
    def _show_window(self, win):
        """设置/历史/翻译窗：置顶到最前，避免被挡住找不到。"""
        from .ui.topmost import center_on_cursor_screen, raise_to_front

        center_on_cursor_screen(win)
        raise_to_front(win, activate=True)

    def _on_settings_saved(self):
        # 热键可能已修改：重新注册监听，并刷新托盘菜单文案
        conflicts = self.hotkeys.start()
        if conflicts:
            self.tray.showMessage(
                "热键冲突",
                "；".join(conflicts)[:200],
                QSystemTrayIcon.MessageIcon.Warning,
            )
        self._refresh_tray_hotkeys()
        self.translate_win.sync_language_from_cfg()
        # 备注译文颜色
        try:
            self.annotation.set_text_color(
                self.cfg.get("annotate_text_color", "#00F0FF")
            )
        except Exception:
            pass
        # 备注条上的「跳过目标语」与设置同步（按当前会话类型）
        self.annotate_ctrl.set_skip_target(
            bool(self.cfg.get(self._annotate_skip_cfg_key()))
        )
        # 若正在监视：仅当「显示模式」与当前会话不一致时才切换（避免只改颜色/热键也清缓存重译）
        if (
            self._watcher
            and self._watcher.isRunning()
            and self._watch_rect
            and self._watch_profile
        ):
            key = f"{self._watch_profile}_watch_annotate"
            annotate = bool(self.cfg.get(key))
            cur = self._watch_annotate
            if cur is None or bool(cur) != annotate:
                self._switch_watch_display(annotate)

    def _run_worker(self, worker: OcrTranslateWorker):
        self._workers.append(worker)

        def _drop(_w=worker):
            try:
                self._workers.remove(_w)
            except ValueError:
                pass

        worker.finished.connect(_drop)
        worker.start()

    def _show_error(self, msg: str):
        # 完整报错写 app.log，托盘只显示摘要
        self.log.error("任务失败:\n%s", msg)
        self.tray.showMessage("翻译：出错", msg[:200], QSystemTrayIcon.MessageIcon.Warning)

    def _open_log(self):
        """用系统默认方式打开日志文件。"""
        try:
            LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            if not LOG_PATH.exists():
                LOG_PATH.write_text("", encoding="utf-8")
            # Windows：用默认程序打开
            import os

            os.startfile(str(LOG_PATH))  # type: ignore[attr-defined]
            self.log.info("用户打开日志 %s", LOG_PATH)
        except Exception as e:
            self.log.exception("打开日志失败")
            from .ui.topmost import topmost_message

            topmost_message(
                "information",
                "日志",
                f"日志路径：\n{LOG_PATH}\n\n打开失败：{e}",
            )

    def _quit(self):
        self.log.info("退出程序")
        self._stop_continuous_translate("程序退出")
        self.hotkeys.stop()
        self.server.stop()
        self.storage.close()
        self.qapp.quit()

    def exec(self) -> int:
        conflicts = self.hotkeys.start()
        if conflicts:
            self.log.warning("热键冲突: %s", conflicts)
        self.log.info(
            "应用已启动 v%s 截屏=%s 划词=%s 窗口=%s 区域=%s 取字=%s log=%s",
            __version__,
            self.cfg.get("hotkey_screenshot"),
            self.cfg.get("hotkey_word"),
            self.cfg.get("hotkey_window"),
            self.cfg.get("hotkey_region_watch"),
            self.cfg.get("hotkey_silent_ocr"),
            LOG_PATH,
        )
        # 启动后不弹托盘气泡，热键/状态看设置里的实时日志
        return self.qapp.exec()


def _acquire_single_instance(qapp: QApplication) -> QSharedMemory | None:
    """确保仅一个实例；已有实例时返回 None。"""
    mem = QSharedMemory(_INSTANCE_KEY)
    if not mem.create(1):
        from .ui.topmost import topmost_message

        topmost_message(
            "warning",
            "翻译",
            "翻译已在运行中（托盘区）。\n请勿重复启动。",
        )
        return None
    # 保持引用，防止被 GC 释放共享内存
    qapp._screen_translator_instance = mem  # type: ignore[attr-defined]
    return mem


def _install_exception_hooks() -> None:
    """未捕获异常写入 app.log，避免 pythonw 静默消失。"""
    import threading
    import traceback

    def _hook(exc_type, exc, tb):
        try:
            log = get_logger("crash")
            log.critical(
                "未捕获异常\n%s",
                "".join(traceback.format_exception(exc_type, exc, tb)),
            )
        except Exception:
            pass
        # 保留默认行为（stderr）；pythonw 无控制台时至少有文件日志
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _hook

    if hasattr(threading, "excepthook"):

        def _thread_hook(args):
            try:
                log = get_logger("crash")
                log.critical(
                    "线程未捕获异常 thread=%s\n%s",
                    getattr(args, "thread", None),
                    "".join(
                        traceback.format_exception(
                            args.exc_type, args.exc_value, args.exc_traceback
                        )
                    ),
                )
            except Exception:
                pass

        threading.excepthook = _thread_hook  # type: ignore[assignment]


def main():
    _install_exception_hooks()
    qapp = QApplication.instance() or QApplication(sys.argv)
    if _acquire_single_instance(qapp) is None:
        return 1
    app = App()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
