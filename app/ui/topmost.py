# -*- coding: utf-8 -*-
"""托盘应用无主窗时，弹层容易被其它全屏/置顶窗挡住。

统一：StaysOnTop + raise + 激活 + Win32 TOPMOST/前台。
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor, QGuiApplication
from PySide6.QtWidgets import QWidget

from ..applog import get_logger

if TYPE_CHECKING:
    pass

# Win32
_HWND_TOPMOST = -1
_HWND_NOTOPMOST = -2
_SWP_NOSIZE = 0x0001
_SWP_NOMOVE = 0x0002
_SWP_SHOWWINDOW = 0x0040
_SWP_NOACTIVATE = 0x0010
_SWP_NOOWNERZORDER = 0x0200
# 顶层窗：GWL/GWLP_HWNDPARENT 表示 owner（从属关系），不是 parent
_GWLP_HWNDPARENT = -8

_log = get_logger("topmost")
_user32 = ctypes.WinDLL("user32", use_last_error=True)

try:
    _SetWindowLongPtr = _user32.SetWindowLongPtrW
except AttributeError:  # 极少数 32 位环境
    _SetWindowLongPtr = _user32.SetWindowLongW  # type: ignore[misc, assignment]

_SetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
_SetWindowLongPtr.restype = ctypes.c_ssize_t
_SetWindowPos = _user32.SetWindowPos
_SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
]
_SetWindowPos.restype = wintypes.BOOL


def _set_window_owner(hwnd: int, owner_hwnd: int) -> bool:
    """设置顶层窗 owner；返回 False 时保留 Win32 错误日志。"""
    ctypes.set_last_error(0)
    previous = _SetWindowLongPtr(hwnd, _GWLP_HWNDPARENT, owner_hwnd)
    error = ctypes.get_last_error()
    if previous == 0 and error:
        _log.warning(
            "设置浮层 owner 失败 hwnd=%#x owner=%#x error=%d",
            hwnd,
            owner_hwnd,
            error,
        )
        return False
    return True


def _set_window_pos(hwnd: int, after_hwnd: int, flags: int) -> bool:
    """只调整 Z 序；失败时记录 GetLastError，避免静默失效。"""
    ctypes.set_last_error(0)
    if _SetWindowPos(hwnd, after_hwnd, 0, 0, 0, 0, flags):
        return True
    error = ctypes.get_last_error()
    _log.warning(
        "调整浮层 Z 序失败 hwnd=%#x after=%#x flags=%#x error=%d",
        hwnd,
        after_hwnd,
        flags,
        error,
    )
    return False


def ensure_stays_on_top(widget: QWidget) -> None:
    """保证带 WindowStaysOnTopHint（不改其它 flag）。"""
    flags = widget.windowFlags()
    if not (flags & Qt.WindowType.WindowStaysOnTopHint):
        widget.setWindowFlags(flags | Qt.WindowType.WindowStaysOnTopHint)


def set_overlay_layer(widget: QWidget, owner_hwnd: int | None) -> None:
    """持续翻译浮层的 Z 序策略。

    - owner_hwnd 有值（窗口翻译）：去掉全局置顶，绑定为该窗口的 owned 窗，
      与目标同层——目标被挡住时译文一起被挡，不压在其它应用上。
    - owner_hwnd 为 None（区域翻译 / 停止后）：恢复 WindowStaysOnTopHint，
      区域没有目标窗可跟随时仍需可见。

    改 flag 会重建原生 HWND，调用方应在之后重新应用显示亲和性等属性。
    """
    if widget is None:
        return
    try:
        owner = int(owner_hwnd) if owner_hwnd else 0
    except (TypeError, ValueError):
        owner = 0

    want_topmost = owner == 0
    flags = widget.windowFlags()
    has_top = bool(flags & Qt.WindowType.WindowStaysOnTopHint)
    flag_dirty = (want_topmost and not has_top) or ((not want_topmost) and has_top)

    if flag_dirty:
        was_visible = widget.isVisible()
        if want_topmost:
            widget.setWindowFlags(flags | Qt.WindowType.WindowStaysOnTopHint)
        else:
            widget.setWindowFlags(flags & ~Qt.WindowType.WindowStaysOnTopHint)
        if was_visible:
            # setWindowFlags 会 hide，需恢复；不抢焦点
            widget.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
            widget.show()
            widget.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)

    try:
        hwnd = int(widget.winId())
        if not hwnd:
            _log.warning("浮层没有可用 HWND widget=%s", type(widget).__name__)
            return
        swp = (
            _SWP_NOMOVE
            | _SWP_NOSIZE
            | _SWP_NOACTIVATE
            | _SWP_NOOWNERZORDER
        )
        if owner:
            # 退出 TOPMOST 层，再挂 owner，最后插到目标正上方
            ok_not_top = _set_window_pos(hwnd, _HWND_NOTOPMOST, swp)
            ok_owner = _set_window_owner(hwnd, owner)
            ok_stack = _set_window_pos(hwnd, owner, swp)
            success = ok_not_top and ok_owner and ok_stack
        else:
            ok_owner = _set_window_owner(hwnd, 0)
            ok_stack = _set_window_pos(hwnd, _HWND_TOPMOST, swp)
            success = ok_owner and ok_stack
        if success:
            widget._st_layer_owner = owner or None  # type: ignore[attr-defined]
    except Exception:
        _log.exception("设置浮层层级异常 widget=%s owner=%s", type(widget).__name__, owner)


def restack_above_owner(widget: QWidget, owner_hwnd: int) -> None:
    """目标窗 z 序变化后，把浮层轻轻贴回目标正上方（不改 flag、不激活）。"""
    if widget is None or not owner_hwnd:
        return
    try:
        hwnd = int(widget.winId())
        if not hwnd or not widget.isVisible():
            return
        _set_window_pos(
            hwnd,
            int(owner_hwnd),
            _SWP_NOMOVE
            | _SWP_NOSIZE
            | _SWP_NOACTIVATE
            | _SWP_NOOWNERZORDER,
        )
    except Exception:
        _log.exception(
            "重排浮层异常 widget=%s owner=%s",
            type(widget).__name__,
            owner_hwnd,
        )


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
