"Tests for the EditMenuMixins."

import datetime
from unittest.mock import MagicMock
import pytest
import gi
from edit_menu_mixins import EditMenuMixins

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


@pytest.fixture
def mock_edit_window(mocker):
    "Fixture to provide a configured MockWindow"
    mock_app = mocker.Mock()

    class MockWindow(Gtk.Window, EditMenuMixins):
        "Test class to hold mixin"

        slist = None
        post_process_progress = None
        t_canvas = None
        settings = {}
        _windowp = None
        _windowr = None
        _windows = None
        _windowi = None
        _pref_udt_cmbx = None
        _scan_udt_cmbx = None

        # Callbacks and methods used by mixins
        _update_uimanager = mocker.Mock()
        _show_message_dialog = mocker.Mock()
        _ask_question = mocker.Mock(return_value=Gtk.ResponseType.OK)
        _restart = mocker.Mock()
        _update_post_save_hooks = mocker.Mock()
        _error_callback = mocker.Mock()

        def get_application(self, *args, **kwargs):  # pylint: disable=arguments-differ
            "mock"
            return mock_app

    # Instantiate
    window = MockWindow()

    # Common mocks
    window.slist = mocker.MagicMock()
    window.post_process_progress = mocker.Mock()
    window.t_canvas = mocker.Mock()

    # Default settings
    window.settings = {
        "device blacklist": "",
        "cycle sane handle": False,
        "cancel-between-pages": False,
        "allow-batch-flatbed": False,
        "ignore-duplex-capabilities": False,
        "use_time": False,
        "user_defined_tools": [],
        "current_udt": "",
        "TMPDIR": "/tmp",
        "Blank threshold": 0.5,
        "Dark threshold": 0.5,
    }

    yield window

    window.destroy()


def test_undo(mock_edit_window):
    "Test undo"
    mock_edit_window.undo(None, None)
    mock_edit_window.slist.undo.assert_called_once()
    mock_edit_window._update_uimanager.assert_called_once()


def test_unundo(mock_edit_window):
    "Test unundo"
    mock_edit_window.unundo(None, None)
    mock_edit_window.slist.unundo.assert_called_once()
    mock_edit_window._update_uimanager.assert_called_once()


def test_cut_selection(mock_edit_window):
    "Test cut_selection"
    mock_edit_window.slist.cut_selection.return_value = "clipboard_data"
    mock_edit_window.cut_selection(None, None)
    mock_edit_window.slist.cut_selection.assert_called_once()
    assert mock_edit_window.slist.clipboard == "clipboard_data"
    mock_edit_window._update_uimanager.assert_called_once()


def test_copy_selection(mock_edit_window):
    "Test copy_selection"
    mock_edit_window.slist.copy_selection.return_value = "clipboard_data"
    mock_edit_window.copy_selection(None, None)
    mock_edit_window.slist.copy_selection.assert_called_once()
    assert mock_edit_window.slist.clipboard == "clipboard_data"
    mock_edit_window._update_uimanager.assert_called_once()


def test_paste_selection_empty(mock_edit_window):
    "Test paste_selection with empty clipboard"
    mock_edit_window.slist.clipboard = None
    mock_edit_window.paste_selection(None, None)
    mock_edit_window.slist.paste_selection.assert_not_called()


def test_paste_selection_with_pages(mock_edit_window):
    "Test paste_selection with selected pages"
    mock_edit_window.slist.clipboard = "data"
    mock_edit_window.slist.get_selected_indices.return_value = [0, 1]

    mock_edit_window.paste_selection(None, None)

    mock_edit_window.slist.paste_selection.assert_called_once_with(
        data="data", dest=1, how="after", select_new_pages=True
    )
    mock_edit_window._update_uimanager.assert_called_once()


