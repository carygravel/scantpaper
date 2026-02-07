"Test tool_menu_mixins.py"

import datetime
import pytest
from tools_menu_mixins import ToolsMenuMixins
from const import _90_DEGREES, _180_DEGREES
import gi

# pylint: disable=redefined-outer-name, protected-access

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


@pytest.fixture
def mock_tool_window(mocker):
    "Fixture to provide a configured MockWindow"
    mock_app = mocker.Mock()

    class MockWindow(Gtk.Window, ToolsMenuMixins):
        "Test class to hold mixin"

        slist = None
        post_process_progress = None
        _display_callback = None
        _error_callback = None
        settings = {}

        # Attributes often used across tests, defined here to avoid AttributeError
        _windowc = None
        _windowu = None
        _windowo = None
        _windowe = None
        _current_page = None
        view = None
        _unpaper = None
        _ocr_engine = None
        _pref_udt_cmbx = None
        _dependencies = {}
        session = None

        def get_application(self, *args, **kwargs):  # pylint: disable=arguments-differ
            "mock"
            return mock_app

        def _show_message_dialog(self, **kwargs):
            "mock"

    # Instantiate
    window = MockWindow()

    # Common mocks
    window.slist = mocker.MagicMock()
    window.post_process_progress = mocker.Mock()
    window._display_callback = mocker.Mock()
    window._error_callback = mocker.Mock()

    yield window

    window.destroy()


def _trigger_apply(mock_dialog_instance):
    "Helper to find and trigger the apply/ok action"
    args, _ = mock_dialog_instance.add_actions.call_args
    apply_cb = next(cb for name, cb in args[0] if name in ("gtk-apply", "gtk-ok"))
    apply_cb()


def test_rotate_90(mock_tool_window):
    "Test rotate_90"

    mock_tool_window.slist.get_selected_indices.return_value = [0]
    mock_tool_window.slist.indices2pages.return_value = ["pageobject"]

    mock_tool_window.rotate_90(None, None)

    mock_tool_window.slist.rotate.assert_called_once()
    call_kwargs = mock_tool_window.slist.rotate.call_args[1]
    assert call_kwargs["angle"] == -_90_DEGREES
    assert call_kwargs["page"] == "pageobject"


def test_rotate_180(mock_tool_window):
    "Test rotate_180"

    mock_tool_window.slist.get_selected_indices.return_value = [0]
    mock_tool_window.slist.indices2pages.return_value = ["pageobject"]

    mock_tool_window.rotate_180(None, None)

    mock_tool_window.slist.rotate.assert_called_once()
    call_kwargs = mock_tool_window.slist.rotate.call_args[1]
    assert call_kwargs["angle"] == _180_DEGREES
    assert call_kwargs["page"] == "pageobject"


def test_rotate_270(mock_tool_window):
    "Test rotate_270"

    mock_tool_window.slist.get_selected_indices.return_value = [0]
    mock_tool_window.slist.indices2pages.return_value = ["pageobject"]

    mock_tool_window.rotate_270(None, None)

    mock_tool_window.slist.rotate.assert_called_once()
    call_kwargs = mock_tool_window.slist.rotate.call_args[1]
    assert call_kwargs["angle"] == _90_DEGREES
    assert call_kwargs["page"] == "pageobject"


def test_ocr_display_callback(mocker, mock_tool_window):
    "Test _ocr_display_callback"

    mock_tool_window.slist.find_page_by_uuid.return_value = 0
    mock_tool_window.slist.get_selected_indices.return_value = [0]
    mock_tool_window.slist.data = [[None, None, "uuid"]]

    mock_tool_window._create_txt_canvas = mocker.Mock()

    mock_response = mocker.Mock()
    mock_response.request.args = [{"page": "uuid"}]

    mock_tool_window._ocr_display_callback(mock_response)

    mock_tool_window._create_txt_canvas.assert_called_once_with("uuid")


def test_ocr_display_callback_page_not_found(mocker, mock_tool_window):
    "Test _ocr_display_callback when page not found"
    mock_tool_window.slist.find_page_by_uuid.return_value = None
    mock_tool_window._create_txt_canvas = mocker.Mock()
    mock_response = mocker.Mock()
    mock_response.request.args = [{"page": "uuid"}]

    mock_tool_window._ocr_display_callback(mock_response)
    mock_tool_window._create_txt_canvas.assert_not_called()


