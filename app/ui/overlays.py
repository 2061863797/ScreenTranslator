# -*- coding: utf-8 -*-
"""翻译结果显示组件：

- _DraggableMixin：可拖动窗口的通用混入（翻译窗口使用）
- SubtitleBar：持续翻译的悬浮字幕条（文字层鼠标穿透 + 独立控制小条）
- AnnotationOverlay：持续翻译的备注模式（译文贴在原文旁，鼠标穿透）
- RegionWatchFrame：区域翻译识别框（可拖动 / 固定）
"""

import ctypes

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen, QShowEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .theme import (
    ACCENT_QCOLOR,
    BORDER_QCOLOR,
    CTRL_STYLE,
    FIELD_QCOLOR,
    MUTED_QCOLOR,
    PANEL_QCOLOR,
    SCROLLBAR_STYLE,
    TEXT_QCOLOR,
    paint_size_grip,
)

_FLAGS_TOP = (
    Qt.WindowType.FramelessWindowHint
    | Qt.WindowType.WindowStaysOnTopHint
    | Qt.WindowType.Tool
)

# Win10 2004+：窗口对人眼可见，但被 BitBlt/mss 等屏幕捕获排除
# 这样区域 OCR 不会扫到浮层，也不必每轮 hide/show（那会造成闪烁）
_WDA_EXCLUDEFROMCAPTURE = 0x00000011


def _exclude_from_capture(widget: QWidget) -> None:
    """标记窗口不参与屏幕捕获（失败则静默忽略，旧系统无此 API）。"""
    try:
        hwnd = int(widget.winId())
        if hwnd:
            ctypes.windll.user32.SetWindowDisplayAffinity(
                hwnd, _WDA_EXCLUDEFROMCAPTURE
            )
    except Exception:
        pass


def _show_once(widget: QWidget) -> None:
    """仅在不可见时 show，避免反复 show/raise 导致闪烁。"""
    if widget is not None and not widget.isVisible():
        widget.show()


def _set_geo_if_changed(widget: QWidget, x: int, y: int, w: int, h: int) -> bool:
    """几何未变则跳过 setGeometry（减少 DWM 重布局闪）。返回是否改过。"""
    g = widget.geometry()
    if g.x() == x and g.y() == y and g.width() == w and g.height() == h:
        return False
    widget.setGeometry(x, y, w, h)
    return True


def _move_if_changed(widget: QWidget, x: int, y: int) -> bool:
    if widget.x() == x and widget.y() == y:
        return False
    widget.move(x, y)
    return True

class _CaptureExcludedMixin:
    """顶层浮层混入：显示时排除屏幕捕获，避免区域 OCR 读到自己。"""

    def showEvent(self, event: QShowEvent):
        super().showEvent(event)
        _exclude_from_capture(self)


