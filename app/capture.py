# -*- coding: utf-8 -*-
"""屏幕捕获：全屏/区域截图（mss），指定窗口捕获（Win32 PrintWindow）。"""

import ctypes

import numpy as np

# 进程级声明 DPI 感知，保证高分屏下坐标与像素一致
ctypes.windll.shcore.SetProcessDpiAwareness(2)


def grab_region(x: int, y: int, width: int, height: int) -> np.ndarray:
    """截取屏幕指定区域，返回 BGR 数组。"""
    import mss

    with mss.mss() as sct:
        shot = sct.grab({"left": x, "top": y, "width": width, "height": height})
        img = np.asarray(shot)  # BGRA
    return img[:, :, :3].copy()


def list_windows() -> list[tuple[int, str]]:
    """枚举可见的顶层窗口，返回 (hwnd, 标题) 列表。"""
    import win32gui

    windows = []

    def _enum(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title.strip():
                windows.append((hwnd, title))

    win32gui.EnumWindows(_enum, None)
    return windows


def grab_window(hwnd: int) -> np.ndarray | None:
    """通过 PrintWindow 捕获指定窗口（含被遮挡部分）。失败返回 None。"""
    import win32gui
    import win32ui

    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    width, height = right - left, bottom - top
    if width <= 0 or height <= 0:
        return None

    hwnd_dc = win32gui.GetWindowDC(hwnd)
    mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
    save_dc = mfc_dc.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    try:
        bmp.CreateCompatibleBitmap(mfc_dc, width, height)
        save_dc.SelectObject(bmp)
        # PW_RENDERFULLCONTENT(=2)：支持 DirectX/硬件加速窗口
        ok = ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 2)
        if not ok:
            return None
        info = bmp.GetInfo()
        data = bmp.GetBitmapBits(True)
        img = np.frombuffer(data, dtype=np.uint8).reshape(
            (info["bmHeight"], info["bmWidth"], 4)
        )
        return img[:, :, :3].copy()
    finally:
        win32gui.DeleteObject(bmp.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwnd_dc)


def get_window_rect(hwnd: int) -> tuple[int, int, int, int]:
    """返回窗口客户区在屏幕上的位置 (x, y, w, h)，用于放置字幕层。"""
    import win32gui

    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    x, y = win32gui.ClientToScreen(hwnd, (left, top))
    return x, y, right - left, bottom - top