def test_ocr_display_callback_page_not_selected(mocker, mock_tool_window):
    "Test _ocr_display_callback when page not selected"
    mock_tool_window.slist.find_page_by_uuid.return_value = 0
    mock_tool_window.slist.get_selected_indices.return_value = [1]
    mock_tool_window._create_txt_canvas = mocker.Mock()
    mock_response = mocker.Mock()
    mock_response.request.args = [{"page": "uuid"}]

    mock_tool_window._ocr_display_callback(mock_response)
    mock_tool_window._create_txt_canvas.assert_not_called()


def test_threshold_dialog(mocker, mock_tool_window):
    "Test the threshold dialog"

    mock_dialog_cls = mocker.patch("tools_menu_mixins.Dialog")
    mock_dialog_instance = mock_dialog_cls.return_value
    mock_vbox = mocker.Mock()
    mock_dialog_instance.get_content_area.return_value = mock_vbox

    mock_tool_window.settings = {"threshold tool": 50}
    mock_tool_window.slist.get_page_index.return_value = [0]
    mock_tool_window.slist.data = [[0, 0, "uuid"]]

    mock_tool_window.threshold(None, None)

    mock_dialog_cls.assert_called()

    _trigger_apply(mock_dialog_instance)

    mock_tool_window.slist.threshold.assert_called_once()
    call_kwargs = mock_tool_window.slist.threshold.call_args[1]
    assert call_kwargs["threshold"] == 50
    assert call_kwargs["page"] == "uuid"

    # Execute finished callback
    finished_callback = call_kwargs["finished_callback"]
    finished_callback("response")
    mock_tool_window.post_process_progress.finish.assert_called_with("response")


def test_threshold_dialog_no_pages(mocker, mock_tool_window):
    "Test the threshold dialog with no pages selected"
    mock_dialog_cls = mocker.patch("tools_menu_mixins.Dialog")
    mock_dialog_instance = mock_dialog_cls.return_value
    mock_tool_window.settings = {"threshold tool": 50}
    mock_tool_window.slist.get_page_index.return_value = []

    mock_tool_window.threshold(None, None)

    _trigger_apply(mock_dialog_instance)

    mock_tool_window.slist.threshold.assert_not_called()


def test_brightness_contrast_dialog(mocker, mock_tool_window):
    "Test the brightness_contrast dialog"

    mock_dialog_cls = mocker.patch("tools_menu_mixins.Dialog")
    mock_dialog_instance = mock_dialog_cls.return_value
    mock_vbox = mocker.Mock()
    mock_dialog_instance.get_content_area.return_value = mock_vbox

    mock_tool_window.settings = {"brightness tool": 20, "contrast tool": 30}
    mock_tool_window.slist.get_page_index.return_value = [0]
    mock_tool_window.slist.data = [[0, 0, "uuid"]]

    mock_tool_window.brightness_contrast(None, None)

    mock_dialog_cls.assert_called()

    _trigger_apply(mock_dialog_instance)

    mock_tool_window.slist.brightness_contrast.assert_called_once()
    call_kwargs = mock_tool_window.slist.brightness_contrast.call_args[1]
    assert call_kwargs["brightness"] == 20
    assert call_kwargs["contrast"] == 30
    assert call_kwargs["page"] == "uuid"

    # Execute finished callback
    finished_callback = call_kwargs["finished_callback"]
    finished_callback("response")
    mock_tool_window.post_process_progress.finish.assert_called_with("response")


def test_brightness_contrast_no_pages(mocker, mock_tool_window):
    "Test brightness_contrast with no pages"
    mock_dialog_cls = mocker.patch("tools_menu_mixins.Dialog")
    mock_tool_window.settings = {"brightness tool": 20, "contrast tool": 30}
    mock_tool_window.slist.get_page_index.return_value = []

    mock_tool_window.brightness_contrast(None, None)
    _trigger_apply(mock_dialog_cls.return_value)

    mock_tool_window.slist.brightness_contrast.assert_not_called()


def test_negate_dialog(mocker, mock_tool_window):
    "Test the negate dialog"

    mock_dialog_cls = mocker.patch("tools_menu_mixins.Dialog")
    mock_dialog_instance = mock_dialog_cls.return_value
    mock_vbox = mocker.Mock()
    mock_dialog_instance.get_content_area.return_value = mock_vbox

    mock_tool_window.settings = {"Page range": "selected"}
    mock_tool_window.slist.get_page_index.return_value = [0]
    mock_tool_window.slist.data = [[0, 0, "uuid"]]

    mock_tool_window.negate(None, None)

    mock_dialog_cls.assert_called()

    _trigger_apply(mock_dialog_instance)

    mock_tool_window.slist.negate.assert_called_once()
    call_kwargs = mock_tool_window.slist.negate.call_args[1]
    assert call_kwargs["page"] == "uuid"

    # Execute finished callback
    finished_callback = call_kwargs["finished_callback"]
    finished_callback("response")
    mock_tool_window.post_process_progress.finish.assert_called_with("response")


