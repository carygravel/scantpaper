"Tests for the ScanMenuItemMixins."

import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
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

    # Patch Gtk in the module under test to avoid TypeError with real GObject methods
    mocker.patch("scan_menu_item_mixins.Gtk")
    mocker.patch("scan_menu_item_mixins._", side_effect=lambda x: x)

    class MockWindow(ScanMenuItemMixins):
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


def test_scan_dialog_show_existing(mock_scan_window):
    "Test scan_dialog when window already exists"
    mock_scan_window._windows = MagicMock()

    mock_scan_window.scan_dialog(None, None)

    mock_scan_window._windows.show_all.assert_called_once()


def test_scan_dialog_sane_default_device(mocker, mock_scan_window):
    "Test scan_dialog uses SANE_DEFAULT_DEVICE if no device in settings"
    del mock_scan_window.settings["device"]
    mocker.patch.dict(os.environ, {"SANE_DEFAULT_DEVICE": "env_dev"})
    mocker.patch("scan_menu_item_mixins.SaneScanDialog")
    mocker.patch("scan_menu_item_mixins.OCRControls")
    mocker.patch("scan_menu_item_mixins.RotateControls")

    mock_scan_window.scan_dialog(None, None)

    assert mock_scan_window.settings["device"] == "env_dev"


def test_scan_dialog_create_new(mocker, mock_scan_window):
    "Test scan_dialog creating a new window"
    mock_sane_dialog_cls = mocker.patch("scan_menu_item_mixins.SaneScanDialog")
    mock_sane_dialog_instance = mock_sane_dialog_cls.return_value
    mock_sane_dialog_instance.notebook = mocker.Mock()

    # Mock OCRControls and RotateControls
    mocker.patch("scan_menu_item_mixins.OCRControls")
    mocker.patch("scan_menu_item_mixins.RotateControls")

    mock_scan_window.scan_dialog(None, None, hidden=True)

    mock_sane_dialog_cls.assert_called_once()
    assert mock_scan_window._windows == mock_sane_dialog_instance
    mock_sane_dialog_instance.connect.assert_called()
    mock_sane_dialog_instance.show_all.assert_not_called()


def test_scan_dialog_callbacks(mocker, mock_scan_window):
    "Test callbacks defined inside scan_dialog"
    mock_sane_dialog_cls = mocker.patch("scan_menu_item_mixins.SaneScanDialog")
    mock_sane_dialog_instance = mock_sane_dialog_cls.return_value
    mock_sane_dialog_instance.notebook = mocker.Mock()

    mocker.patch("scan_menu_item_mixins.OCRControls")
    mocker.patch("scan_menu_item_mixins.RotateControls")

    # Capture callbacks
    callbacks = {}

    def side_effect(signal, callback, *args):
        callbacks[signal] = callback
        return mocker.Mock()

    mock_sane_dialog_instance.connect.side_effect = side_effect

    mock_scan_window.scan_dialog(None, None)

    # Test started-process callback
    assert "started-process" in callbacks
    mock_scan_window._scan_progress.connect.return_value = "signal_id"
    callbacks["started-process"](None, "starting")
    mock_scan_window._scan_progress.set_fraction.assert_called_with(0)
    mock_scan_window._scan_progress.set_text.assert_called_with("starting")
    mock_scan_window._scan_progress.connect.assert_called_with(
        "clicked", mock_sane_dialog_instance.cancel_scan
    )

    # Test removed-profile callback
    assert "removed-profile" in callbacks
    mock_scan_window.settings["profile"]["test_prof"] = "data"
    callbacks["removed-profile"](None, "test_prof")
    assert "test_prof" not in mock_scan_window.settings["profile"]

    # Test changed-current-scan-options callback
    assert "changed-current-scan-options" in callbacks
    mock_profile = mocker.Mock()
    mock_profile.get.return_value = "opts"
    callbacks["changed-current-scan-options"](None, mock_profile, None)
    assert mock_scan_window.settings["default-scan-options"] == "opts"

    # Test changed-paper-formats callback
    assert "changed-paper-formats" in callbacks
    callbacks["changed-paper-formats"](None, "A3")
    assert mock_scan_window.settings["Paper"] == "A3"