def test_paste_selection_no_pages(mock_edit_window):
    "Test paste_selection without selected pages"
    mock_edit_window.slist.clipboard = "data"
    mock_edit_window.slist.get_selected_indices.return_value = []

    mock_edit_window.paste_selection(None, None)

    mock_edit_window.slist.paste_selection.assert_called_once_with(
        data="data", select_new_pages=True
    )
    mock_edit_window._update_uimanager.assert_called_once()


def test_delete_selection(mock_edit_window):
    "Test delete_selection"
    mock_windows = MagicMock()
    mock_edit_window._windows = mock_windows

    mock_edit_window.delete_selection(None, None)

    mock_edit_window.slist.delete_selection_extra.assert_called_once()
    mock_windows.reset_start_page.assert_called_once()
    mock_edit_window._update_uimanager.assert_called_once()


def test_select_all(mock_edit_window):
    "Test select_all"
    mock_selection = MagicMock()
    mock_edit_window.slist.get_selection.return_value = mock_selection

    mock_edit_window.select_all(None, None)

    mock_selection.select_all.assert_called_once()


def test_select_odd_even(mock_edit_window):
    "Test select_odd_even"
    # Data structure: [index, ?, page]
    # Use 1-based page numbers for logic check: 1=Odd, 2=Even, 3=Odd
    mock_edit_window.slist.data = [[1, None, None], [2, None, None], [3, None, None]]
    mock_selection = MagicMock()
    mock_edit_window.slist.get_selection.return_value = mock_selection

    # Test Odd (0) -> select indices 0, 2
    mock_edit_window.select_odd_even(0)
    mock_selection.unselect_all.assert_called_once()
    mock_edit_window.slist.select.assert_called_with([0, 2])

    mock_selection.reset_mock()
    mock_edit_window.slist.select.reset_mock()

    # Test Even (1) -> select index 1
    mock_edit_window.select_odd_even(1)
    mock_selection.unselect_all.assert_called_once()
    mock_edit_window.slist.select.assert_called_with([1])


def test_select_invert(mock_edit_window):
    "Test select_invert"
    mock_edit_window.slist.data = [[0], [1], [2]]
    mock_edit_window.slist.get_selected_indices.return_value = [0]
    mock_selection = MagicMock()
    mock_edit_window.slist.get_selection.return_value = mock_selection

    mock_edit_window.select_invert(None, None)

    mock_selection.unselect_all.assert_called_once()
    mock_edit_window.slist.select.assert_called_once_with([1, 2])


def test_select_modified_since_ocr(mock_edit_window):
    "Test select_modified_since_ocr"
    page1 = MagicMock()
    page1.ocr_flag = True
    page1.ocr_time = datetime.datetime(2023, 1, 1)
    page1.dirty_time = datetime.datetime(2023, 1, 2)  # Dirty after OCR

    page2 = MagicMock()
    page2.ocr_flag = True
    page2.ocr_time = datetime.datetime(2023, 1, 2)
    page2.dirty_time = datetime.datetime(2023, 1, 1)  # Clean

    page3 = MagicMock()
    page3.ocr_flag = False  # No OCR

    mock_edit_window.slist.data = [[0, 0, page1], [1, 0, page2], [2, 0, page3]]
    mock_selection = MagicMock()
    mock_edit_window.slist.get_selection.return_value = mock_selection

    mock_edit_window.select_modified_since_ocr(None, None)

    mock_selection.unselect_all.assert_called_once()
    mock_edit_window.slist.select.assert_called_once_with([0])


def test_select_no_ocr(mock_edit_window):
    "Test select_no_ocr"
    page1 = MagicMock()
    page1.text_layer = "text"

    page2 = MagicMock()
    page2.text_layer = None

    mock_edit_window.slist.data = [[0, 0, page1], [1, 0, page2]]
    mock_selection = MagicMock()
    mock_edit_window.slist.get_selection.return_value = mock_selection

    mock_edit_window.select_no_ocr(None, None)

    mock_selection.unselect_all.assert_called_once()
    mock_edit_window.slist.select.assert_called_once_with([1])