def test_negate_no_pages(mocker, mock_tool_window):
    "Test negate with no pages"
    mock_dialog_cls = mocker.patch("tools_menu_mixins.Dialog")
    mock_tool_window.settings = {"Page range": "selected"}
    mock_tool_window.slist.get_page_index.return_value = []

    mock_tool_window.negate(None, None)
    _trigger_apply(mock_dialog_cls.return_value)

    mock_tool_window.slist.negate.assert_not_called()


def test_unsharp(mocker, mock_tool_window):
    "Test the unsharp dialog"

    mock_dialog_cls = mocker.patch("tools_menu_mixins.Dialog")
    mock_dialog_instance = mock_dialog_cls.return_value
    mock_vbox = mocker.Mock()
    mock_dialog_instance.get_content_area.return_value = mock_vbox

    mock_tool_window.settings = {
        "unsharp radius": 5.0,
        "unsharp percentage": 100,
        "unsharp threshold": 10,
        "Page range": "selected",
    }
    mock_tool_window.slist.get_page_index.return_value = [0]
    mock_tool_window.slist.data = [[0, 0, "uuid"]]

    mock_tool_window.unsharp(None, None)

    mock_dialog_cls.assert_called()

    _trigger_apply(mock_dialog_instance)

    mock_tool_window.slist.unsharp.assert_called_once()
    call_kwargs = mock_tool_window.slist.unsharp.call_args[1]
    assert call_kwargs["radius"] == 5.0
    assert call_kwargs["percent"] == 100
    assert call_kwargs["threshold"] == 10
    assert call_kwargs["page"] == "uuid"

    # Execute finished callback
    finished_callback = call_kwargs["finished_callback"]
    finished_callback("response")
    mock_tool_window.post_process_progress.finish.assert_called_with("response")


def test_unsharp_no_pages(mocker, mock_tool_window):
    "Test unsharp with no pages"
    mock_dialog_cls = mocker.patch("tools_menu_mixins.Dialog")
    mock_tool_window.settings = {
        "unsharp radius": 5,
        "unsharp percentage": 50,
        "unsharp threshold": 10,
        "Page range": "selected",
    }
    mock_tool_window.slist.get_page_index.return_value = []

    mock_tool_window.unsharp(None, None)
    _trigger_apply(mock_dialog_cls.return_value)

    mock_tool_window.slist.unsharp.assert_not_called()


def test_crop_dialog(mocker, mock_tool_window):
    "Test the crop dialog"

    mock_crop_cls = mocker.patch("tools_menu_mixins.Crop")
    mock_crop_instance = mock_crop_cls.return_value
    mock_crop_instance.page_range = "selected"

    mock_page = mocker.Mock()
    mock_page.get_size.return_value = (100, 50)
    mock_tool_window._current_page = mock_page

    mock_tool_window.slist.get_page_index.return_value = [0]
    mock_tool_window.slist.data = [[0, 0, "uuid"]]

    mock_selection = mocker.Mock()
    mock_selection.x = 10
    mock_selection.y = 10
    mock_selection.width = 50
    mock_selection.height = 50
    mock_tool_window.settings = {"selection": mock_selection}

    mock_tool_window.crop_dialog(None, None)

    mock_crop_cls.assert_called()

    _trigger_apply(mock_crop_instance)

    mock_tool_window.slist.crop.assert_called_once()
    call_kwargs = mock_tool_window.slist.crop.call_args[1]
    assert call_kwargs["x"] == 10
    assert call_kwargs["y"] == 10
    assert call_kwargs["w"] == 50
    assert call_kwargs["h"] == 50
    assert call_kwargs["page"] == "uuid"

    # Execute finished callback
    finished_callback = call_kwargs["finished_callback"]
    finished_callback("response")
    mock_tool_window.post_process_progress.finish.assert_called_with("response")


def test_crop_dialog_existing(mocker, mock_tool_window):
    "Test the crop dialog when already open"
    mock_tool_window._windowc = mocker.Mock()
    mock_tool_window.crop_dialog(None, None)
    mock_tool_window._windowc.present.assert_called_once()


def test_crop_selection_no_selection(mock_tool_window):
    "Test crop_selection with no selection in settings"
    mock_tool_window.settings = {"selection": None}
    mock_tool_window.crop_selection(None, None)
    mock_tool_window.slist.crop.assert_not_called()


