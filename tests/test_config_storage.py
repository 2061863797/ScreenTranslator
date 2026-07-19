import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app import config
from app.storage import Storage


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.old_path = config.CONFIG_PATH
        self.tmp = tempfile.TemporaryDirectory()
        config.CONFIG_PATH = Path(self.tmp.name) / "config.json"

    def tearDown(self):
        config.CONFIG_PATH = self.old_path
        self.tmp.cleanup()

    def test_non_object_json_falls_back_to_defaults(self):
        config.CONFIG_PATH.write_text("null", encoding="utf-8")
        loaded = config.load()
        self.assertEqual(loaded["server_port"], config.DEFAULTS["server_port"])

    def test_invalid_known_types_fall_back(self):
        config.CONFIG_PATH.write_text(
            json.dumps({"server_port": "abc", "history_enabled": "false"}),
            encoding="utf-8",
        )
        loaded = config.load()
        self.assertEqual(loaded["server_port"], 8080)
        self.assertIs(loaded["history_enabled"], True)

    def test_font_sizes_accept_default_or_8_to_48_pixels(self):
        config.CONFIG_PATH.write_text(
            json.dumps({
                "translate_window_font_size": 7,
                "window_watch_font_size": 20,
                "region_watch_font_size": 49,
            }),
            encoding="utf-8",
        )
        loaded = config.load()
        self.assertEqual(loaded["translate_window_font_size"], 0)
        self.assertEqual(loaded["window_watch_font_size"], 20)
        self.assertEqual(loaded["region_watch_font_size"], 0)

    def test_save_is_atomic_and_readable(self):
        data = dict(config.DEFAULTS)
        data["target_language"] = "英语"
        config.save(data)
        self.assertFalse(config.CONFIG_PATH.with_name("config.json.tmp").exists())
        self.assertEqual(json.loads(config.CONFIG_PATH.read_text(encoding="utf-8"))["target_language"], "英语")


class StorageTests(unittest.TestCase):
    def test_legacy_table_is_preserved_and_history_can_be_cleared(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "data.db"
            conn = sqlite3.connect(db)
            conn.execute("CREATE TABLE vocabulary (word TEXT)")
            conn.execute("INSERT INTO vocabulary VALUES ('keep')")
            conn.commit()
            conn.close()

            storage = Storage(db)
            storage.add_history("a", "b", "test")
            storage.clear_history()
            self.assertEqual(storage.recent_history(), [])
            row = storage._conn.execute("SELECT word FROM vocabulary").fetchone()
            self.assertEqual(row, ("keep",))
            storage.close()


if __name__ == "__main__":
    unittest.main()
