"Tests for the ScanMenuItemMixins."

from unittest.mock import MagicMock
import pytest
import gi
from scan_menu_item_mixins import ScanMenuItemMixins
from const import EMPTY

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


@pytest.fixture
def mock_scan_window(mocker):
    "Fixture to provide a configured MockWindow"
    mock_app = mocker.Mock()
    mock_app.args = mocker.Mock()
    mock_app.args.device = None

    class MockWindow(Gtk.Window, ScanMenuItemMixins):
        "Test class to hold mixin"

        slist = None
        post_process_progress = None
        settings = {}
        _windows = None
        _scan_progress = None
        _rotate_controls = None
        _scan_udt_cmbx = None
        _unpaper = None
        _dependencies = {}
        session = None
        _ocr_engine = [["tesseract", "Tesseract"]]

        # Callbacks
        _error_callback = mocker.Mock()
        _finished_process_callback = mocker.Mock()
        _process_error_callback = mocker.Mock()

        def get_application(self, *args, **kwargs):  # pylint: disable=arguments-differ
            "mock"
            return mock_app

    # Instantiate
    window = MockWindow()

    # Common mocks
    window.slist = mocker.MagicMock()
    window.slist.data = []
    window.post_process_progress = mocker.Mock()
    window._scan_progress = mocker.Mock()
    window._rotate_controls = mocker.Mock()

    # Default settings
    window.settings = {
        "device": "mock_device",
        "SANE_DEFAULT_DEVICE": "env_device",
        "Paper": "A4",
        "allow-batch-flatbed": False,
        "adf-defaults-scan-all-pages": False,
        "ignore-duplex-capabilities": False,
        "cycle sane handle": False,
        "cancel-between-pages": False,
        "profile": {},
        "scan_window_width": 100,
        "scan_window_height": 100,
        "cache-device-list": False,
        "device list": [],
        "rotate facing": 0,
        "rotate reverse": 0,
        "unpaper on scan": False,
        "udt_on_scan": False,
        "OCR on scan": False,
        "ocr engine": "tesseract",
        "ocr language": "eng",
        "threshold-before-ocr": False,
        "threshold tool": 0,
        "user_defined_tools": [],
        "current_udt": "",
    }

    window.session = mocker.Mock()
    window.session.name = "session_name"
    window._dependencies = {"unpaper": True}
    window._unpaper = mocker.Mock()

    yield window

    window.destroy()


def test_scan_dialog_show_existing(mock_scan_window):
    "Test scan_dialog when window already exists"
    mock_scan_window._windows = MagicMock()

    mock_scan_window.scan_dialog(None, None)

    mock_scan_window._windows.show_all.assert_called_once()


def test_scan_dialog_create_new(mocker, mock_scan_window):
    "Test scan_dialog creating a new window"
    mock_sane_dialog_cls = mocker.patch("scan_menu_item_mixins.SaneScanDialog")
    mock_sane_dialog_instance = mock_sane_dialog_cls.return_value
    mock_sane_dialog_instance.notebook = mocker.Mock()

    # Mock OCRControls and RotateControls
    mocker.patch("scan_menu_item_mixins.OCRControls")
    mocker.patch("scan_menu_item_mixins.RotateControls")

    # Mock Gtk widgets to avoid type errors
    mocker.patch("scan_menu_item_mixins.Gtk.Box")
    mocker.patch("scan_menu_item_mixins.Gtk.ScrolledWindow")

    mock_scan_window.scan_dialog(None, None)

    mock_sane_dialog_cls.assert_called_once()
    assert mock_scan_window._windows == mock_sane_dialog_instance
    mock_sane_dialog_instance.connect.assert_called()
    mock_sane_dialog_instance.get_devices.assert_called_once()


def test_changed_device_callback(mock_scan_window):
    "Test _changed_device_callback"
    mock_widget = MagicMock()

    mock_scan_window._changed_device_callback(mock_widget, "new_device")

    assert mock_scan_window.settings["device"] == "new_device"
    mock_widget.connect.assert_called_with(
        "reloaded-scan-options", mock_scan_window._reloaded_scan_options_callback
    )


def test_changed_device_callback_empty(mock_scan_window):
    "Test _changed_device_callback with empty device"
    mock_widget = MagicMock()
    original_device = mock_scan_window.settings["device"]

    mock_scan_window._changed_device_callback(mock_widget, EMPTY)

    assert mock_scan_window.settings["device"] == original_device
    mock_widget.connect.assert_not_called()


def test_changed_device_list_callback(mock_scan_window):
    "Test _changed_device_list_callback"
    mock_widget = MagicMock()
    device1 = MagicMock()
    device1.name = "dev1"
    device2 = MagicMock()
    device2.name = "dev2"
    device_list = [device1, device2]

    mock_scan_window._changed_device_list_callback(mock_widget, device_list)

    assert mock_widget.device == "dev1"


def test_changed_device_list_callback_blacklist(mock_scan_window):
    "Test _changed_device_list_callback with blacklist"
    mock_scan_window.settings["device blacklist"] = "dev1"

    mock_widget = MagicMock()
    device1 = MagicMock()
    device1.name = "dev1"
    device2 = MagicMock()
    device2.name = "dev2"
    device_list = [device1, device2]

    mock_scan_window._changed_device_list_callback(mock_widget, device_list)

    # dev1 should be removed, so dev2 becomes the first/default
    assert len(device_list) == 1
    assert device_list[0].name == "dev2"
    assert mock_widget.device == "dev2"


def test_changed_side_to_scan_callback(mock_scan_window):
    "Test _changed_side_to_scan_callback"
    mock_widget = MagicMock()

    # Case 1: Existing pages
    mock_scan_window.slist.data = [[4, 0, 0]]  # Last page number is 4
    mock_scan_window._changed_side_to_scan_callback(mock_widget, None)
    assert mock_widget.page_number_start == 5

    # Case 2: No pages
    mock_scan_window.slist.data = []
    mock_scan_window._changed_side_to_scan_callback(mock_widget, None)
    assert mock_widget.page_number_start == 1


def test_new_scan_callback(mock_scan_window):
    "Test _new_scan_callback"
    mock_image = MagicMock()
    mock_scan_window.post_process_progress = MagicMock()
    mock_scan_window.slist.import_scan = MagicMock()

    mock_scan_window._new_scan_callback(None, mock_image, 1, 300, 300)

    mock_scan_window.slist.import_scan.assert_called_once()
    call_kwargs = mock_scan_window.slist.import_scan.call_args[1]

    assert call_kwargs["page"] == 1
    assert call_kwargs["dir"] == "session_name"
    assert call_kwargs["image_object"] == mock_image
    assert call_kwargs["resolution"] == (300, 300, "PixelsPerInch")


def test_show_unpaper_options(mocker, mock_scan_window):
    "Test _show_unpaper_options"
    mock_dialog_cls = mocker.patch("scan_menu_item_mixins.Dialog")
    mock_dialog_instance = mock_dialog_cls.return_value

    mock_scan_window._show_unpaper_options(None)

    mock_scan_window._unpaper.add_options.assert_called_once()
    mock_dialog_instance.show_all.assert_called_once()

    # Test apply callback
    args, _kwargs = mock_dialog_instance.add_actions.call_args
    actions = args[0]
    apply_callback = None
    for action_name, callback in actions:
        if action_name == "gtk-ok":
            apply_callback = callback
            break

    assert apply_callback

    mock_scan_window._unpaper.get_options.return_value = "options"
    apply_callback()

    assert mock_scan_window.settings["unpaper options"] == "options"
    mock_dialog_instance.destroy.assert_called()