def test_crop_selection_no_pages(mock_tool_window):
    "Test crop_selection with no pages selected"
    mock_tool_window.settings = {"selection": "something"}
    mock_tool_window.slist.get_selected_indices.return_value = []
    mock_tool_window.crop_selection(None, None)
    mock_tool_window.slist.crop.assert_not_called()


def test_crop_dialog_selection_change(mocker, mock_tool_window):
    "Test that selection changes in crop dialog update settings and view"

    mock_crop_cls = mocker.patch("tools_menu_mixins.Crop")
    mock_crop_instance = mock_crop_cls.return_value
    mock_crop_instance.page_range = "selected"

    mock_page = mocker.Mock()
    mock_page.get_size.return_value = (100, 50)
    mock_tool_window._current_page = mock_page

    mock_tool_window.view = mocker.Mock()
    mock_tool_window.slist.get_page_index.return_value = [0]
    mock_tool_window.settings = {"selection": None}

    mock_tool_window.crop_dialog(None, None)

    on_changed_selection = None
    for call in mock_crop_instance.connect.call_args_list:
        if call[0][0] == "changed-selection":
            on_changed_selection = call[0][1]
            break

    assert on_changed_selection is not None, "Could not find changed-selection callback"

    mock_selection = mocker.Mock()
    mock_selection.copy.return_value = mock_selection

    on_changed_selection(None, mock_selection)

    assert mock_tool_window.settings["selection"] == mock_selection

    mock_tool_window.view.handler_block.assert_called()
    mock_tool_window.view.set_selection.assert_called_with(mock_selection)
    mock_tool_window.view.handler_unblock.assert_called()


def test_split_dialog(mocker, mock_tool_window):
    "Test the split dialog"

    mock_dialog_cls = mocker.patch("tools_menu_mixins.Dialog")
    mock_dialog_instance = mock_dialog_cls.return_value

    mock_page = mocker.Mock()
    mock_page.get_size.return_value = (100, 50)
    mock_tool_window._current_page = mock_page

    mock_tool_window.view = mocker.Mock()
    mock_tool_window.slist.get_page_index.return_value = [0]
    mock_tool_window.settings = {}

    mock_tool_window.split_dialog(None, None)

    mock_dialog_cls.assert_called()

    _trigger_apply(mock_dialog_instance)

    mock_tool_window.slist.split_page.assert_called_once()

    # Execute finished callback
    call_kwargs = mock_tool_window.slist.split_page.call_args[1]
    finished_callback = call_kwargs["finished_callback"]
    finished_callback("response")
    mock_tool_window.post_process_progress.finish.assert_called_with("response")


def test_split_dialog_interaction(mocker, mock_tool_window):
    "Test split dialog interaction including horizontal split"
    mock_dialog_cls = mocker.patch("tools_menu_mixins.Dialog")
    mock_dialog = mock_dialog_cls.return_value
    mock_dialog.get_content_area.return_value = mocker.Mock()  # vbox

    # Patch Gtk.Box to avoid TypeError when packing mock widgets
    mocker.patch("tools_menu_mixins.Gtk.Box")

    # Mock ComboBoxText which is imported in tools_menu_mixins
    mock_combo_cls = mocker.patch("tools_menu_mixins.ComboBoxText")
    mock_combo = mock_combo_cls.return_value

    # Mock SpinButton
    mock_spin_cls = mocker.patch("gi.repository.Gtk.SpinButton.new_with_range")
    mock_spin = mock_spin_cls.return_value
    mock_spin.get_value.return_value = 50

    mock_page = mocker.Mock()
    mock_page.get_size.return_value = (100, 100)
    mock_tool_window._current_page = mock_page
    mock_tool_window.view = mocker.Mock()
    mock_tool_window.slist.get_page_index.return_value = [0]
    mock_tool_window.settings = {}

    # 1. Open dialog
    mock_tool_window.split_dialog(None, None)

    # Extract callbacks
    # ComboBox changed
    combo_changed_cb = mock_combo.connect.call_args_list[0][0][1]

    # 2. Test Horizontal change
    # direction data is [["v", ...], ["h", ...]]
    # mock get_active to return 1 (horizontal)
    mock_combo.get_active.return_value = 1
    combo_changed_cb(None)

    # Verify _update_view_position called for H
    # We can check set_selection on view
    args, _ = mock_tool_window.view.set_selection.call_args
    selection = args[0]
    assert selection.width == 100
    # selection.height should be 50 (spin value)

    # 3. Test Apply callback with H
    args, _ = mock_dialog.add_actions.call_args
    actions = args[0]
    apply_cb = next(cb for name, cb in actions if name == "gtk-apply")
    apply_cb()

    mock_tool_window.slist.split_page.assert_called_with(
        direction="h",
        position=50,
        page=mocker.ANY,
        queued_callback=mocker.ANY,
        started_callback=mocker.ANY,
        running_callback=mocker.ANY,
        finished_callback=mocker.ANY,
        error_callback=mocker.ANY,
        display_callback=mocker.ANY,
    )

    # 4. Test Cancel callback
    cancel_cb = next(cb for name, cb in actions if name == "gtk-cancel")
    cancel_cb()
    mock_dialog.destroy.assert_called()
    mock_tool_window.view.disconnect.assert_called()


