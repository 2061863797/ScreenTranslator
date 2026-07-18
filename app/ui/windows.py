# -*- coding: utf-8 -*-
"""功能窗口：设置、翻译历史、统一翻译窗口（输入/划词/截屏共用）。"""

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizeGrip,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .. import config
from ..applog import LOG_PATH, get_log_emitter, recent_lines
from .overlays import _DraggableMixin
from .theme import (
    CornerSizeGrip,
    FLOAT_PANEL_STYLE,
    SETTINGS_STYLE,
    apply_frameless_float,
)
from .topmost import ensure_stays_on_top, raise_to_front, show_toast, topmost_message

LANGUAGES = [
    "简体中文", "繁体中文", "英语", "日语", "韩语", "法语", "德语",
    "俄语", "西班牙语", "葡萄牙语", "意大利语", "泰语", "越南语", "阿拉伯语",
]


class HotkeyEdit(QLineEdit):
    """点击后录入全局热键：键盘组合 或 鼠标侧键（可加 Ctrl/Alt/Shift）。

    存储：键盘如 <alt>+q；侧键如 mouse.x1、<ctrl>+mouse.x2。
    """

    _MOD_KEYS = {
        Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta,
    }

    def __init__(self, pynput_str: str):
        super().__init__()
        self.setReadOnly(True)
        self.setPlaceholderText("点击后按快捷键或鼠标侧键…")
        self._value = pynput_str
        self.setText(self._display(pynput_str))
        # 接收侧键（Back/Forward）
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    @property
    def value(self) -> str:
        """返回热键配置串。"""
        return self._value

    def set_value(self, pynput_str: str):
        self._value = pynput_str
        self.setText(self._display(pynput_str))

    def focusInEvent(self, event):
        self.setText("请按快捷键或鼠标侧键…")
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.setText(self._display(self._value))
        super().focusOutEvent(event)

    def _mod_parts(self, mods) -> list[str]:
        parts = []
        if mods & Qt.KeyboardModifier.ControlModifier:
            parts.append("<ctrl>")
        if mods & Qt.KeyboardModifier.AltModifier:
            parts.append("<alt>")
        if mods & Qt.KeyboardModifier.ShiftModifier:
            parts.append("<shift>")
        if mods & Qt.KeyboardModifier.MetaModifier:
            parts.append("<cmd>")
        return parts

    def _commit(self, parts: list[str]):
        self._value = "+".join(parts)
        self.setText(self._display(self._value))
        self.clearFocus()

    def mousePressEvent(self, event):
        """录入态下捕获鼠标侧键（X1/X2）。左键仅用于聚焦，不写入。"""
        if not self.hasFocus():
            super().mousePressEvent(event)
            return
        btn = event.button()
        mouse_tok = None
        if btn == Qt.MouseButton.BackButton:
            mouse_tok = "mouse.x1"
        elif btn == Qt.MouseButton.ForwardButton:
            mouse_tok = "mouse.x2"
        if mouse_tok is None:
            # 左/右/中键不作为热键，避免点选输入框时误设
            if btn == Qt.MouseButton.LeftButton:
                super().mousePressEvent(event)
            return
        parts = self._mod_parts(event.modifiers())
        parts.append(mouse_tok)
        self._commit(parts)
        event.accept()

    def keyPressEvent(self, event):
        key = event.key()
        if key in self._MOD_KEYS or key == Qt.Key.Key_unknown:
            return  # 只按了修饰键，等主键
        if key == Qt.Key.Key_Escape:
            self.clearFocus()  # Esc 取消录入
            return
        parts = self._mod_parts(event.modifiers())

        main = self._main_key(key, event.text())
        if main is None:
            return
        if not parts:
            # 无修饰键的裸键盘键太容易误触；鼠标侧键允许单独
            self.setText("键盘请加 Ctrl/Alt/Shift；侧键可直接按…")
            return
        parts.append(main)
        self._commit(parts)

    @staticmethod
    def _main_key(key, text: str) -> str | None:
        """Qt 键码 → pynput 主键名。"""
        if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F24:
            return f"<f{key - Qt.Key.Key_F1 + 1}>"
        specials = {
            Qt.Key.Key_Space: "<space>",
            Qt.Key.Key_Tab: "<tab>",
            Qt.Key.Key_Return: "<enter>",
            Qt.Key.Key_Enter: "<enter>",
            Qt.Key.Key_Home: "<home>",
            Qt.Key.Key_End: "<end>",
            Qt.Key.Key_PageUp: "<page_up>",
            Qt.Key.Key_PageDown: "<page_down>",
            Qt.Key.Key_Insert: "<insert>",
            Qt.Key.Key_Delete: "<delete>",
            Qt.Key.Key_Up: "<up>",
            Qt.Key.Key_Down: "<down>",
            Qt.Key.Key_Left: "<left>",
            Qt.Key.Key_Right: "<right>",
        }
        if key in specials:
            return specials[key]
        if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            return chr(key).lower()
        if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
            return chr(key)
        if text and text.isprintable() and not text.isspace():
            return text.lower()
        return None

    @staticmethod
    def _display(pynput_str: str) -> str:
        """配置串 → 人类可读（<alt>+q → Alt+Q；mouse.x1 → 侧键1）。"""
        names = {
            "<ctrl>": "Ctrl", "<alt>": "Alt", "<shift>": "Shift", "<cmd>": "Win",
            "<space>": "Space", "<tab>": "Tab", "<enter>": "Enter",
            "mouse.x1": "侧键1(后退)",
            "mouse.x2": "侧键2(前进)",
            "mouse.button4": "侧键1(后退)",
            "mouse.button5": "侧键2(前进)",
            "mouse.back": "侧键1(后退)",
            "mouse.forward": "侧键2(前进)",
        }
        out = []
        for p in (pynput_str or "").split("+"):
            p = p.strip()
            if not p:
                continue
            pl = p.lower()
            if pl in names:
                out.append(names[pl])
            elif p in names:
                out.append(names[p])
            elif p.startswith("<f") and p.endswith(">"):
                out.append(p[1:-1].upper())
            elif p.startswith("<") and p.endswith(">"):
                out.append(p[1:-1].replace("_", " ").title())
            else:
                out.append(p.upper())
        return "+".join(out) if out else ""