def test_clear_ocr(mock_edit_window):
    "Test clear_ocr"
    page1 = MagicMock()
    page1.text_layer = "text"

    mock_edit_window.slist.get_selected_indices.return_value = [0]
    mock_edit_window.slist.data = [[0, 0, page1]]

    mock_edit_window.clear_ocr(None, None)

    mock_edit_window.t_canvas.clear_text.assert_called_once()
    assert page1.text_layer is None


def test_properties_dialog(mocker, mock_edit_window):
    "Test properties dialog"
    mock_dialog_cls = mocker.patch("edit_menu_mixins.Dialog")
    mock_dialog_instance = mock_dialog_cls.return_value
    mock_vbox = mocker.Mock()
    mock_dialog_instance.get_content_area.return_value = mock_vbox

    # Mock Gtk widgets used in the method
    mocker.patch("gi.repository.Gtk.Box")
    mocker.patch("gi.repository.Gtk.Label")
    mock_spin_button = mocker.patch("gi.repository.Gtk.SpinButton")
    mock_x_spin = MagicMock()
    mock_y_spin = MagicMock()
    mock_spin_button.new_with_range.side_effect = [mock_x_spin, mock_y_spin]

    mock_edit_window.slist.get_selected_properties.return_value = (150, 150)
    mock_selection = MagicMock()
    mock_edit_window.slist.get_selection.return_value = mock_selection

    mock_edit_window.properties(None, None)

    mock_dialog_cls.assert_called_once()
    mock_x_spin.set_value.assert_called_with(150)

    # Test apply callback
    args, _kwargs = mock_dialog_instance.add_actions.call_args
    actions = args[0]
    apply_callback = None
    for action_name, callback in actions:
        if action_name == "gtk-ok":
            apply_callback = callback
            break

    assert apply_callback

    mock_x_spin.get_value.return_value = 300
    mock_y_spin.get_value.return_value = 300
    mock_edit_window.slist.get_selected_indices.return_value = [0]
    page = MagicMock()
    mock_edit_window.slist.data = [[0, 0, page]]

    apply_callback()

    mock_dialog_instance.hide.assert_called()
    assert page.resolution == (300, 300, "PixelsPerInch")


def test_renumber_dialog(mocker, mock_edit_window):
    "Test renumber_dialog"
    mock_renumber_cls = mocker.patch("edit_menu_mixins.Renumber")
    mock_renumber_instance = mock_renumber_cls.return_value

    mock_edit_window.renumber_dialog(None, None)

    mock_renumber_cls.assert_called_with(
        transient_for=mock_edit_window,
        document=mock_edit_window.slist,
        hide_on_delete=False,
    )
    mock_renumber_instance.show_all.assert_called_once()

    # Verify signal connection
    assert mock_renumber_instance.connect.call_count >= 1


def test_preferences_dialog(mocker, mock_edit_window):
    "Test preferences dialog"
    mock_pref_cls = mocker.patch("edit_menu_mixins.PreferencesDialog")
    mock_pref_instance = mock_pref_cls.return_value

    mock_edit_window.preferences(None, None)

    mock_pref_cls.assert_called_with(
        transient_for=mock_edit_window, settings=mock_edit_window.settings
    )
    mock_pref_instance.show_all.assert_called_once()
    mock_pref_instance.connect.assert_called_with(
        "changed-preferences", mock_edit_window._changed_preferences
    )


def test_changed_preferences(mock_edit_window):
    "Test _changed_preferences"
    new_settings = mock_edit_window.settings.copy()
    new_settings["TMPDIR"] = "/new/tmp"

    mock_edit_window._changed_preferences(None, new_settings)

    mock_edit_window._ask_question.assert_called_once()
    mock_edit_window._restart.assert_called_once()
    assert mock_edit_window.settings["TMPDIR"] == "/new/tmp"