def test_split_no_pages(mocker, mock_tool_window):
    "Test split with no pages"
    mock_dialog_cls = mocker.patch("tools_menu_mixins.Dialog")
    mocker.patch("tools_menu_mixins.ComboBoxText")
    mocker.patch("tools_menu_mixins.Gtk.Box")

    mock_tool_window._current_page = mocker.Mock()
    mock_tool_window._current_page.get_size.return_value = (100, 100)
    mock_tool_window.view = mocker.Mock()

    mock_tool_window.slist.get_page_index.return_value = []

    mock_tool_window.split_dialog(None, None)
    _trigger_apply(mock_dialog_cls.return_value)

    mock_tool_window.slist.split_page.assert_not_called()


def test_split_selection_changed(mocker, mock_tool_window):
    "Test split dialog selection changed on view"
    mocker.patch("tools_menu_mixins.Dialog")
    mock_combo_cls = mocker.patch("tools_menu_mixins.ComboBoxText")
    mock_combo = mock_combo_cls.return_value
    mock_combo.get_active.return_value = 0
    mocker.patch("tools_menu_mixins.Gtk.Box")
    mock_spin = mocker.patch("gi.repository.Gtk.SpinButton.new_with_range").return_value

    mock_tool_window._current_page = mocker.Mock()
    mock_tool_window._current_page.get_size.return_value = (100, 100)
    mock_tool_window.view = mocker.Mock()
    mock_tool_window.split_dialog(None, None)

    args, _ = mock_tool_window.view.connect.call_args
    assert args[0] == "selection-changed"
    callback = args[1]

    selection = mocker.Mock()
    selection.x = 10
    selection.width = 20
    selection.y = 5
    selection.height = 10

    # direction "v" (default)
    callback(None, selection)
    mock_spin.set_value.assert_called_with(30)  # 10 + 20


def test_split_selection_changed_h(mocker, mock_tool_window):
    "Test split dialog selection changed on view"
    mocker.patch("tools_menu_mixins.Dialog")
    mock_combo_cls = mocker.patch("tools_menu_mixins.ComboBoxText")
    mock_combo = mock_combo_cls.return_value
    mock_combo.get_active.return_value = 1
    mocker.patch("tools_menu_mixins.Gtk.Box")
    mock_spin = mocker.patch("gi.repository.Gtk.SpinButton.new_with_range").return_value

    mock_tool_window._current_page = mocker.Mock()
    mock_tool_window._current_page.get_size.return_value = (100, 100)
    mock_tool_window.view = mocker.Mock()
    mock_tool_window.split_dialog(None, None)

    args, _ = mock_tool_window.view.connect.call_args
    assert args[0] == "selection-changed"
    callback = args[1]

    selection = mocker.Mock()
    selection.x = 10
    selection.width = 20
    selection.y = 5
    selection.height = 10

    # direction "h"
    callback(None, selection)
    mock_spin.set_value.assert_called_with(15)  # 10 + 5


def test_unpaper_dialog(mocker, mock_tool_window):
    "Test the unpaper dialog"

    mock_dialog_cls = mocker.patch("tools_menu_mixins.Dialog")
    mock_dialog_instance = mock_dialog_cls.return_value
    mock_vbox = mocker.Mock()
    mock_dialog_instance.get_content_area.return_value = mock_vbox

    mock_tool_window.settings = {}
    mock_tool_window.slist.get_page_index.return_value = [0]
    mock_tool_window.slist.indices2pages.return_value = ["pageobject"]

    mock_unpaper = mocker.Mock()
    mock_unpaper.get_options.return_value = {}
    mock_unpaper.get_cmdline.return_value = ["unpaper"]
    mock_unpaper.get_option.return_value = "direction"
    mock_tool_window._unpaper = mock_unpaper

    mock_tool_window.unpaper_dialog(None, None)

    mock_dialog_cls.assert_called()

    _trigger_apply(mock_dialog_instance)

    mock_tool_window.slist.unpaper.assert_called_once()
    call_kwargs = mock_tool_window.slist.unpaper.call_args[1]
    assert call_kwargs["options"]["command"] == ["unpaper"]
    assert call_kwargs["options"]["direction"] == "direction"
    assert call_kwargs["page"] == "pageobject"

    # Execute finished callback
    finished_callback = call_kwargs["finished_callback"]
    finished_callback("response")
    mock_tool_window.post_process_progress.finish.assert_called_with("response")