def _settings_card(title: str, hint: str = "") -> tuple[QFrame, QVBoxLayout]:
    """设置页内容卡片。"""
    card = QFrame()
    card.setObjectName("card")
    lay = QVBoxLayout(card)
    lay.setContentsMargins(14, 12, 14, 14)
    lay.setSpacing(10)
    t = QLabel(title)
    t.setObjectName("cardTitle")
    lay.addWidget(t)
    if hint:
        h = QLabel(hint)
        h.setObjectName("cardHint")
        h.setWordWrap(True)
        lay.addWidget(h)
    return card, lay


def _form_row(label: str, widget: QWidget) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(12)
    lab = QLabel(label)
    lab.setMinimumWidth(120)
    lab.setStyleSheet("color:rgba(255,255,255,200);")
    row.addWidget(lab)
    row.addWidget(widget, stretch=1)
    return row


class SettingsWindow(_DraggableMixin, QWidget):
    """高级设置：侧栏分类 + 卡片内容；实时日志独立页。"""

    def __init__(self, cfg: dict, on_saved=None):
        super().__init__()
        self.setWindowTitle("设置")
        apply_frameless_float(self)
        self.resize(780, 560)
        self.setMinimumSize(640, 440)
        ensure_stays_on_top(self)
        self._cfg = cfg
        self._on_saved = on_saved
        self._log_auto_scroll = True

        # —— 控件 ——
        self._target = QComboBox()
        self._target.addItems(LANGUAGES)

        self._hk_shot = HotkeyEdit(cfg["hotkey_screenshot"])
        self._hk_word = HotkeyEdit(cfg["hotkey_word"])
        self._hk_win = HotkeyEdit(cfg["hotkey_window"])
        self._hk_ocr = HotkeyEdit(cfg["hotkey_silent_ocr"])
        self._hk_region = HotkeyEdit(cfg["hotkey_region_watch"])

        def _ms_spin() -> QSpinBox:
            sp = QSpinBox()
            sp.setRange(200, 5000)
            sp.setSingleStep(100)
            sp.setSuffix(" 毫秒")
            return sp

        self._win_interval = _ms_spin()
        self._win_annotate = QComboBox()
        self._win_annotate.addItem("字幕条（整段译，窗口外侧不遮挡）", False)
        self._win_annotate.addItem("备注（按行译，贴在原文旁）", True)
        self._win_annotate.setToolTip(
            "字幕条：译文在目标窗口下方外侧，不遮挡。"
            "备注：与区域相同，译文贴在窗口内原文旁。"
        )
        self._reg_interval = _ms_spin()
        self._reg_annotate = QComboBox()
        self._reg_annotate.addItem("字幕条（整段译，识别区外侧）", False)
        self._reg_annotate.addItem("备注（按行译，贴在原文旁）", True)
        self._reg_annotate.setToolTip(
            "字幕条=识别区下方整段译文；备注=译文贴在识别区内原文旁。"
        )

        self._win_skip_target = QCheckBox("不翻译已是目标语言的文字")
        self._win_skip_target.setToolTip(
            "仅窗口备注模式：判定为已是目标语言的行不再送模型、不叠备注标签。"
            "也可在备注条「跳过目标语」按钮切换（仅影响窗口）。"
        )
        self._reg_skip_target = QCheckBox("不翻译已是目标语言的文字")
        self._reg_skip_target.setToolTip(
            "仅区域备注模式：判定为已是目标语言的行不再送模型、不叠备注标签。"
            "也可在备注条「跳过目标语」按钮切换（仅影响区域）。"
        )

        # 备注译文颜色（窗口/区域共用）
        self._ann_color = QLineEdit()
        self._ann_color.setPlaceholderText("#00F0FF")
        self._ann_color.setMaxLength(9)
        self._ann_color.setFixedWidth(100)
        self._ann_color.setToolTip("备注模式译文颜色，#RRGGBB；窗口与区域共用")
        self._ann_color_btn = QPushButton("选色")
        self._ann_color_btn.setFixedWidth(52)
        self._ann_color_btn.clicked.connect(self._pick_annotate_color)
        self._ann_color_swatch = QLabel()
        self._ann_color_swatch.setFixedSize(22, 22)
        self._ann_color_swatch.setToolTip("当前颜色预览")
        self._ann_color.textChanged.connect(self._refresh_color_swatch)

        self._max_tokens = QSpinBox()
        self._max_tokens.setRange(64, 8192)
        self._max_tokens.setSingleStep(128)
        self._max_tokens.setToolTip("单次翻译最大生成长度；过小可能截断，过大略增延迟")

        # —— 分页内容 ——
        self._stack = QStackedWidget()
        self._stack.addWidget(self._page_general())
        self._stack.addWidget(self._page_hotkeys())
        self._stack.addWidget(self._page_window())
        self._stack.addWidget(self._page_region())
        self._stack.addWidget(self._page_advanced())
        self._stack.addWidget(self._page_log())

        # —— 侧栏 ——
        nav = QFrame()
        nav.setObjectName("sideNav")
        nav.setFixedWidth(148)
        nav_lay = QVBoxLayout(nav)
        nav_lay.setContentsMargins(6, 6, 6, 6)
        nav_lay.setSpacing(4)
        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        for i, name in enumerate(
            ("常规", "热键", "窗口翻译", "区域翻译", "高级", "日志")
        ):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if i == 0:
                btn.setChecked(True)
            self._nav_group.addButton(btn, i)
            nav_lay.addWidget(btn)
        nav_lay.addStretch()
        self._nav_group.idClicked.connect(self._stack.setCurrentIndex)

        # —— 标题栏 ——
        title_bar = QWidget()
        title_bar.setObjectName("titleBar")
        tb = QHBoxLayout(title_bar)
        tb.setContentsMargins(4, 0, 0, 0)
        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        title_lbl = QLabel("设置")
        title_lbl.setObjectName("titleLabel")
        sub = QLabel("ScreenTranslator · 本地离线")
        sub.setObjectName("subtitle")
        title_col.addWidget(title_lbl)
        title_col.addWidget(sub)
        tb.addLayout(title_col)
        tb.addStretch()
        btn_close = QPushButton("×")
        btn_close.setObjectName("closeBtn")
        btn_close.setFixedSize(32, 28)
        btn_close.setToolTip("关闭")
        btn_close.clicked.connect(self.hide)
        tb.addWidget(btn_close)

        # —— 底栏 ——
        footer = QWidget()
        footer.setObjectName("footer")
        foot = QHBoxLayout(footer)
        foot.setContentsMargins(0, 10, 0, 0)
        foot.addStretch()
        btn_save = QPushButton("保存设置")
        btn_save.setObjectName("primaryBtn")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self._save)
        foot.addWidget(btn_save)
        foot.addSpacing(4)
        foot.addWidget(CornerSizeGrip(footer), 0, Qt.AlignmentFlag.AlignBottom)

        # —— 主体 ——
        body = QHBoxLayout()
        body.setSpacing(14)
        body.addWidget(nav)
        body.addWidget(self._stack, stretch=1)

        container = QWidget()
        container.setObjectName("panel")
        inner = QVBoxLayout(container)
        inner.setContentsMargins(16, 14, 16, 12)
        inner.setSpacing(12)
        inner.addWidget(title_bar)
        inner.addLayout(body, stretch=1)
        inner.addWidget(footer)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(container)
        self.setStyleSheet(SETTINGS_STYLE)

        get_log_emitter().line.connect(
            self._append_log_line, Qt.ConnectionType.QueuedConnection
        )
        self.reload_from_cfg()
        self._load_recent_logs()

    def _wrap_scroll(self, *widgets: QWidget) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 2, 0)
        lay.setSpacing(12)
        for w in widgets:
            lay.addWidget(w)
        lay.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        scroll.setWidget(page)
        wrap = QWidget()
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.addWidget(scroll)
        return wrap

    def _annotate_color_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)
        lab = QLabel("备注译文颜色")
        lab.setFixedWidth(100)
        row.addWidget(lab)
        row.addWidget(self._ann_color_swatch)
        row.addWidget(self._ann_color)
        row.addWidget(self._ann_color_btn)
        row.addStretch(1)
        return row

    def _normalize_hex_color(self, text: str) -> str:
        s = (text or "").strip()
        if not s:
            return "#00F0FF"
        if not s.startswith("#"):
            s = "#" + s
        c = QColor(s)
        if not c.isValid():
            return "#00F0FF"
        return c.name(QColor.NameFormat.HexRgb).upper()

    def _refresh_color_swatch(self, _text: str = ""):
        hex_c = self._normalize_hex_color(self._ann_color.text())
        self._ann_color_swatch.setStyleSheet(
            f"background:{hex_c};border:1px solid #888;border-radius:3px;"
        )

    def _pick_annotate_color(self):
        cur = QColor(self._normalize_hex_color(self._ann_color.text()))
        c = QColorDialog.getColor(cur, self, "备注译文颜色")
        if c.isValid():
            self._ann_color.setText(c.name(QColor.NameFormat.HexRgb).upper())

    def _page_general(self) -> QWidget:
        card, lay = _settings_card(
            "常规",
            "全局默认目标语言；源语言自动识别。翻译结果窗内也可临时切换。",
        )
        lay.addLayout(_form_row("目标语言", self._target))
        lay.addLayout(self._annotate_color_row())
        tip = QLabel("备注译文颜色对窗口/区域备注模式均生效，保存后立即应用。")
        tip.setWordWrap(True)
        tip.setStyleSheet("color:#aaa;font-size:12px;")
        lay.addWidget(tip)
        return self._wrap_scroll(card)

    def _page_hotkeys(self) -> QWidget:
        card, lay = _settings_card(
            "全局热键",
            "点击输入框后：键盘组合键（需含 Ctrl/Alt/Shift，Esc 取消）；"
            "或直接按鼠标侧键（侧键1=后退 / 侧键2=前进，也可 Ctrl+侧键）。",
        )
        lay.addLayout(_form_row("截屏翻译", self._hk_shot))
        lay.addLayout(_form_row("划词翻译", self._hk_word))
        lay.addLayout(_form_row("截图取字", self._hk_ocr))
        lay.addLayout(_form_row("窗口持续", self._hk_win))
        lay.addLayout(_form_row("区域实时", self._hk_region))
        return self._wrap_scroll(card)

    def _page_window(self) -> QWidget:
        card, lay = _settings_card(
            "窗口持续翻译",
            "字幕条显示在目标窗口外侧不遮挡；备注按行贴在原文旁。",
        )
        lay.addLayout(_form_row("监视间隔", self._win_interval))
        lay.addLayout(_form_row("显示模式", self._win_annotate))
        tip_card, tip_lay = _settings_card(
            "备注选项",
            "仅窗口备注模式生效，与区域设置互不影响。",
        )
        tip_lay.addWidget(self._win_skip_target)
        return self._wrap_scroll(card, tip_card)

    def _page_region(self) -> QWidget:
        card, lay = _settings_card(
            "区域实时翻译",
            "识别框可拖顶栏移动、拖边角缩放；点「固定」锁定。",
        )
        lay.addLayout(_form_row("监视间隔", self._reg_interval))
        lay.addLayout(_form_row("显示模式", self._reg_annotate))
        tip_card, tip_lay = _settings_card(
            "备注选项",
            "仅区域备注模式生效，与窗口设置互不影响。",
        )
        tip_lay.addWidget(self._reg_skip_target)
        return self._wrap_scroll(card, tip_card)

    def _page_advanced(self) -> QWidget:
        card, lay = _settings_card(
            "模型与生成",
            "max_tokens 为单次翻译生成上限；过小可能截断，过大略增延迟。",
        )
        lay.addLayout(_form_row("max_tokens", self._max_tokens))
        return self._wrap_scroll(card)

    def _page_log(self) -> QWidget:
        card, lay = _settings_card(
            "运行日志",
            f"文件：{LOG_PATH.name} · 清空显示不会删除磁盘日志。",
        )
        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMaximumBlockCount(2000)
        self._log_view.setPlaceholderText("运行日志将显示在这里…")
        self._log_view.setMinimumHeight(280)
        self._log_view.verticalScrollBar().valueChanged.connect(self._on_log_scroll)
        bar = QHBoxLayout()
        btn_bottom = QPushButton("滚到底")
        btn_bottom.setObjectName("ghostBtn")
        btn_bottom.clicked.connect(self._scroll_log_bottom)
        btn_clear = QPushButton("清空显示")
        btn_clear.setObjectName("ghostBtn")
        btn_clear.clicked.connect(self._log_view.clear)
        btn_open = QPushButton("打开日志文件")
        btn_open.setObjectName("ghostBtn")
        btn_open.clicked.connect(self._open_log_file)
        bar.addWidget(btn_bottom)
        bar.addWidget(btn_clear)
        bar.addWidget(btn_open)
        bar.addStretch()
        lay.addLayout(bar)
        lay.addWidget(self._log_view, stretch=1)
        # 日志页不包 scroll，避免双滚动
        page = QWidget()
        pl = QVBoxLayout(page)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.addWidget(card)
        return page

    def showEvent(self, event):
        # 每次打开都从当前 cfg 刷新（监视中改模式/翻译窗改语言会写 cfg）
        self.reload_from_cfg()
        self._load_recent_logs()
        super().showEvent(event)

    def _load_recent_logs(self):
        """用内存环 + 文件尾填充面板（避免重复连接时丢历史）。"""
        lines = recent_lines(500)
        self._log_view.setPlainText("\n".join(lines))
        self._scroll_log_bottom()

    def _append_log_line(self, line: str):
        self._log_view.appendPlainText(line)
        if self._log_auto_scroll:
            self._scroll_log_bottom()

    def _scroll_log_bottom(self):
        self._log_auto_scroll = True
        bar = self._log_view.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _on_log_scroll(self, value: int):
        bar = self._log_view.verticalScrollBar()
        # 距底部超过一行高则认为用户在翻历史
        self._log_auto_scroll = value >= bar.maximum() - 4

    def _open_log_file(self):
        try:
            LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            if not LOG_PATH.exists():
                LOG_PATH.write_text("", encoding="utf-8")
            import os

            os.startfile(str(LOG_PATH))  # type: ignore[attr-defined]
        except Exception as e:
            topmost_message(
                "information", "日志", f"路径：\n{LOG_PATH}\n\n打开失败：{e}", parent=self
            )

    def reload_from_cfg(self):
        cfg = self._cfg
        self._target.setCurrentText(cfg.get("target_language", "简体中文"))
        self._hk_shot.set_value(cfg["hotkey_screenshot"])
        self._hk_word.set_value(cfg["hotkey_word"])
        self._hk_win.set_value(cfg["hotkey_window"])
        self._hk_ocr.set_value(cfg["hotkey_silent_ocr"])
        self._hk_region.set_value(cfg["hotkey_region_watch"])
        self._win_interval.setValue(int(cfg.get("window_watch_interval_ms", 800)))
        self._win_annotate.setCurrentIndex(
            1 if cfg.get("window_watch_annotate") else 0
        )
        self._reg_interval.setValue(int(cfg.get("region_watch_interval_ms", 800)))
        self._reg_annotate.setCurrentIndex(
            1 if cfg.get("region_watch_annotate") else 0
        )
        self._win_skip_target.setChecked(
            bool(cfg.get("window_annotate_skip_target_lang"))
        )
        self._reg_skip_target.setChecked(
            bool(cfg.get("region_annotate_skip_target_lang"))
        )
        self._ann_color.setText(
            self._normalize_hex_color(str(cfg.get("annotate_text_color", "#00F0FF")))
        )
        self._refresh_color_swatch()
        self._max_tokens.setValue(int(cfg.get("max_tokens", 512)))

    def _save(self):
        from ..hotkeys import find_hotkey_conflicts

        draft = {
            "target_language": self._target.currentText(),
            "hotkey_screenshot": self._hk_shot.value,
            "hotkey_word": self._hk_word.value,
            "hotkey_window": self._hk_win.value,
            "hotkey_silent_ocr": self._hk_ocr.value,
            "hotkey_region_watch": self._hk_region.value,
            "window_watch_interval_ms": self._win_interval.value(),
            "window_watch_annotate": self._win_annotate.currentData(),
            "window_annotate_skip_target_lang": self._win_skip_target.isChecked(),
            "region_watch_interval_ms": self._reg_interval.value(),
            "region_watch_annotate": self._reg_annotate.currentData(),
            "region_annotate_skip_target_lang": self._reg_skip_target.isChecked(),
            "annotate_text_color": self._normalize_hex_color(self._ann_color.text()),
            "max_tokens": self._max_tokens.value(),
        }
        conflicts = find_hotkey_conflicts({**self._cfg, **draft})
        if conflicts:
            topmost_message(
                "warning",
                "热键冲突",
                "以下热键重复，请修改后再保存：\n\n" + "\n".join(conflicts),
                parent=self,
            )
            return
        self._cfg.update(draft)
        # 去掉已拆分的旧共用键，避免下次误读
        self._cfg.pop("annotate_skip_target_lang", None)
        config.save(self._cfg)
        if self._on_saved:
            self._on_saved()
        # 轻量 toast：无模态、不必点确定；在原设置窗中心闪一下
        geo = self.frameGeometry()
        self.hide()
        show_toast("设置已保存", at_rect=geo, msec=1500)


