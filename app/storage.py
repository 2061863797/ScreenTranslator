# -*- coding: utf-8 -*-
"""本地存储：翻译历史（SQLite，最多保留 50 条）。"""

import sqlite3
import time
from pathlib import Path

from .paths import DB_PATH

MAX_HISTORY = 50


class Storage:
    def __init__(self, db_path: Path | None = None):
        db_path = db_path or DB_PATH
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                source TEXT NOT NULL,
                translation TEXT NOT NULL,
                mode TEXT NOT NULL
            )"""
        )
        # 旧版本可能存在生词本表，功能已移除，顺手清掉
        self._conn.execute("DROP TABLE IF EXISTS vocabulary")
        self._conn.commit()

    def add_history(self, source: str, translation: str, mode: str) -> None:
        self._conn.execute(
            "INSERT INTO history (ts, source, translation, mode) VALUES (?, ?, ?, ?)",
            (time.time(), source, translation, mode),
        )
        # 只保留最新 MAX_HISTORY 条
        self._conn.execute(
            "DELETE FROM history WHERE id NOT IN "
            "(SELECT id FROM history ORDER BY id DESC LIMIT ?)",
            (MAX_HISTORY,),
        )
        self._conn.commit()

    def recent_history(self, limit: int = MAX_HISTORY) -> list[tuple]:
        cur = self._conn.execute(
            "SELECT ts, source, translation, mode FROM history ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return cur.fetchall()

    def close(self) -> None:
        self._conn.close()