def test_unpaper_dialog_existing(mocker, mock_tool_window):
    "Test unpaper_dialog when already open"
    mock_tool_window._windowu = mocker.Mock()
    mock_tool_window.unpaper_dialog(None, None)
    mock_tool_window._windowu.present.assert_called_once()


def test_ocr_dialog(mocker, mock_tool_window):
    "Test the ocr dialog"

    mock_dialog_cls = mocker.patch("tools_menu_mixins.Dialog")
    mock_dialog_instance = mock_dialog_cls.return_value
    mock_vbox = mocker.Mock()
    mock_dialog_instance.get_content_area.return_value = mock_vbox

    mock_ocr_controls_cls = mocker.patch("tools_menu_mixins.OCRControls")
    mock_ocr_controls_instance = mock_ocr_controls_cls.return_value
    mock_ocr_controls_instance.engine = "tesseract"
    mock_ocr_controls_instance.language = "eng"
    mock_ocr_controls_instance.threshold = True
    mock_ocr_controls_instance.threshold_value = 50

    mock_tool_window.settings = {
        "ocr engine": "tesseract",
        "ocr language": "eng",
        "OCR on scan": False,
        "threshold-before-ocr": False,
        "threshold tool": 0,
    }
    mock_tool_window._ocr_engine = ["tesseract"]
    mock_tool_window.slist.get_page_index.return_value = [0]
    mock_tool_window.slist.indices2pages.return_value = ["pageobject"]

    mock_tool_window._ocr_finished_callback = mocker.Mock()
    mock_tool_window._ocr_display_callback = mocker.Mock()

    mock_tool_window.ocr_dialog(None, None)

    mock_dialog_cls.assert_called()
    mock_ocr_controls_cls.assert_called()

    _trigger_apply(mock_dialog_instance)

    mock_tool_window.slist.ocr_pages.assert_called_once()
    call_kwargs = mock_tool_window.slist.ocr_pages.call_args[1]
    assert call_kwargs["engine"] == "tesseract"
    assert call_kwargs["language"] == "eng"
    assert call_kwargs["threshold"] == 50
    assert call_kwargs["pages"] == ["pageobject"]


def test_ocr_dialog_no_pages(mocker, mock_tool_window):
    "Test the ocr dialog"

    mock_dialog_cls = mocker.patch("tools_menu_mixins.Dialog")
    mock_dialog_instance = mock_dialog_cls.return_value
    mock_vbox = mocker.Mock()
    mock_dialog_instance.get_content_area.return_value = mock_vbox

    mock_ocr_controls_cls = mocker.patch("tools_menu_mixins.OCRControls")
    mock_ocr_controls_instance = mock_ocr_controls_cls.return_value
    mock_ocr_controls_instance.engine = "tesseract"
    mock_ocr_controls_instance.language = "eng"
    mock_ocr_controls_instance.threshold = True
    mock_ocr_controls_instance.threshold_value = 50

    mock_tool_window.settings = {
        "ocr engine": "tesseract",
        "ocr language": "eng",
        "OCR on scan": False,
        "threshold-before-ocr": False,
        "threshold tool": 0,
    }
    mock_tool_window._ocr_engine = ["tesseract"]
    mock_tool_window.slist.get_page_index.return_value = []
    mock_tool_window.slist.indices2pages.return_value = []

    mock_tool_window._ocr_finished_callback = mocker.Mock()
    mock_tool_window._ocr_display_callback = mocker.Mock()

    mock_tool_window.ocr_dialog(None, None)

    mock_dialog_cls.assert_called()
    mock_ocr_controls_cls.assert_called()

    _trigger_apply(mock_dialog_instance)


def test_ocr_dialog_existing(mocker, mock_tool_window):
    "Test ocr_dialog when already open"
    mock_tool_window._windowo = mocker.Mock()
    mock_tool_window.ocr_dialog(None, None)
    mock_tool_window._windowo.present.assert_called_once()


