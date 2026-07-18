# -*- coding: utf-8 -*-
"""选择要持续翻译的窗口的对话框。"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import capture
from .theme import CornerSizeGrip, FLOAT_PANEL_STYLE, apply_frameless_float
from .topmost import center_on_cursor_screen, raise_to_front


class WindowPicker(QDialog):
    """列出可见顶层窗口，返回选中的 hwnd（selected_hwnd，未选为 None）。

    始终置顶并居中到当前鼠标所在屏幕，避免被游戏/浏览器挡在后面找不到。
    视觉与截图/划词翻译结果窗一致（半透明深色面板）。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择要翻译的窗口")
        apply_frameless_float(self, tool=False)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.resize(440, 400)
        self.setMinimumSize(320, 260)
        self.selected_hwnd: int | None = None

        self._list = QListWidget()
        self._refresh()

        btn_refresh = QPushButton("刷新")
        btn_ok = QPushButton("开始翻译")
        btn_cancel = QPushButton("取消")
        btn_refresh.clicked.connect(self._refresh)
        btn_ok.clicked.connect(self._confirm)
        btn_cancel.clicked.connect(self.reject)
        self._list.itemDoubleClicked.connect(lambda _: self._confirm())

        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(4, 2, 2, 2)
        title_lbl = QLabel("选择要翻译的窗口")
        title_lbl.setStyleSheet("font-size:14px;font-weight:600;")
        btn_close = QPushButton("×")
        btn_close.setFixedWidth(28)
        btn_close.clicked.connect(self.reject)
        title_bar.addWidget(title_lbl)
        title_bar.addStretch()
        title_bar.addWidget(btn_close)

        bar = QHBoxLayout()
        bar.addWidget(btn_refresh)
        bar.addStretch()
        bar.addWidget(btn_ok)
        bar.addWidget(btn_cancel)

        container = QWidget()
        container.setObjectName("panel")
        inner = QVBoxLayout(container)
        inner.setContentsMargins(12, 10, 12, 10)
        inner.setSpacing(8)
        inner.addLayout(title_bar)
        hint = QLabel("请选择要持续翻译的窗口（双击也可）")
        inner.addWidget(hint)
        inner.addWidget(self._list, stretch=1)
        inner.addLayout(bar)
        grip_row = QHBoxLayout()
        grip_row.setContentsMargins(0, 0, 0, 0)
        grip_row.addStretch()
        grip_row.addWidget(CornerSizeGrip(container))
        inner.addLayout(grip_row)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(container)
        self.setStyleSheet(FLOAT_PANEL_STYLE)

        self._drag_offset = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # 仅标题区拖动：列表区域留给选择
            if event.position().y() < 40:
                self._drag_offset = (
                    event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            event.buttons() & Qt.MouseButton.LeftButton
            and self._drag_offset is not None
        ):
            self.move(event.globalPosition().toPoint() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def showEvent(self, event: QShowEvent):
        super().showEvent(event)
        center_on_cursor_screen(self)
        raise_to_front(self)

    def exec(self) -> int:  # noqa: A003 — Qt API
        center_on_cursor_screen(self)
        raise_to_front(self)
        return super().exec()

    def _refresh(self):
        self._list.clear()
        own_title = self.windowTitle()
        for hwnd, title in capture.list_windows():
            if title == own_title:
                continue
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, hwnd)
            self._list.addItem(item)

    def _confirm(self):
        item = self._list.currentItem()
        if item:
            self.selected_hwnd = item.data(Qt.ItemDataRole.UserRole)
            self.accept()
