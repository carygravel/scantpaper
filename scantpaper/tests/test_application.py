"Test application"

from unittest.mock import MagicMock
import gi
import pytest
from app import Application
from app_window import ApplicationWindow
from const import PROG_NAME, VERSION

gi.require_version("Gtk", "3.0")
from gi.repository import GLib  # pylint: disable=wrong-import-position


@pytest.mark.skip(reason="this doesn't work yet")
def test_application(mainloop_with_timeout):
    "Test the application class"
    loop = mainloop_with_timeout()

    class TestApp(Application):
        "Test application class"

        asserts = 0

        def do_activate(self):
            "Activate the application"
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


def test_text_layer_sort_combo_box(mocker):
    "Test the text layer sort combo box"
    mocker.patch("app_window.ApplicationWindow._populate_main_window")
    mocker.patch("app_window.ApplicationWindow._create_temp_directory")
    mocker.patch("config.read_config").return_value = {
        "restore window": False,
        "image_control_tool": "selector",
        "Paper": {},
        "cwd": ".",
        "unpaper options": "",
        "available-tmp-warning": 100,
        "message": {},
    }
    mocker.patch("shutil.disk_usage", return_value=(1, 1, 1024 * 1024 * 200))

    app = Application()
    app.args = MagicMock()
    app.args.device = None
    app.args.import_files = None
    app.args.import_all = None

    mock_app = MagicMock()
    mock_app.iconpath = "icons"
    mocker.patch("app_window.ApplicationWindow.get_application", return_value=mock_app)

    window = ApplicationWindow(application=app, title=f"{PROG_NAME} v{VERSION}")
    window.t_canvas = MagicMock()
    window._ocr_text_hbox = MagicMock()

    # Simulate changing the sort method to 'confidence'
    window._changed_text_sort_method(None, "confidence")
    window.t_canvas.sort_by_confidence.assert_called_once()
    window.t_canvas.sort_by_position.assert_not_called()

    # Reset the mock
    window.t_canvas.reset_mock()

    # Simulate changing the sort method to 'position'
    window._changed_text_sort_method(None, "position")
    window.t_canvas.sort_by_confidence.assert_not_called()
    window.t_canvas.sort_by_position.assert_called_once()


def test_text_layer_add_and_ok_buttons(mocker):
    """Test that the text layer add and ok buttons call _take_snapshot"""
    mocker.patch("app_window.ApplicationWindow._populate_main_window")
    mocker.patch("app_window.ApplicationWindow._create_temp_directory")
    mocker.patch("config.read_config").return_value = {
        "restore window": False,
        "image_control_tool": "selector",
        "Paper": {},
        "cwd": ".",
        "unpaper options": "",
        "available-tmp-warning": 100,
        "message": {},
    }
    mocker.patch("shutil.disk_usage", return_value=(1, 1, 1024 * 1024 * 200))

    app = Application()
    app.args = MagicMock()
    app.args.device = None
    app.args.import_files = None
    app.args.import_all = None

    mock_app = MagicMock()
    mock_app.iconpath = "icons"
    mocker.patch("app_window.ApplicationWindow.get_application", return_value=mock_app)

    window = ApplicationWindow(application=app, title=f"{PROG_NAME} v{VERSION}")

    # Mock dependencies for the tested methods
    window.slist = MagicMock()
    window.slist.thread._take_snapshot = MagicMock()

    window._ocr_text_hbox = MagicMock()
    window._ocr_text_hbox._textbuffer.get_text.return_value = "some text"

    window._current_ocr_bbox = MagicMock()
    window.view = MagicMock()
    window.view.get_selection.return_value = {"x": 0, "y": 0, "width": 10, "height": 10}

    window._current_page = MagicMock()
    window.t_canvas = MagicMock()
    window._edit_ocr_text = MagicMock()

    # Call the method for the "OK" button
    window._ocr_text_button_clicked(None)

    # Assert that _take_snapshot was called
    window.slist.thread._take_snapshot.assert_called_once()

    # Reset the mock for the next call
    window.slist.thread._take_snapshot.reset_mock()

    # Call the method for the "Add" button
    window._ocr_text_add(None)

    # Assert that _take_snapshot was called again
    window.slist.thread._take_snapshot.assert_called_once()


def test_edit_ocr_text_updates_selection(mocker):
    "Test _edit_ocr_text"
    mocker.patch("app_window.ApplicationWindow._populate_main_window")
    mocker.patch("app_window.ApplicationWindow._create_temp_directory")
    mocker.patch("config.read_config").return_value = {
        "restore window": False,
        "image_control_tool": "selector",
        "Paper": {},
        "cwd": ".",
        "unpaper options": "",
        "available-tmp-warning": 100,
        "message": {},
    }
    mocker.patch("shutil.disk_usage", return_value=(1, 1, 1024 * 1024 * 200))

    app = Application()
    app.args = MagicMock()
    app.args.device = None
    app.args.import_files = None
    app.args.import_all = None

    mock_app = MagicMock()
    mock_app.iconpath = "icons"
    mocker.patch("app_window.ApplicationWindow.get_application", return_value=mock_app)

    window = ApplicationWindow(application=app, title=f"{PROG_NAME} v{VERSION}")

    # Mock dependencies for _edit_ocr_text
    window._ocr_text_hbox = MagicMock()
    window.view = MagicMock()
    window.t_canvas = MagicMock()

    # Create two distinct mock bboxes
    mock_bbox1 = MagicMock()
    mock_bbox1.text = "word1"
    mock_bbox2 = MagicMock()
    mock_bbox2.text = "word2"

    mock_event = MagicMock()
    mock_target = MagicMock()

    # First call to _edit_ocr_text, simulating a click on the first box
    window._edit_ocr_text(
        widget=mock_bbox1, _target=mock_target, ev=mock_event, bbox=mock_bbox1
    )
    assert window._current_ocr_bbox == mock_bbox1

    # Second call to _edit_ocr_text, simulating a click on the second box
    window._edit_ocr_text(
        widget=mock_bbox2, _target=mock_target, ev=mock_event, bbox=mock_bbox2
    )
    assert window._current_ocr_bbox == mock_bbox2
