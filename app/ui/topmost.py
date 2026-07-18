# -*- coding: utf-8 -*-
"""托盘应用无主窗时，弹层容易被其它全屏/置顶窗挡住。

统一：StaysOnTop + raise + 激活 + Win32 TOPMOST/前台。
"""

from __future__ import annotations

import ctypes
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor, QGuiApplication
from PySide6.QtWidgets import QWidget

if TYPE_CHECKING:
    pass

# Win32
_HWND_TOPMOST = -1
_SWP_NOSIZE = 0x0001
_SWP_NOMOVE = 0x0002
_SWP_SHOWWINDOW = 0x0040
_SWP_NOACTIVATE = 0x0010


def ensure_stays_on_top(widget: QWidget) -> None:
    """保证带 WindowStaysOnTopHint（不改其它 flag）。"""
    flags = widget.windowFlags()
    if not (flags & Qt.WindowType.WindowStaysOnTopHint):
        widget.setWindowFlags(flags | Qt.WindowType.WindowStaysOnTopHint)


def raise_to_front(widget: QWidget, *, activate: bool = True) -> None:
    """把已有窗口提到所有普通窗口之前并尽量激活。

    已可见时避免重复 show/raise 造成闪烁；用 SetWindowPos 调 z-order。
    """
    if widget is None:
        return
    ensure_stays_on_top(widget)
    was_visible = widget.isVisible()
    if not was_visible:
        widget.show()
    if activate:
        widget.activateWindow()
    try:
        hwnd = int(widget.winId())
        if not hwnd:
            return
        # 已显示时用 NOACTIVATE 减少焦点闪；首次显示才 SHOWWINDOW
        flags = _SWP_NOMOVE | _SWP_NOSIZE
        if was_visible and not activate:
            flags |= _SWP_NOACTIVATE
        else:
            flags |= _SWP_SHOWWINDOW
        if was_visible and activate:
            # 仅调 z-order，避免 SHOWWINDOW 再闪一帧
            flags = _SWP_NOMOVE | _SWP_NOSIZE
        ctypes.windll.user32.SetWindowPos(
            hwnd,
            _HWND_TOPMOST,
            0,
            0,
            0,
            0,
            flags,
        )
        if activate:
            try:
                ctypes.windll.user32.AllowSetForegroundWindow(-1)  # ASFW_ANY
            except Exception:
                pass
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            ctypes.windll.user32.BringWindowToTop(hwnd)
    except Exception:
        pass


def center_on_cursor_screen(widget: QWidget) -> None:
    """把窗口放到鼠标所在屏幕中央，避免弹到另一块看不见的屏上。"""
    try:
        screen = QGuiApplication.screenAt(QCursor.pos())
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        fg = widget.frameGeometry()
        if fg.width() <= 0 or fg.height() <= 0:
            widget.adjustSize()
            fg = widget.frameGeometry()
        x = geo.x() + max(0, (geo.width() - fg.width()) // 2)
        y = geo.y() + max(0, (geo.height() - fg.height()) // 2)
        widget.move(x, y)
    except Exception:
        pass


def topmost_message(
    icon: str,
    title: str,
    text: str,
    parent: QWidget | None = None,
) -> int:
    """置顶消息框（critical / warning / information）。"""
    from PySide6.QtWidgets import QMessageBox

    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    kind = {
        "critical": QMessageBox.Icon.Critical,
        "warning": QMessageBox.Icon.Warning,
        "information": QMessageBox.Icon.Information,
        "question": QMessageBox.Icon.Question,
    }.get(icon, QMessageBox.Icon.Information)
    box.setIcon(kind)
    box.setWindowFlags(
        box.windowFlags()
        | Qt.WindowType.WindowStaysOnTopHint
        | Qt.WindowType.Dialog
    )
    center_on_cursor_screen(box)
    raise_to_front(box, activate=True)
    return box.exec()


def show_toast(
    text: str,
    *,
    parent: QWidget | None = None,
    msec: int = 1600,
    near: QWidget | None = None,
    at_rect=None,
) -> None:
    """轻量成功提示：无模态、无按钮、自动消失（适合「设置已保存」）。

    at_rect: 可选 QRect，在该区域底部居中显示（设置窗关闭前先记下几何）。
    """
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QLabel

    # 复用：关掉上一个 toast，避免叠多层
    old = getattr(show_toast, "_current", None)
    if old is not None:
        try:
            old.close()
            old.deleteLater()
        except Exception:
            pass
        show_toast._current = None  # type: ignore[attr-defined]

    toast = QLabel()
    toast.setWindowFlags(
        Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.WindowStaysOnTopHint
        | Qt.WindowType.Tool
        | Qt.WindowType.WindowDoesNotAcceptFocus
    )
    toast.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
    toast.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    toast.setStyleSheet(
        """
        QLabel {
            background: rgba(20, 22, 28, 220);
            color: #e8f8ff;
            border: 1px solid rgba(0, 200, 255, 90);
            border-radius: 10px;
            padding: 12px 22px;
            font-size: 14px;
            font-weight: 600;
        }
        """
    )
    toast.setText(f"✓  {text}")
    toast.adjustSize()

    # 定位：at_rect > near/parent 几何 > 鼠标屏中央
    try:
        g = at_rect
        if g is None:
            anchor = near or parent
            if anchor is not None and anchor.isVisible():
                g = anchor.frameGeometry()
        if g is not None:
            x = g.x() + max(0, (g.width() - toast.width()) // 2)
            y = g.y() + max(8, (g.height() - toast.height()) // 2)
            toast.move(x, y)
        else:
            center_on_cursor_screen(toast)
    except Exception:
        center_on_cursor_screen(toast)

    toast.show()
    toast.raise_()
    show_toast._current = toast  # type: ignore[attr-defined]

    def _close():
        try:
            if getattr(show_toast, "_current", None) is toast:
                show_toast._current = None  # type: ignore[attr-defined]
            toast.close()
            toast.deleteLater()
        except Exception:
            pass

    QTimer.singleShot(max(600, int(msec)), _close)