def test_user_defined_dialog(mocker, mock_tool_window):
    "Test the user_defined_dialog"

    mock_dialog_cls = mocker.patch("tools_menu_mixins.Dialog")
    mock_dialog_instance = mock_dialog_cls.return_value
    mock_vbox = mocker.Mock()
    mock_dialog_instance.get_content_area.return_value = mock_vbox

    mock_tool_window.settings = {"current_udt": "", "Page range": "selected"}
    mock_tool_window.slist.get_page_index.return_value = [0]
    mock_tool_window.slist.indices2pages.return_value = ["pageobject"]

    mock_combobox = mocker.Mock()
    mock_combobox.get_active_text.return_value = "my-tool"
    mock_tool_window._pref_udt_cmbx = mock_combobox

    # We can inject the method
    mock_tool_window._add_udt_combobox = lambda _hbox: mock_tool_window._pref_udt_cmbx

    mock_tool_window.user_defined_dialog(None, None)

    mock_dialog_cls.assert_called()

    _trigger_apply(mock_dialog_instance)

    mock_tool_window.slist.user_defined.assert_called_once()
    call_kwargs = mock_tool_window.slist.user_defined.call_args[1]
    assert call_kwargs["command"] == "my-tool"
    assert call_kwargs["page"] == "pageobject"

    # Execute finished callback
    finished_callback = call_kwargs["finished_callback"]
    finished_callback("response")
    mock_tool_window.post_process_progress.finish.assert_called_with("response")


def test_user_defined_no_pages(mocker, mock_tool_window):
    "Test user_defined with no pages"
    mock_dialog_cls = mocker.patch("tools_menu_mixins.Dialog")
    mock_tool_window.settings = {"Page range": "selected"}
    mock_tool_window.slist.get_page_index.return_value = []
    # mock combobox creation
    mock_tool_window._add_udt_combobox = lambda x: mocker.Mock()

    mock_tool_window.user_defined_dialog(None, None)
    _trigger_apply(mock_dialog_cls.return_value)

    mock_tool_window.slist.user_defined.assert_not_called()


def test_email_dialog(mocker, mock_tool_window):
    "Test the email dialog"

    mock_save_dialog_cls = mocker.patch("tools_menu_mixins.SaveDialog")
    mock_save_dialog_instance = mock_save_dialog_cls.return_value
    mock_save_dialog_instance.pdf_user_password = "password"
    mock_save_dialog_instance.page_range = "all"
    mock_save_dialog_instance.downsample = False
    mock_save_dialog_instance.downsample_dpi = 300
    mock_save_dialog_instance.pdf_compression = "auto"
    mock_save_dialog_instance.jpeg_quality = 75
    mock_save_dialog_instance.meta_datetime = "now"

    mocker.patch("tools_menu_mixins.expand_metadata_pattern", return_value="doc")
    mocker.patch("tools_menu_mixins.collate_metadata", return_value={})

    mock_tool_window.settings = {
        "Page range": "all",
        "use_time": True,
        "datetime offset": datetime.timedelta(0),
        "title": "Title",
        "title-suggestions": [],
        "author": "Author",
        "author-suggestions": [],
        "subject": "Subject",
        "subject-suggestions": [],
        "keywords": "Keywords",
        "keywords-suggestions": [],
        "quality": 75,
        "downsample dpi": 300,
        "downsample": False,
        "pdf compression": "auto",
        "default filename": "doc",
        "convert whitespace to underscores": True,
    }

    mock_tool_window.session = mocker.Mock()
    mock_tool_window.session.name = "session_name"
    mock_tool_window._list_of_page_uuids = mocker.Mock(return_value=["uuid1", "uuid2"])

    mock_tool_window.email(None, None)

    mock_save_dialog_cls.assert_called()

    _trigger_apply(mock_save_dialog_instance)

    mock_tool_window.slist.save_pdf.assert_called_once()
    call_kwargs = mock_tool_window.slist.save_pdf.call_args[1]
    assert call_kwargs["path"] == "session_name/doc.pdf"
    assert call_kwargs["list_of_pages"] == ["uuid1", "uuid2"]
    assert call_kwargs["options"]["user-password"] == "password"


def test_email_dialog_existing(mocker, mock_tool_window):
    "Test email dialog when already open"
    mock_tool_window._windowe = mocker.Mock()
    mock_tool_window.email(None, None)
    mock_tool_window._windowe.present.assert_called_once()


