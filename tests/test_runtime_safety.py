import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
from PySide6.QtCore import QCoreApplication, QMimeData

from app import capture
from app.llama_server import LlamaServer
from app.main import App, _PreloadSignals, _clone_mime_data


class _FakeProcess:
    def __init__(self):
        self.pid = 123
        self.stdout = []
        self.returncode = None
        self.terminated = False

    def poll(self):
        return 0 if self.terminated else None

    def terminate(self):
        self.terminated = True
        self.returncode = 0

    def wait(self, timeout=None):
        return 0

    def kill(self):
        self.terminate()


class _FakeMss:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def grab(self, box):
        image = np.zeros((box["height"], box["width"], 4), dtype=np.uint8)
        image[:, :, 0] = 10 if box["left"] < 100 else 20
        return image


class RuntimeSafetyTests(unittest.TestCase):
    def test_llama_timeout_reaps_spawned_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "llama-server.exe").write_bytes(b"x")
            model = root / "model.gguf"
            model.write_bytes(b"GGUF")
            server = LlamaServer({
                "llama_dir": str(root),
                "model_path": str(model),
                "server_host": "127.0.0.1",
                "server_port": 18080,
            })
            proc = _FakeProcess()
            server.is_healthy = Mock(return_value=False)
            with patch("app.llama_server.subprocess.Popen", return_value=proc):
                with self.assertRaises(TimeoutError):
                    server.start(wait_seconds=0)
            self.assertTrue(proc.terminated)
            self.assertIsNone(server._proc)

    def test_health_check_rejects_unrelated_http_service(self):
        server = object.__new__(LlamaServer)
        server.host, server.port = "127.0.0.1", 18080
        unrelated = Mock(status_code=200)
        unrelated.json.return_value = {"hello": "world"}
        with patch("app.llama_server.requests.get", return_value=unrelated):
            self.assertFalse(server.is_healthy())

    def test_native_rect_is_mapped_to_qt_logical_coordinates(self):
        old = list(capture._SCREEN_LAYOUT)
        try:
            capture._SCREEN_LAYOUT[:] = [(0, 0, 100, 100, 0, 0, 200, 200)]
            self.assertEqual(capture._native_rect_to_logical(20, 40, 100, 80), (10, 20, 50, 40))
        finally:
            capture._SCREEN_LAYOUT[:] = old

    def test_region_capture_stitches_mixed_dpi_screens(self):
        old = list(capture._SCREEN_LAYOUT)
        try:
            capture._SCREEN_LAYOUT[:] = [
                (0, 0, 100, 100, 0, 0, 100, 100),
                (100, 0, 100, 100, 100, 0, 200, 200),
            ]
            with patch("mss.MSS", return_value=_FakeMss()):
                image = capture.grab_region(50, 0, 100, 50)
            self.assertEqual(image.shape, (50, 100, 3))
            self.assertTrue(np.all(image[:, :50, 0] == 10))
            self.assertTrue(np.all(image[:, 50:, 0] == 20))
        finally:
            capture._SCREEN_LAYOUT[:] = old

    def test_clipboard_mime_clone_preserves_all_formats(self):
        source = QMimeData()
        source.setText("plain")
        source.setHtml("<b>rich</b>")
        source.setData("application/x-screen-translator-test", b"payload")
        cloned = _clone_mime_data(source)
        self.assertEqual(cloned.text(), "plain")
        self.assertEqual(cloned.html(), "<b>rich</b>")
        self.assertEqual(bytes(cloned.data("application/x-screen-translator-test")), b"payload")

    def test_preload_signal_crosses_from_python_thread(self):
        app = QCoreApplication.instance() or QCoreApplication([])
        bridge = _PreloadSignals()
        received = []
        bridge.status.connect(lambda *args: received.append(args))
        thread = threading.Thread(target=lambda: bridge.status.emit("ocr", "ok", ""))
        thread.start()
        thread.join()
        deadline = time.time() + 1
        while not received and time.time() < deadline:
            app.processEvents()
            time.sleep(0.01)
        self.assertEqual(received, [("ocr", "ok", "")])

    def test_cancelled_selection_clears_every_mode(self):
        app = App.__new__(App)
        app.log = Mock()
        for mode in ("screenshot", "silent_ocr", "region_watch"):
            app._pending_mode = mode
            app._on_region_cancelled()
            self.assertIsNone(app._pending_mode)

    def test_selection_start_failure_resets_pending_mode(self):
        app = App.__new__(App)
        app._quitting = False
        app._pending_mode = None
        app.selector = Mock()
        app.selector.isVisible.return_value = False
        app.selector.start.side_effect = OSError("capture unavailable")
        app.qapp = Mock()
        app.qapp.screens.return_value = []
        app.log = Mock()
        app._show_error = Mock()
        with patch("app.main.capture.configure_qt_screens"):
            app._start_select("silent_ocr")
        self.assertIsNone(app._pending_mode)
        app._show_error.assert_called_once_with("capture unavailable")

    def test_copy_shortcut_failure_does_not_abort_fallback_flow(self):
        app = App.__new__(App)
        app.log = Mock()
        app._word_marker = "marker"
        app._word_copy_kinds = ("ctrl_c",)
        app._word_copy_phase = 0
        clipboard = Mock()
        with (
            patch("app.main.QApplication.clipboard", return_value=clipboard),
            patch(
                "app.selection.send_copy_shortcut",
                side_effect=OSError("blocked"),
            ),
        ):
            app._word_fire_copy_phase()
        clipboard.setText.assert_called_once_with("marker")
        app.log.warning.assert_called_once()


if __name__ == "__main__":
    unittest.main()