class HistoryWindow(_DraggableMixin, QWidget):
    """翻译历史（最多 50 条）。双击一行在翻译窗口打开。

    视觉与截图/划词翻译结果窗一致。
    """

    def __init__(self, storage, on_open=None):
        super().__init__()
        self.setWindowTitle("翻译历史")
        apply_frameless_float(self)
        self.resize(640, 420)
        self.setMinimumSize(400, 260)
        ensure_stays_on_top(self)
        self._storage = storage
        # on_open(source, translation) → 通常送入翻译窗口
        self._on_open = on_open

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["原文", "译文"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setColumnWidth(0, 280)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.cellDoubleClicked.connect(self._on_double_click)

        tip = QLabel("双击一行可在翻译窗口中打开")

        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(4, 2, 2, 2)
        title_lbl = QLabel("翻译历史")
        title_lbl.setStyleSheet("font-size:14px;font-weight:600;")
        btn_close = QPushButton("×")
        btn_close.setFixedWidth(28)
        btn_close.clicked.connect(self.hide)
        title_bar.addWidget(title_lbl)
        title_bar.addStretch()
        title_bar.addWidget(btn_close)

        container = QWidget()
        container.setObjectName("panel")
        inner = QVBoxLayout(container)
        inner.setContentsMargins(12, 10, 12, 10)
        inner.setSpacing(8)
        inner.addLayout(title_bar)
        inner.addWidget(self._table, stretch=1)
        inner.addWidget(tip)
        grip_row = QHBoxLayout()
        grip_row.setContentsMargins(0, 0, 0, 0)
        grip_row.addStretch()
        grip_row.addWidget(CornerSizeGrip(container))
        inner.addLayout(grip_row)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(container)
        self.setStyleSheet(FLOAT_PANEL_STYLE)

    def showEvent(self, event):
        rows = [(r[1], r[2]) for r in self._storage.recent_history()]
        self._table.setRowCount(len(rows))
        for r, (src, dst) in enumerate(rows):
            self._table.setItem(r, 0, QTableWidgetItem(src))
            self._table.setItem(r, 1, QTableWidgetItem(dst))
        super().showEvent(event)

    def _on_double_click(self, row: int, _column: int):
        src_item = self._table.item(row, 0)
        dst_item = self._table.item(row, 1)
        if not src_item or not self._on_open:
            return
        source = src_item.text()
        translation = dst_item.text() if dst_item else ""
        self._on_open(source, translation)


class _TranslateWorker(QThread):
    """翻译面板的后台请求线程，避免阻塞 UI。"""

    done = Signal(str)
    failed = Signal(str)

    def __init__(self, translator, text: str, target: str, parent=None):
        super().__init__(parent)
        self._translator = translator
        self._text = text
        self._target = target

    def run(self):
        try:
            self.done.emit(self._translator.translate(self._text, self._target))
        except Exception as e:
            self.failed.emit(str(e))


class InputTranslateWindow(_DraggableMixin, QWidget):
    """统一翻译窗口：手动输入翻译，也承接划词/截屏的结果显示。

    源语言自动识别，目标语言窗口内直接切换（切换后自动重翻当前内容）。
    无边框半透明（与实时字幕同款），可拖动；点"固定"锁定位置防误拖。
    """

    def __init__(self, translator, cfg: dict, ensure_server=None):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(460, 320)
        self.setMinimumSize(320, 220)
        self._translator = translator
        self._cfg = cfg
        self._ensure_server = ensure_server  # 可选 () -> bool
        self._pinned = False
        self._worker: _TranslateWorker | None = None
        self._block_lang_signal = False

        self._input = QTextEdit()
        self._input.setPlaceholderText("输入任意语言的文本，或用划词/截屏热键送入…")
        self._output = QTextEdit(readOnly=True)
        self._output.setPlaceholderText("译文")

        self._lang = QComboBox()
        self._lang.addItems(LANGUAGES)
        self._lang.setCurrentText(cfg.get("target_language", "简体中文"))
        # 切语言：写回 cfg（持续监视共用）并自动重翻
        self._lang.currentTextChanged.connect(self._on_lang_changed)

        self._btn_pin = QPushButton("固定")
        self._btn_pin.setCheckable(True)
        self._btn_pin.toggled.connect(self._toggle_pin)
        btn_go = QPushButton("翻译")
        btn_copy = QPushButton("复制")
        btn_close = QPushButton("×")
        btn_close.setFixedWidth(28)
        btn_go.clicked.connect(self._go)
        btn_copy.clicked.connect(self._copy)
        btn_close.clicked.connect(self.hide)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("译成："))
        bar.addWidget(self._lang)
        bar.addStretch()
        bar.addWidget(btn_go)
        bar.addWidget(btn_copy)
        bar.addWidget(self._btn_pin)
        bar.addWidget(btn_close)

        # 内容容器：与实时字幕条相同的半透明底
        container = QWidget()
        container.setObjectName("panel")
        inner = QVBoxLayout(container)
        inner.addLayout(bar)
        inner.addWidget(self._input)
        inner.addWidget(self._output)
        # 右下角拖拽调整窗口大小
        grip_row = QHBoxLayout()
        grip_row.setContentsMargins(0, 0, 0, 0)
        grip_row.addStretch()
        grip_row.addWidget(QSizeGrip(container))
        inner.addLayout(grip_row)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(container)

        self.setStyleSheet(
            "#panel{background:rgba(0,0,0,175);border-radius:8px;}"
            "QLabel{color:#fff;}"
            "QTextEdit{background:rgba(255,255,255,28);color:#fff;"
            "border:1px solid rgba(255,255,255,60);border-radius:4px;}"
            "QComboBox{background:rgba(255,255,255,28);color:#fff;"
            "border:1px solid rgba(255,255,255,60);border-radius:4px;padding:2px 6px;}"
            "QComboBox QAbstractItemView{background:#2b2b2b;color:#eee;}"
            "QPushButton{background:rgba(255,255,255,40);color:#fff;"
            "border:none;border-radius:4px;padding:4px 10px;}"
            "QPushButton:checked{background:rgba(0,150,255,150);}"
        )

    def _toggle_pin(self, checked: bool):
        self._pinned = checked
        self._btn_pin.setText("已固定" if checked else "固定")

    def _on_lang_changed(self, lang: str):
        if self._block_lang_signal:
            return
        self._cfg["target_language"] = lang
        config.save(self._cfg)
        self._go()

    def sync_language_from_cfg(self):
        """设置页改语言后同步下拉（不触发重翻）。"""
        lang = self._cfg.get("target_language", "简体中文")
        if self._lang.currentText() == lang:
            return
        self._block_lang_signal = True
        self._lang.setCurrentText(lang)
        self._block_lang_signal = False

    def mouseMoveEvent(self, event):
        # 固定后不可拖动
        if not self._pinned:
            super().mouseMoveEvent(event)

    @property
    def target_language(self) -> str:
        return self._lang.currentText()

    def show_result(self, source: str, translation: str, near_x: int = None,
                    near_y: int = None):
        """划词/截屏结果送入本窗口。未固定时移动到触发位置附近（支持多屏）。"""
        self._input.setPlainText(source)
        self._output.setPlainText(translation)
        if not self._pinned and near_x is not None and near_y is not None:
            from PySide6.QtCore import QPoint

            pt = QPoint(int(near_x), int(near_y))
            screen = QGuiApplication.screenAt(pt)
            if screen is None:
                screen = QGuiApplication.primaryScreen()
            geo = screen.availableGeometry()
            x = min(max(near_x, geo.left()), geo.right() - self.width())
            y = min(max(near_y, geo.top()), geo.bottom() - self.height())
            self.move(x, y)
        raise_to_front(self, activate=True)

    def _go(self):
        text = self._input.toPlainText().strip()
        if not text:
            return
        if self._worker and self._worker.isRunning():
            return  # 上一个请求还没回来，不叠加
        if self._ensure_server is not None and not self._ensure_server():
            self._output.setPlainText("翻译服务未就绪")
            return
        self._output.setPlainText("翻译中…")
        self._worker = _TranslateWorker(
            self._translator, text, self._lang.currentText(), parent=self
        )
        self._worker.done.connect(self._output.setPlainText)
        self._worker.failed.connect(
            lambda e: self._output.setPlainText(f"翻译失败：{e}")
        )
        self._worker.start()

    def _copy(self):
        QApplication.clipboard().setText(self._output.toPlainText())
