"Test application"

import gi
import pytest
from unittest.mock import MagicMock

gi.require_version("Gtk", "3.0")
from gi.repository import GLib  # pylint: disable=wrong-import-position
from app import Application
from app_window import ApplicationWindow
from const import PROG_NAME, VERSION


@pytest.mark.skip(reason="this doesn't work yet")
def test_application(mainloop_with_timeout):
    loop = mainloop_with_timeout()

    class TestApp(Application):
        asserts = 0

        def do_activate(self):
            if not self.window:
                self.window = ApplicationWindow(
                    application=self, title=f"{PROG_NAME} v{VERSION}"
                )
                global window
                window = self.window
            self.window.present()
            self.asserts += 1

    app = TestApp()

    GLib.idle_add(lambda: loop.quit())

    app.run()
    assert app.asserts == 1, "app activation finished"


def test_text_layer_sort_combo_box():
    """
    Test that the text layer sort combo box calls the correct sorting method.
    """
    app = Application()
    app.args = MagicMock()
    app.args.device = None
    app.args.import_files = None
    app.args.import_all = None

    window = ApplicationWindow(application=app, title=f"{PROG_NAME} v{VERSION}")
    window.t_canvas = MagicMock()

    # Simulate changing the sort method to 'confidence'
    window._ocr_text_hbox.emit("sort-changed", "confidence")
    window.t_canvas.sort_by_confidence.assert_called_once()
    window.t_canvas.sort_by_position.assert_not_called()

    # Reset the mock
    window.t_canvas.reset_mock()

    # Simulate changing the sort method to 'position'
    window._ocr_text_hbox.emit("sort-changed", "position")
    window.t_canvas.sort_by_confidence.assert_not_called()
    window.t_canvas.sort_by_position.assert_called_once()
