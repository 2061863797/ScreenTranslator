# -*- coding: utf-8 -*-
"""获取前台选中文本：WM_COPY / 多种复制快捷键。

终端（Windows Terminal、conhost 等）往往不用 Ctrl+C 复制选区，
而用 Ctrl+Shift+C 或「选中即复制」；标准编辑框则 WM_COPY / Ctrl+C 更稳。
"""

from __future__ import annotations

import ctypes
import time
from ctypes import wintypes

from pynput.keyboard import Controller, Key

user32 = ctypes.windll.user32

WM_COPY = 0x0301


class _GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hwndActive", wintypes.HWND),
        ("hwndFocus", wintypes.HWND),
        ("hwndCapture", wintypes.HWND),
        ("hwndMenuOwner", wintypes.HWND),
        ("hwndMoveSize", wintypes.HWND),
        ("hwndCaret", wintypes.HWND),
        ("rcCaret", wintypes.RECT),
    ]


def get_focus_hwnd() -> int:
    """前台焦点控件句柄（失败则返回前台顶层窗）。"""
    fg = user32.GetForegroundWindow()
    if not fg:
        return 0
    tid = user32.GetWindowThreadProcessId(fg, None)
    info = _GUITHREADINFO()
    info.cbSize = ctypes.sizeof(_GUITHREADINFO)
    if user32.GetGUIThreadInfo(tid, ctypes.byref(info)):
        return int(info.hwndFocus or info.hwndActive or fg)
    return int(fg)


def try_wm_copy() -> bool:
    """向焦点控件发 WM_COPY（多数编辑框有效，部分终端无效）。"""
    hwnd = get_focus_hwnd()
    if not hwnd:
        return False
    try:
        user32.SendMessageW(hwnd, WM_COPY, 0, 0)
        return True
    except Exception:
        return False


def _release_modifiers(kb: Controller) -> None:
    for mod in (
        Key.alt, Key.alt_l, Key.alt_r,
        Key.shift, Key.shift_l, Key.shift_r,
        Key.ctrl, Key.ctrl_l, Key.ctrl_r,
        Key.cmd,
    ):
        try:
            kb.release(mod)
        except Exception:
            pass


def send_copy_shortcut(kind: str = "ctrl_c") -> None:
    """模拟复制快捷键。kind: ctrl_c | ctrl_shift_c | ctrl_insert"""
    kb = Controller()
    _release_modifiers(kb)
    time.sleep(0.02)
    if kind == "ctrl_shift_c":
        # Windows Terminal / 许多终端默认
        with kb.pressed(Key.ctrl):
            with kb.pressed(Key.shift):
                kb.press("c")
                kb.release("c")
    elif kind == "ctrl_insert":
        with kb.pressed(Key.ctrl):
            kb.press(Key.insert)
            kb.release(Key.insert)
    else:
        with kb.pressed(Key.ctrl):
            kb.press("c")
            kb.release("c")
