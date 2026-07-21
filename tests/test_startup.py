import unittest
from unittest.mock import Mock, patch

from app.config import DEFAULTS
from app.i18n import set_language
from app.main import App


class StartupTests(unittest.TestCase):
    def tearDown(self):
        set_language("zh")

    def test_application_name_follows_interface_language(self):
        app = App.__new__(App)
        app.qapp = Mock()

        set_language("zh")
        app._refresh_application_name()
        app.qapp.setApplicationName.assert_called_with("本地屏译")
        app.qapp.setApplicationDisplayName.assert_called_with("本地屏译")

        set_language("en")
        app._refresh_application_name()
        app.qapp.setApplicationName.assert_called_with("LocalScreen Translator")
        app.qapp.setApplicationDisplayName.assert_called_with(
            "LocalScreen Translator"
        )

    def test_exec_opens_existing_settings_window_after_event_loop_starts(self):
        app = App.__new__(App)
        app.hotkeys = Mock()
        app.hotkeys.start.return_value = []
        app.log = Mock()
        app.cfg = dict(DEFAULTS)
        app.settings_win = Mock()
        app._show_window = Mock()
        app.qapp = Mock()
        app.qapp.exec.return_value = 0

        with patch("app.main.QTimer.singleShot") as single_shot:
            self.assertEqual(app.exec(), 0)

        single_shot.assert_called_once()
        delay, callback = single_shot.call_args.args
        self.assertEqual(delay, 0)
        callback()
        app._show_window.assert_called_once_with(app.settings_win)


if __name__ == "__main__":
    unittest.main()