def test_scan_dialog_args_device(mocker, mock_scan_window):
    "Test scan_dialog with args.device"
    mocker.patch("scan_menu_item_mixins.SaneScanDialog")
    mocker.patch("scan_menu_item_mixins.OCRControls")
    mocker.patch("scan_menu_item_mixins.RotateControls")

    mock_app = mock_scan_window.get_application()
    mock_app.args.device = ["dev1"]

    mock_scan_window.scan_dialog(None, None)

    assert mock_scan_window._windows.device_list[0].name == "dev1"


def test_scan_dialog_cached_device(mocker, mock_scan_window):
    "Test scan_dialog with cached device list"
    mocker.patch("scan_menu_item_mixins.SaneScanDialog")
    mocker.patch("scan_menu_item_mixins.OCRControls")
    mocker.patch("scan_menu_item_mixins.RotateControls")

    mock_scan_window.settings["cache-device-list"] = True
    mock_scan_window.settings["device list"] = [
        SimpleNamespace(name="cached", label="cached")
    ]

    mock_scan_window.scan_dialog(None, None, scan=False)

    assert mock_scan_window._windows.device_list[0].name == "cached"


def test_add_postprocessing_options_clicked_cb(mocker, mock_scan_window):
    "Test add_postprocessing_options and the clicked-scan-button callback"
    mock_widget = mocker.Mock()
    mock_widget.notebook = mocker.Mock()
    # Capture callbacks
    callbacks = {}
    mock_widget.connect.side_effect = lambda s, c: callbacks.update({s: c})

    # Mock OCR and Rotate controls
    mock_rotate_cls = mocker.patch("scan_menu_item_mixins.RotateControls")
    mock_rotate = mock_rotate_cls.return_value
    mock_rotate.rotate_facing = 90
    mock_rotate.rotate_reverse = 180
    mock_scan_window._rotate_controls = mock_rotate

    mock_ocr_cls = mocker.patch("scan_menu_item_mixins.OCRControls")
    mock_ocr = mock_ocr_cls.return_value
    mock_ocr.active = True
    mock_ocr.engine = "tesseract"
    mock_ocr.language = "deu"
    mock_ocr.threshold = True
    mock_ocr.threshold_value = 50

    # Setup settings
    mock_scan_window.settings["user_defined_tools"] = ["my_tool"]

    mock_combo_cls = mocker.patch("scan_menu_item_mixins.ComboBoxText")
    mock_combo = mock_combo_cls.return_value
    mock_combo.get_active_text.return_value = "my_tool"

    import scan_menu_item_mixins

    mock_unpaper_btn = mocker.Mock()
    mock_udt_btn = mocker.Mock()
    scan_menu_item_mixins.Gtk.CheckButton.side_effect = [mock_unpaper_btn, mock_udt_btn]

    mock_unpaper_btn.get_active.return_value = True
    mock_udt_btn.get_active.return_value = True

    # Run
    mock_scan_window.add_postprocessing_options(mock_widget)

    # Trigger callback
    assert "clicked-scan-button" in callbacks
    callbacks["clicked-scan-button"](None)

    # Assertions
    assert mock_scan_window.settings["rotate facing"] == 90
    assert mock_scan_window.settings["rotate reverse"] == 180
    assert mock_scan_window.settings["unpaper on scan"] is True
    assert mock_scan_window.settings["udt_on_scan"] is True
    assert mock_scan_window.settings["current_udt"] == "my_tool"
    assert mock_scan_window.settings["OCR on scan"] is True
    assert mock_scan_window.settings["ocr engine"] == "tesseract"
    assert mock_scan_window.settings["ocr language"] == "deu"
    assert mock_scan_window.settings["threshold-before-ocr"] is True
    assert mock_scan_window.settings["threshold tool"] == 50


def test_add_postprocessing_options_ocr_fallback(mocker, mock_scan_window):
    "Test OCR engine fallback in clicked callback"
    mock_widget = mocker.Mock()
    callbacks = {}
    mock_widget.connect.side_effect = lambda s, c: callbacks.update({s: c})

    mocker.patch("scan_menu_item_mixins.RotateControls")
    mock_ocr_cls = mocker.patch("scan_menu_item_mixins.OCRControls")
    mock_ocr = mock_ocr_cls.return_value
    mock_ocr.active = True
    mock_ocr.engine = None  # Force fallback

    mock_scan_window._ocr_engine = [["fallback_eng", "Fallback"]]

    mock_scan_window.add_postprocessing_options(mock_widget)
    callbacks["clicked-scan-button"](None)

    assert mock_scan_window.settings["ocr engine"] == "fallback_eng"