class _DraggableMixin:
    """按住窗口空白处拖动。"""

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            event.buttons() & Qt.MouseButton.LeftButton
            and getattr(self, "_drag_offset", None) is not None
        ):
            self.move(event.globalPosition().toPoint() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
        super().mouseReleaseEvent(event)


class SubtitleBar(_CaptureExcludedMixin, QWidget):
    """持续翻译的悬浮字幕条：

    - 文字层：鼠标穿透，固定尺寸，长文在框内滚动（不随译文自动改大小）
    - 右侧滚动条：独立可点窗口
    - 右下角缩放把手：独立窗口，grabMouse 保证拖出后仍跟手
    - 控制小条：跟随 / 自由 / 固定 / 备注 / 关闭
    """

    mode_changed = Signal(str)  # follow / free / pinned
    stop_requested = Signal()   # 用户点关闭，停止持续翻译
    switch_to_annotate = Signal()  # 运行中切换到备注模式

    _PAD = 10
    _SCROLL_W = 14
    _GRIP = 18
    _MIN_W = 200
    _MIN_H = 80
    _DEFAULT_H = 100

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.mode = "follow"
        self._interactive = False
        self._user_size: tuple[int, int] | None = None
        self._text = ""
        self._scroll = 0
        self._content_h = 0
        self._font = QFont()
        self._font.setPixelSize(16)
        # 译文层始终点击穿透
        self.setWindowFlags(_FLAGS_TOP | Qt.WindowType.WindowTransparentForInput)

        self._ctrl = _SubtitleCtrl(self)
        self._vscroll = _SubtitleVScroll(self)
        self._grip = _SubtitleResizeGrip(self)
        self.resize(self._MIN_W, self._DEFAULT_H)

    def set_interactive(self, on: bool):
        """字幕模式：显示右下角缩放；译文层始终穿透。"""
        on = bool(on)
        if on == self._interactive:
            return
        self._interactive = on
        if self.isVisible():
            self._place_chrome()
            self._show_chrome()
            _exclude_from_capture(self)

    def set_mode(self, mode: str, emit: bool = False):
        self.mode = mode
        self._ctrl.sync_checked(mode)
        if emit:
            self.mode_changed.emit(mode)

    def attach_below(
        self,
        win_rect: tuple[int, int, int, int],
        *,
        outside: bool = False,
    ):
        """跟随模式下吸附到目标下缘；其他模式不动。框体大小不随译文变。"""
        if self.mode != "follow":
            return
        x, y, w, h = win_rect
        if self._user_size:
            bar_w, bar_h = self._user_size
        else:
            bar_w, bar_h = max(w, 280), self._DEFAULT_H
        if outside:
            nx, ny, nw, nh = x, y + h + 4, bar_w, bar_h
        else:
            nx, ny, nw, nh = x, y + h - bar_h - 10, max(w, 200), bar_h
        changed = _set_geo_if_changed(self, nx, ny, nw, nh)
        if changed:
            self._reflow_text()
        self._place_chrome()
        if self.isVisible():
            self._show_chrome()

    def move_to(self, x: int, y: int):
        """自由模式下由控制条拖动调用。"""
        _move_if_changed(self, x, y)
        self._place_chrome()
        if self.isVisible():
            self._show_chrome()

    def resize_to(self, w: int, h: int):
        """右下角把手缩放：改框大小并记住，不随译文自动改。"""
        w = max(self._MIN_W, int(w))
        h = max(self._MIN_H, int(h))
        if self.width() == w and self.height() == h and self._user_size == (w, h):
            return
        self.setFixedSize(w, h)
        self._user_size = (w, h)
        self._reflow_text()
        self._place_chrome()
        if self.isVisible():
            self._show_chrome()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 不用 setFixedSize 时仍同步（attach_below 用 setGeometry）
        if self.isVisible():
            self._reflow_text()
            self._place_chrome()
            self._show_chrome()

    def setGeometry(self, *args):
        # 兼容 QRect / x,y,w,h；跟随后不锁死 fixed，方便拖目标窗改默认宽
        super().setGeometry(*args)
        if self._user_size is not None:
            # 用户缩放过：强制保持记忆尺寸（位置可随 attach 变）
            g = self.geometry()
            uw, uh = self._user_size
            if g.width() != uw or g.height() != uh:
                super().setGeometry(g.x(), g.y(), uw, uh)

    def _text_rect_size(self) -> QSize:
        """正文可用区域（为滚动条留出右边距）。"""
        return QSize(
            max(40, self.width() - self._PAD * 2 - self._SCROLL_W),
            max(20, self.height() - self._PAD * 2),
        )

    def _reflow_text(self):
        """按当前框宽计算内容高度，更新滚动范围；不改框体尺寸。"""
        tr = self._text_rect_size()
        if not self._text:
            self._content_h = 0
            self._scroll = 0
            self._vscroll.set_range(0, 0, tr.height())
            self.update()
            return
        # 用 font metrics 估算换行后高度（与 paint 同一套 flags，避免估矮导致滑条误关）
        fm = QFontMetrics(self._font)
        flags = int(
            Qt.TextFlag.TextWordWrap
            | Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignTop
        )
        br = fm.boundingRect(0, 0, max(1, tr.width()), 10_000_000, flags, self._text)
        # 略留余量：部分字体/抗锯齿下 boundingRect 会偏矮
        self._content_h = max(br.height() + 4, fm.height())
        max_scroll = max(0, self._content_h - tr.height())
        self._scroll = min(self._scroll, max_scroll)
        self._vscroll.set_range(0, max_scroll, tr.height())
        self._vscroll.set_value(self._scroll)
        self.update()

    def set_scroll(self, value: int):
        tr = self._text_rect_size()
        max_scroll = max(0, self._content_h - tr.height())
        self._scroll = max(0, min(int(value), max_scroll))
        # 外部滑块可能已同步，避免回写死循环；仅刷新画面
        self.update()

    def _place_chrome(self):
        """控制条 / 滚动条 / 缩放把手贴在文字层周围（几何未变则不动）。"""
        g = self.geometry()
        self._ctrl.adjustSize()
        _move_if_changed(
            self._ctrl,
            g.right() - self._ctrl.width(),
            g.top() - self._ctrl.height() - 2,
        )
        sw = max(self._SCROLL_W, 16)
        _set_geo_if_changed(
            self._vscroll,
            g.right() - sw + 1,
            g.top(),
            sw,
            max(self._MIN_H, g.height()),
        )
        _move_if_changed(
            self._grip,
            g.right() - self._GRIP + 2,
            g.bottom() - self._GRIP + 2,
        )

    def _show_chrome(self):
        """统一显示附属窗：仅在需要时 show，避免每轮 raise 闪烁。"""
        if not self.isVisible():
            return
        _show_once(self._ctrl)
        if self._text:
            _show_once(self._vscroll)
            need = self._content_h > self._text_rect_size().height()
            self._vscroll.set_enabled(need)
            if not getattr(self._vscroll, "_capture_excluded", False):
                _exclude_from_capture(self._vscroll)
                self._vscroll._capture_excluded = True  # type: ignore[attr-defined]
        else:
            if self._vscroll.isVisible():
                self._vscroll.hide()
        if self._interactive:
            _show_once(self._grip)
            if not getattr(self._grip, "_capture_excluded", False):
                _exclude_from_capture(self._grip)
                self._grip._capture_excluded = True  # type: ignore[attr-defined]
        else:
            if self._grip.isVisible():
                self._grip.hide()
        if not getattr(self._ctrl, "_capture_excluded", False):
            _exclude_from_capture(self._ctrl)
            self._ctrl._capture_excluded = True  # type: ignore[attr-defined]

    def set_text(self, text: str):
        """更新译文：框大小不变，过长用滚动条。已显示时只重绘，不反复 raise。"""
        text = text or ""
        same = text == self._text and self.isVisible()
        self._text = text
        # 新译文从顶部看起（同文案刷新则保持滚动位置）
        if not same:
            self._scroll = 0
        first = not self.isVisible()
        if first:
            if self._user_size:
                self.resize(*self._user_size)
            elif self.width() < self._MIN_W:
                self.resize(max(self.width(), 280), self._DEFAULT_H)
            self.show()
            _exclude_from_capture(self)
        self._reflow_text()
        self._place_chrome()
        self._show_chrome()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(PANEL_QCOLOR)
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 8, 8)

        if not self._text:
            return
        tr = self._text_rect_size()
        text_rect = self.rect().adjusted(self._PAD, self._PAD, -self._PAD - self._SCROLL_W, -self._PAD)
        painter.setFont(self._font)
        painter.setPen(TEXT_QCOLOR)
        painter.setClipRect(text_rect)
        # 内容整体上移实现滚动
        draw_rect = text_rect.translated(0, -self._scroll)
        draw_rect.setHeight(max(self._content_h + self._PAD, text_rect.height()))
        painter.drawText(
            draw_rect,
            int(Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop),
            self._text,
        )

    def hide(self):
        self._ctrl.hide()
        self._vscroll.hide()
        self._grip.hide()
        super().hide()