def test_email_execution_flow(mocker, mock_tool_window):
    "Test email execution including success and failure callback"

    mock_save_dialog_cls = mocker.patch("tools_menu_mixins.SaveDialog")
    mock_save_dialog = mock_save_dialog_cls.return_value
    mock_save_dialog.meta_datetime = datetime.datetime.now()
    # Mock attributes accessed in callback
    mock_save_dialog.downsample = False
    mock_save_dialog.downsample_dpi = 300
    mock_save_dialog.pdf_compression = "auto"
    mock_save_dialog.jpeg_quality = 75
    mock_save_dialog.pdf_user_password = ""

    mocker.patch("tools_menu_mixins.expand_metadata_pattern", return_value="doc")
    mocker.patch("tools_menu_mixins.collate_metadata", return_value={})
    mock_exec = mocker.patch("tools_menu_mixins.exec_command", return_value=0)
    mock_launch = mocker.patch("tools_menu_mixins.launch_default_for_file")
    mock_tool_window._show_message_dialog = mocker.Mock()

    mock_tool_window.settings = {
        "Page range": "all",
        "use_time": True,
        "datetime offset": datetime.timedelta(0),
        "title": "",
        "title-suggestions": [],
        "author": "",
        "author-suggestions": [],
        "subject": "",
        "subject-suggestions": [],
        "keywords": "",
        "keywords-suggestions": [],
        "quality": 75,
        "downsample dpi": 300,
        "downsample": False,
        "pdf compression": "auto",
        "default filename": "doc",
        "convert whitespace to underscores": True,
        "view files toggle": True,
    }
    mock_tool_window.session = mocker.Mock()
    mock_tool_window.session.name = "sess"
    mock_tool_window._list_of_page_uuids = mocker.Mock(return_value=["uuid"])
    mock_tool_window.slist.thread = mocker.Mock()

    # 1. Call email
    mock_tool_window.email(None, None)

    # 2. Trigger OK
    _trigger_apply(mock_save_dialog)

    # 3. Extract save_pdf finished_callback
    call_kwargs = mock_tool_window.slist.save_pdf.call_args[1]
    finished_callback = call_kwargs["finished_callback"]

    # 4. Call finished callback (Success case)
    finished_callback("response")

    # 5. Assertions
    mock_launch.assert_called_with("sess/doc.pdf")
    mock_exec.assert_called()
    mock_tool_window._show_message_dialog.assert_not_called()

    # Reset for failure test
    mock_exec.return_value = 1
    finished_callback("response")
    mock_tool_window._show_message_dialog.assert_called()


def test_email_default_filename(mocker, mock_tool_window):
    "Test email default filename fallback"

    mock_save_dialog_cls = mocker.patch("tools_menu_mixins.SaveDialog")
    mock_save_dialog = mock_save_dialog_cls.return_value
    mock_save_dialog.meta_datetime = datetime.datetime.now()
    mock_save_dialog.downsample = False
    mock_save_dialog.downsample_dpi = 300
    mock_save_dialog.pdf_compression = "auto"
    mock_save_dialog.jpeg_quality = 75
    mock_save_dialog.pdf_user_password = ""

    # Force empty filename from expand_metadata_pattern
    mocker.patch("tools_menu_mixins.expand_metadata_pattern", return_value="   ")
    mocker.patch("tools_menu_mixins.collate_metadata", return_value={})
    mocker.patch("tools_menu_mixins.exec_command", return_value=0)
    mocker.patch("tools_menu_mixins.launch_default_for_file")

    mock_tool_window.settings = {
        "Page range": "all",
        "use_time": True,
        "datetime offset": datetime.timedelta(0),
        "title": "",
        "title-suggestions": [],
        "author": "",
        "author-suggestions": [],
        "subject": "",
        "subject-suggestions": [],
        "keywords": "",
        "keywords-suggestions": [],
        "quality": 75,
        "downsample dpi": 300,
        "downsample": False,
        "pdf compression": "auto",
        "default filename": "doc",
        "convert whitespace to underscores": True,
        "view files toggle": False,
    }
    mock_tool_window.session = mocker.Mock()
    mock_tool_window.session.name = "sess"
    mock_tool_window._list_of_page_uuids = mocker.Mock(return_value=["uuid"])
    mock_tool_window.slist.thread = mocker.Mock()

    mock_tool_window.email(None, None)
    _trigger_apply(mock_save_dialog_cls.return_value)

    # Check that filename became "document"
    call_kwargs = mock_tool_window.slist.save_pdf.call_args[1]
    assert call_kwargs["path"] == "sess/document.pdf"


def test_about_dialog_runs(mocker, mock_tool_window):
    "Test that ToolsMenuMixins.about runs without error"

    mock_about_dialog = mocker.patch("gi.repository.Gtk.AboutDialog")
    mocker.patch("gi.repository.GdkPixbuf.Pixbuf.new_from_file")

    mock_tool_window.get_application().iconpath = "."

    mock_tool_window.about(None, None)

    mock_about_dialog.assert_called_once()
    instance = mock_about_dialog.return_value
    instance.run.assert_called_once()
    instance.destroy.assert_called_once()

    instance.set_program_name.assert_called()
    instance.set_version.assert_called()
    instance.set_website.assert_called()
    instance.set_logo.assert_called()