def test_add_postprocessing_unpaper_disabled(mocker, mock_scan_window):
    "Test unpaper option when dependency missing"
    mock_scan_window._dependencies["unpaper"] = False
    mock_vbox = mocker.Mock()

    import scan_menu_item_mixins

    mock_btn = mocker.Mock()
    scan_menu_item_mixins.Gtk.CheckButton.return_value = mock_btn

    mock_scan_window._add_postprocessing_unpaper(mock_vbox)

    mock_btn.set_sensitive.assert_called_with(False)
    mock_btn.set_active.assert_called_with(False)


def test_add_postprocessing_unpaper_enabled_active(mocker, mock_scan_window):
    "Test unpaper option when enabled and active in settings"
    mock_scan_window._dependencies["unpaper"] = True
    mock_scan_window.settings["unpaper on scan"] = True
    mock_vbox = mocker.Mock()

    import scan_menu_item_mixins

    mock_btn = mocker.Mock()
    scan_menu_item_mixins.Gtk.CheckButton.return_value = mock_btn

    mock_scan_window._add_postprocessing_unpaper(mock_vbox)

    mock_btn.set_active.assert_called_with(True)


def test_add_postprocessing_udt_enabled(mocker, mock_scan_window):
    "Test UDT option when enabled"
    mock_scan_window.settings["user_defined_tools"] = ["tool1"]
    mock_scan_window.settings["udt_on_scan"] = True
    mock_vbox = mocker.Mock()

    import scan_menu_item_mixins

    mock_btn = mocker.Mock()
    scan_menu_item_mixins.Gtk.CheckButton.return_value = mock_btn

    mock_scan_window._add_postprocessing_udt(mock_vbox)

    mock_btn.set_active.assert_called_with(True)


def test_add_postprocessing_udt_disabled(mocker, mock_scan_window):
    "Test UDT option when no tools defined"
    mock_scan_window.settings["user_defined_tools"] = []
    mock_vbox = mocker.Mock()

    import scan_menu_item_mixins

    mock_btn = mocker.Mock()
    scan_menu_item_mixins.Gtk.CheckButton.return_value = mock_btn
    mock_hbox = mocker.Mock()
    scan_menu_item_mixins.Gtk.Box.return_value = mock_hbox

    mock_scan_window._add_postprocessing_udt(mock_vbox)

    mock_hbox.set_sensitive.assert_called_with(False)
    mock_btn.set_active.assert_called_with(False)


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


def test_changed_device_list_callback_empty(mock_scan_window):
    "Test _changed_device_list_callback with empty list"
    mock_widget = MagicMock()
    mock_scan_window._windows = mock_widget

    mock_scan_window._changed_device_list_callback(mock_widget, [])

    assert mock_scan_window._windows is None


def test_changed_device_list_callback_match_existing(mock_scan_window):
    "Test _changed_device_list_callback matches existing device setting"
    mock_widget = MagicMock()
    device1 = MagicMock()
    device1.name = "dev1"
    mock_scan_window.settings["device"] = "dev1"

    mock_scan_window._changed_device_list_callback(mock_widget, [device1])

    assert mock_widget.device == "dev1"


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


def test_update_postprocessing_options_callback(mock_scan_window):
    "Test _update_postprocessing_options_callback"
    mock_widget = MagicMock()
    mock_widget.page_number_increment = 1
    mock_options = MagicMock()
    mock_widget.available_scan_options = mock_options

    # Not duplex, increment 1
    mock_options.can_duplex.return_value = False
    mock_scan_window._update_postprocessing_options_callback(mock_widget)
    assert mock_scan_window._rotate_controls.can_duplex is False

    # Duplex
    mock_options.can_duplex.return_value = True
    mock_scan_window._update_postprocessing_options_callback(mock_widget)
    assert mock_scan_window._rotate_controls.can_duplex is True

    # Increment != 1
    mock_widget.page_number_increment = 2
    mock_options.can_duplex.return_value = False
    mock_scan_window._update_postprocessing_options_callback(mock_widget)
    assert mock_scan_window._rotate_controls.can_duplex is True