class _SubtitleVScroll(_CaptureExcludedMixin, QWidget):
    """字幕条右侧纵向滚动条（独立顶层窗，可点）。

    显隐只由 SubtitleBar._show_chrome 控制；set_range 绝不 hide，
    避免跟随/缩放路径漏 show 导致滑条突然消失。
    """

    def __init__(self, bar: SubtitleBar):
        super().__init__()
        self.setWindowFlags(_FLAGS_TOP)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._bar = bar
        self._bar_widget = QScrollBar(Qt.Orientation.Vertical)
        # 与翻译结果窗同系：深底 + 浅色滑块（非高饱和蓝）
        self._bar_widget.setStyleSheet(SCROLLBAR_STYLE)
        self._bar_widget.valueChanged.connect(self._bar.set_scroll)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(1, 2, 1, 2)
        lay.addWidget(self._bar_widget)

    def set_range(self, mn: int, mx: int, page: int):
        self._bar_widget.blockSignals(True)
        self._bar_widget.setRange(mn, max(mn, mx))
        self._bar_widget.setPageStep(max(10, page))
        self._bar_widget.setSingleStep(16)
        self._bar_widget.blockSignals(False)
        # 不在这里 hide —— 显隐交给 _show_chrome

    def set_value(self, v: int):
        self._bar_widget.blockSignals(True)
        self._bar_widget.setValue(int(v))
        self._bar_widget.blockSignals(False)

    def set_enabled(self, on: bool):
        self._bar_widget.setEnabled(bool(on))