def test_select_blank_pages(mock_edit_window):
    "Test select_blank_pages"
    mock_edit_window.settings["Blank threshold"] = 10

    page1 = MagicMock()
    page1.std_dev = [5, 5, 5]  # Average 5 <= 10

    page2 = MagicMock()
    page2.std_dev = [15, 15, 15]  # Average 15 > 10

    mock_edit_window.slist.data = [[0, 0, page1], [1, 0, page2]]

    mock_edit_window.select_blank_pages()

    mock_edit_window.slist.select.assert_called_with([0, 0, page1])
    mock_edit_window.slist.unselect.assert_called_with([1, 0, page2])


def test_select_dark_pages(mock_edit_window):
    "Test select_dark_pages"
    mock_edit_window.settings["Dark threshold"] = 10

    page1 = MagicMock()
    page1.mean = [5, 5, 5]
    page1.std_dev = [1, 1, 1]  # length 3
    # Average 15/3 = 5 <= 10

    page2 = MagicMock()
    page2.mean = [30, 30, 30]
    page2.std_dev = [1, 1, 1]
    # Average 90/3 = 30 > 10

    mock_edit_window.slist.data = [[0, 0, page1], [1, 0, page2]]

    mock_edit_window.select_dark_pages()

    mock_edit_window.slist.select.assert_called_with([0, 0, page1])
    mock_edit_window.slist.unselect.assert_called_with([1, 0, page2])


def test_analyse(mock_edit_window):
    "Test analyse"
    page1 = MagicMock()
    page1.uuid = "uuid1"
    page1.analyse_time = datetime.datetime(2023, 1, 1)
    page1.dirty_time = datetime.datetime(2023, 1, 2)  # Needs analysis

    page2 = MagicMock()
    page2.uuid = "uuid2"
    page2.analyse_time = datetime.datetime(2023, 1, 2)
    page2.dirty_time = datetime.datetime(2023, 1, 1)  # Fresh

    mock_edit_window.slist.data = [[0, 0, page1], [1, 0, page2]]

    mock_edit_window.analyse(True, False)

    mock_edit_window.slist.analyse.assert_called_once()
    call_kwargs = mock_edit_window.slist.analyse.call_args[1]
    assert call_kwargs["list_of_pages"] == ["uuid1"]

    # Test finished callback
    finished_callback = call_kwargs["finished_callback"]
    mock_edit_window.select_blank_pages = MagicMock()

    finished_callback("response")

    mock_edit_window.post_process_progress.finish.assert_called_with("response")
    mock_edit_window.select_blank_pages.assert_called_once()


def test_analyse_empty(mock_edit_window):
    "Test analyse when no pages need analysis"
    page1 = MagicMock()
    page1.analyse_time = datetime.datetime(2023, 1, 2)
    page1.dirty_time = datetime.datetime(2023, 1, 1)

    mock_edit_window.slist.data = [[0, 0, page1]]
    mock_edit_window.select_blank_pages = MagicMock()

    mock_edit_window.analyse(True, False)

    mock_edit_window.slist.analyse.assert_not_called()
    mock_edit_window.select_blank_pages.assert_called_once()


def test_update_list_user_defined_tools(mock_edit_window):
    "Test _update_list_user_defined_tools"
    mock_combobox = MagicMock()
    # Simulate existing rows
    mock_combobox.get_num_rows.side_effect = [2, 1, 0, 0]  # Decreases as removed

    mock_edit_window.settings["user_defined_tools"] = ["tool1", "tool2"]
    mock_edit_window.settings["current_udt"] = "tool1"

    mock_edit_window._update_list_user_defined_tools([mock_combobox])

    # Check removal of old items
    assert mock_combobox.remove.call_count == 2
    mock_combobox.remove.assert_called_with(0)

    # Check addition of new items
    mock_combobox.append_text.assert_any_call("tool1")
    mock_combobox.append_text.assert_any_call("tool2")

    # Check setting active
    mock_combobox.set_active_by_text.assert_called_with("tool1")

    # Check hooks update
    mock_edit_window._update_post_save_hooks.assert_called_once()