def test_changed_progress_callback(mock_scan_window):
    "Test _changed_progress_callback"
    # Normal update
    mock_scan_window._changed_progress_callback(None, 0.5, "halfway")
    mock_scan_window._scan_progress.set_fraction.assert_called_with(0.5)
    mock_scan_window._scan_progress.set_text.assert_called_with("halfway")

    # Pulse
    mock_scan_window._changed_progress_callback(None, None, None)
    mock_scan_window._scan_progress.pulse.assert_called()


def test_profile_callbacks(mock_scan_window):
    "Test profile related callbacks"
    # Changed profile
    mock_scan_window._changed_profile_callback(None, "new_prof")
    assert mock_scan_window.settings["default profile"] == "new_prof"

    # Added profile
    mock_profile = MagicMock()
    mock_profile.get.return_value = "pdata"
    mock_scan_window._added_profile_callback(None, "pname", mock_profile)
    assert mock_scan_window.settings["profile"]["pname"] == "pdata"


def test_new_scan_callback(mock_scan_window):
    "Test _new_scan_callback with normal flow"
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


def test_new_scan_callback_none_image(mock_scan_window):
    "Test _new_scan_callback with None image"
    mock_scan_window.slist.import_scan = MagicMock()
    mock_scan_window._new_scan_callback(None, None, 1, 300, 300)
    mock_scan_window.slist.import_scan.assert_not_called()


def test_new_scan_callback_options(mock_scan_window):
    "Test _new_scan_callback with various options"
    mock_image = MagicMock()
    mock_scan_window.slist.import_scan = MagicMock()

    # Enable options
    mock_scan_window.settings["unpaper on scan"] = True
    mock_scan_window.settings["threshold-before-ocr"] = True
    mock_scan_window.settings["threshold tool"] = 10
    mock_scan_window.settings["udt_on_scan"] = True
    mock_scan_window.settings["current_udt"] = "tool1"

    # Even page number -> rotate reverse
    mock_scan_window.settings["rotate reverse"] = 90
    mock_scan_window.settings["rotate facing"] = 180

    # Page 2 is even, 2 % 2 == 0, should use rotate reverse
    mock_scan_window._new_scan_callback(None, mock_image, 2, 300, 300)

    call_kwargs = mock_scan_window.slist.import_scan.call_args[1]
    assert call_kwargs["rotate"] == 90

    # Page 1 is odd, 1 % 2 == 1, should use rotate facing
    mock_scan_window._new_scan_callback(None, mock_image, 1, 300, 300)
    call_kwargs = mock_scan_window.slist.import_scan.call_args_list[1][1]
    assert call_kwargs["rotate"] == 180


def test_reloaded_scan_options_callback(mocker, mock_scan_window):
    "Test _reloaded_scan_options_callback"
    mock_widget = MagicMock()

    # 1. Default Profile
    mock_scan_window.settings["default profile"] = "def_prof"
    mock_scan_window._reloaded_scan_options_callback(mock_widget)
    assert mock_widget.profile == "def_prof"

    # 2. Default Scan Options
    del mock_scan_window.settings["default profile"]
    mock_scan_window.settings["default-scan-options"] = "some_opts"
    mock_profile_cls = mocker.patch("scan_menu_item_mixins.Profile")
    mock_scan_window._reloaded_scan_options_callback(mock_widget)
    mock_profile_cls.assert_called_with("some_opts")
    mock_widget.set_current_scan_options.assert_called()

    # 3. First Profile from list
    del mock_scan_window.settings["default-scan-options"]
    mock_scan_window.settings["profile"] = {"prof1": "data"}
    mock_scan_window._reloaded_scan_options_callback(mock_widget)
    assert mock_widget.profile == "prof1"

    # 4. No profiles
    mock_scan_window.settings["profile"] = {}
    mock_scan_window._reloaded_scan_options_callback(mock_widget)
    # Should just call _update_postprocessing_options_callback without crashing


def test_import_scan_finished_callback(mock_scan_window):
    "Test _import_scan_finished_callback"
    mock_response = MagicMock()
    mock_scan_window._import_scan_finished_callback(mock_response)
    mock_scan_window.post_process_progress.finish.assert_called_with(mock_response)


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