class _SubtitleResizeGrip(_CaptureExcludedMixin, QWidget):
    """右下角缩放把手：独立窗口 + grabMouse，拖出按钮外仍跟手。"""

    def __init__(self, bar: SubtitleBar):
        super().__init__()
        self.setWindowFlags(_FLAGS_TOP)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(bar._GRIP, bar._GRIP)
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self.setToolTip("拖动缩放译文框")
        self._bar = bar
        self._origin: tuple | None = None

    def paintEvent(self, event):
        # 与翻译窗右下角 QSizeGrip 同形态：三道白斜线，深色底上可见
        p = QPainter(self)
        paint_size_grip(p, self.width(), self.height())

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._origin = (
            event.globalPosition().toPoint(),
            self._bar.width(),
            self._bar.height(),
        )
        self.grabMouse()
        event.accept()

    def mouseMoveEvent(self, event):
        if self._origin is None or not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        g0, w0, h0 = self._origin
        d = event.globalPosition().toPoint() - g0
        self._bar.resize_to(w0 + d.x(), h0 + d.y())
        event.accept()

    def mouseReleaseEvent(self, event):
        if self._origin is not None:
            self._origin = None
            self.releaseMouse()
            event.accept()


class _SubtitleCtrl(_CaptureExcludedMixin, QWidget):
    """字幕条控制小条：拖动把手 + 模式按钮 + 关闭（可点）。"""

    def __init__(self, bar: SubtitleBar):
        super().__init__()
        self.setWindowFlags(_FLAGS_TOP)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._bar = bar
        self._drag_offset = None

        self._btns: dict[str, QPushButton] = {}
        container = QWidget()
        container.setObjectName("ctrl")
        lay = QHBoxLayout(container)
        lay.setContentsMargins(6, 3, 6, 3)
        lay.setSpacing(4)
        handle = QLabel("⠿")
        handle.setStyleSheet(
            "color:#fff;font-size:14px;padding:0 2px;background:transparent;"
        )
        handle.setToolTip("自由模式下拖动移动字幕")
        lay.addWidget(handle)
        for key, text in [
            ("follow", "跟随"), ("free", "自由"), ("pinned", "固定"),
        ]:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setFixedHeight(20)
            btn.clicked.connect(
                lambda _=False, k=key: self._bar.set_mode(k, emit=True)
            )
            self._btns[key] = btn
            lay.addWidget(btn)
        btn_ann = QPushButton("备注")
        btn_ann.setFixedHeight(20)
        btn_ann.setToolTip("切换为备注模式（贴在原文旁）")
        btn_ann.clicked.connect(self._bar.switch_to_annotate.emit)
        lay.addWidget(btn_ann)
        btn_close = QPushButton("关闭")
        btn_close.setFixedHeight(20)
        btn_close.setToolTip("停止持续翻译并关闭字幕")
        btn_close.clicked.connect(self._bar.stop_requested.emit)
        lay.addWidget(btn_close)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(container)
        self.setStyleSheet(CTRL_STYLE)
        self.sync_checked(bar.mode)

    def sync_checked(self, mode: str):
        for k, btn in self._btns.items():
            btn.setChecked(k == mode)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self._bar.pos()

    def mouseMoveEvent(self, event):
        if (
            self._bar.mode == "free"
            and self._drag_offset is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            p = event.globalPosition().toPoint() - self._drag_offset
            self._bar.move_to(p.x(), p.y())

    def mouseReleaseEvent(self, event):
        self._drag_offset = None


class RegionWatchFrame(_CaptureExcludedMixin, QWidget):
    """区域翻译专用：识别范围框。

    - 蓝色外框标出 OCR 区域（内容区）
    - 顶栏在识别区上方：拖动移动、固定/解锁
    - 未固定时可拖边/角缩放识别区（类似窗口缩放）
    - 已排除屏幕捕获
    """

    region_moved = Signal(int, int, int, int)

    _BAR_H = 26
    _PIN_W = 64
    _EDGE = 10
    _MIN_W = 100
    _MIN_H = 60

    def __init__(self):
        super().__init__()
        self.setWindowFlags(_FLAGS_TOP)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self._pinned = False
        self._drag_offset = None
        self._resize_edge: str | None = None  # l/r/t/b/tl/tr/bl/br
        self._resize_origin = None  # (global_pos, geometry)

    def show_region(self, rect: tuple[int, int, int, int], *, pinned: bool = False):
        """显示框：rect 为 OCR 识别区；顶栏画在其上方。"""
        x, y, w, h = rect
        if w <= 0 or h <= 0:
            self.hide()
            return
        self._pinned = bool(pinned)
        self._drag_offset = None
        self._resize_edge = None
        # 整窗 = 顶栏 + 识别区
        nx = x
        ny = y - self._BAR_H
        nw = max(w, self._MIN_W)
        nh = max(h, self._MIN_H) + self._BAR_H
        first = not self.isVisible()
        _set_geo_if_changed(self, nx, ny, nw, nh)
        _show_once(self)
        if first:
            _exclude_from_capture(self)
        self.update()

    def content_rect(self) -> tuple[int, int, int, int]:
        """当前 OCR 识别区（不含顶栏）。"""
        g = self.geometry()
        return g.x(), g.y() + self._BAR_H, g.width(), max(0, g.height() - self._BAR_H)

    @property
    def pinned(self) -> bool:
        return self._pinned

    def hide_frame(self):
        self._drag_offset = None
        self._resize_edge = None
        self._pinned = False
        self.hide()

    def _toggle_pin(self):
        self._pinned = not self._pinned
        self._drag_offset = None
        self._resize_edge = None
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def _pin_hit(self):
        from PySide6.QtCore import QRect

        return QRect(
            max(0, self.width() - self._PIN_W - 4),
            2,
            self._PIN_W,
            self._BAR_H - 4,
        )

    def _hit_resize_edge(self, pos) -> str | None:
        """识别区边缘/角命中；顶栏不参与缩放。"""
        if pos.y() < self._BAR_H:
            return None
        e = self._EDGE
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        left = x <= e
        right = x >= w - e
        top = self._BAR_H <= y <= self._BAR_H + e
        bottom = y >= h - e
        if top and left:
            return "tl"
        if top and right:
            return "tr"
        if bottom and left:
            return "bl"
        if bottom and right:
            return "br"
        if left:
            return "l"
        if right:
            return "r"
        if top:
            return "t"
        if bottom:
            return "b"
        return None

    def _cursor_for_edge(self, edge: str | None):
        m = {
            "l": Qt.CursorShape.SizeHorCursor,
            "r": Qt.CursorShape.SizeHorCursor,
            "t": Qt.CursorShape.SizeVerCursor,
            "b": Qt.CursorShape.SizeVerCursor,
            "tl": Qt.CursorShape.SizeFDiagCursor,
            "br": Qt.CursorShape.SizeFDiagCursor,
            "tr": Qt.CursorShape.SizeBDiagCursor,
            "bl": Qt.CursorShape.SizeBDiagCursor,
        }
        return m.get(edge, Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position().toPoint()
        if pos.y() <= self._BAR_H:
            pr = self._pin_hit()
            if pr.contains(pos):
                self._toggle_pin()
                event.accept()
                return
            if not self._pinned:
                self._drag_offset = event.globalPosition().toPoint() - self.pos()
                self.setCursor(Qt.CursorShape.SizeAllCursor)
                event.accept()
            return
        if not self._pinned:
            edge = self._hit_resize_edge(pos)
            if edge:
                self._resize_edge = edge
                self._resize_origin = (
                    event.globalPosition().toPoint(),
                    self.geometry(),
                )
                event.accept()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        # 悬停光标
        if self._drag_offset is None and self._resize_edge is None and not self._pinned:
            if pos.y() <= self._BAR_H:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            else:
                self.setCursor(self._cursor_for_edge(self._hit_resize_edge(pos)))

        if (
            self._drag_offset is not None
            and not self._pinned
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            p = event.globalPosition().toPoint() - self._drag_offset
            self.move(p.x(), p.y())
            self.region_moved.emit(*self.content_rect())
            event.accept()
            return

        if (
            self._resize_edge
            and self._resize_origin
            and not self._pinned
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            gpos0, geo0 = self._resize_origin
            d = event.globalPosition().toPoint() - gpos0
            x, y, w, h = geo0.x(), geo0.y(), geo0.width(), geo0.height()
            edge = self._resize_edge
            if "l" in edge:
                nw = max(self._MIN_W, w - d.x())
                x = x + (w - nw)
                w = nw
            if "r" in edge:
                w = max(self._MIN_W, w + d.x())
            if "t" in edge:
                # 顶边是识别区顶 = 整窗 y+BAR_H，缩放时动 y 且改高
                nh = max(self._MIN_H + self._BAR_H, h - d.y())
                y = y + (h - nh)
                h = nh
            if "b" in edge:
                h = max(self._MIN_H + self._BAR_H, h + d.y())
            self.setGeometry(x, y, w, h)
            self.region_moved.emit(*self.content_rect())
            self.update()
            event.accept()

    def mouseReleaseEvent(self, event):
        if self._drag_offset is not None or self._resize_edge is not None:
            self._drag_offset = None
            self._resize_edge = None
            self._resize_origin = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.region_moved.emit(*self.content_rect())
            event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        w, h = self.width(), self.height()
        # 顶栏：与翻译结果窗同系深色条
        painter.fillRect(0, 0, w, self._BAR_H, PANEL_QCOLOR)
        painter.setPen(MUTED_QCOLOR)
        if self._pinned:
            title = "已固定 · 点右侧解锁"
        else:
            title = "⠿ 拖动 · 拖边角缩放识别区"
        painter.drawText(
            8, 0, max(0, w - self._PIN_W - 16), self._BAR_H,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            title,
        )
        pr = self._pin_hit()
        painter.fillRect(
            pr, ACCENT_QCOLOR if self._pinned else FIELD_QCOLOR
        )
        painter.setPen(TEXT_QCOLOR)
        painter.drawText(
            pr, Qt.AlignmentFlag.AlignCenter,
            "已固定" if self._pinned else "固定",
        )
        # 识别区外框（浅色描边，不抢戏）
        painter.setPen(QPen(BORDER_QCOLOR, 2))
        painter.drawRect(
            1, self._BAR_H, max(0, w - 3), max(0, h - self._BAR_H - 1)
        )
        # 右下角缩放：与翻译窗同形态的三道斜线
        if not self._pinned:
            painter.save()
            painter.translate(w - 18, h - 18)
            paint_size_grip(painter, 18, 18)
            painter.restore()


class AnnotateCtrl(_CaptureExcludedMixin, QWidget):
    """备注模式控制小条：字幕 / 跳过目标语 / 关闭（可点，贴在目标外侧）。"""

    stop_requested = Signal()
    skip_target_changed = Signal(bool)  # 不翻译已是目标语言的文字
    switch_to_subtitle = Signal()  # 运行中切换到字幕条模式

    def __init__(self):
        super().__init__()
        self.setWindowFlags(_FLAGS_TOP)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        container = QWidget()
        container.setObjectName("annCtrl")
        lay = QHBoxLayout(container)
        lay.setContentsMargins(8, 3, 8, 3)
        lay.setSpacing(6)
        tip = QLabel("备注")
        lay.addWidget(tip)
        btn_sub = QPushButton("字幕")
        btn_sub.setFixedHeight(20)
        btn_sub.setToolTip("切换为字幕条模式（目标外侧）")
        btn_sub.clicked.connect(self.switch_to_subtitle.emit)
        lay.addWidget(btn_sub)
        self._btn_skip = QPushButton("跳过目标语")
        self._btn_skip.setCheckable(True)
        self._btn_skip.setFixedHeight(20)
        self._btn_skip.setToolTip(
            "开启后：已是目标语言的行不再翻译、不显示备注标签"
        )
        self._btn_skip.clicked.connect(self._on_skip_clicked)
        lay.addWidget(self._btn_skip)
        btn_close = QPushButton("关闭")
        btn_close.setFixedHeight(20)
        btn_close.setToolTip("停止持续翻译")
        btn_close.clicked.connect(self.stop_requested.emit)
        lay.addWidget(btn_close)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(container)
        self.setStyleSheet(CTRL_STYLE)

    def _on_skip_clicked(self):
        self.skip_target_changed.emit(self._btn_skip.isChecked())

    def set_skip_target(self, on: bool):
        """与配置/设置页同步，不触发 signal。"""
        on = bool(on)
        if self._btn_skip.isChecked() != on:
            self._btn_skip.blockSignals(True)
            self._btn_skip.setChecked(on)
            self._btn_skip.blockSignals(False)

    def place_above(self, win_rect: tuple[int, int, int, int]):
        """贴在目标右上角外侧，不挡内容。"""
        x, y, w, h = win_rect
        self.adjustSize()
        nx = x + max(0, w - self.width())
        ny = y - self.height() - 4
        first = not self.isVisible()
        _move_if_changed(self, nx, ny)
        _show_once(self)
        if first:
            _exclude_from_capture(self)


class AnnotationOverlay(_CaptureExcludedMixin, QWidget):
    """备注模式：每行译文贴在对应原文正下方（越界则贴上方），
    覆盖整个目标区域，鼠标完全穿透，不挡操作。

    默认布局以「对得上是哪一行」为优先，不做复杂空白搜索。
    """

    def __init__(self):
        super().__init__()
        self.setWindowFlags(_FLAGS_TOP | Qt.WindowType.WindowTransparentForInput)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        # [(box(x1,y1,x2,y2) 相对区域, 译文), ...]
        self._items: list[tuple[tuple[int, int, int, int], str]] = []
        self._text_color = QColor("#00F0FF")

    def set_text_color(self, color) -> None:
        """备注译文颜色：#RRGGBB 字符串或 QColor。"""
        c = QColor(color) if not isinstance(color, QColor) else QColor(color)
        if not c.isValid():
            c = QColor("#00F0FF")
        if c.rgb() == self._text_color.rgb() and c.alpha() == self._text_color.alpha():
            return
        self._text_color = c
        if self.isVisible():
            self.update()

    def update_geometry(self, win_rect: tuple[int, int, int, int]):
        x, y, w, h = win_rect
        if _set_geo_if_changed(self, x, y, w, h):
            self.update()

    def set_items(self, items: list[tuple[tuple[int, int, int, int], str]]):
        self._items = items or []
        first = not self.isVisible()
        _show_once(self)
        if first:
            _exclude_from_capture(self)
        self.update()

    def clear(self):
        self._items = []
        self.hide()

    def paintEvent(self, event):
        if not self._items:
            return
        painter = QPainter(self)
        font = QFont()
        font.setPixelSize(13)
        painter.setFont(font)
        fm = painter.fontMetrics()
        W, H = self.width(), self.height()
        painter.setPen(self._text_color)
        for (x1, y1, x2, y2), text in self._items:
            if not text:
                continue
            tw = fm.horizontalAdvance(text) + 10
            th = fm.height() + 4
            # 默认：贴原文正下方；下方越界则贴上方；水平对齐原文左缘
            ax = min(x1, max(0, W - tw))
            ay = y2 + 2
            if ay + th > H:
                ay = y1 - th - 2
            if ay < 0:
                ay = 0
            painter.drawText(
                ax + 5, ay, tw - 10, th,
                Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextSingleLine,
                text,
            )
