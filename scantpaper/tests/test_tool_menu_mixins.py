"Test tool_menu_mixins.py"

import pytest
from tools_menu_mixins import ToolsMenuMixins
from const import _90_DEGREES
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

    # Instantiate
    window = MockWindow()

    # Common mocks
    window.slist = mocker.MagicMock()
    window.post_process_progress = mocker.Mock()
    window._display_callback = mocker.Mock()
    window._error_callback = mocker.Mock()

    yield window

    window.destroy()


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

    from const import _180_DEGREES  # pylint: disable=import-outside-toplevel

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

    args, _kwargs = mock_dialog_instance.add_actions.call_args
    actions = args[0]
    apply_callback = None
    for action_name, callback in actions:
        if action_name == "gtk-apply":
            apply_callback = callback
            break

    assert apply_callback is not None, "Could not find gtk-apply callback"

    apply_callback()

    mock_tool_window.slist.threshold.assert_called_once()
    call_kwargs = mock_tool_window.slist.threshold.call_args[1]
    assert call_kwargs["threshold"] == 50
    assert call_kwargs["page"] == "uuid"


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

    args, _kwargs = mock_dialog_instance.add_actions.call_args
    actions = args[0]
    apply_callback = None
    for action_name, callback in actions:
        if action_name == "gtk-apply":
            apply_callback = callback
            break

    assert apply_callback is not None, "Could not find gtk-apply callback"

    apply_callback()

    mock_tool_window.slist.brightness_contrast.assert_called_once()
    call_kwargs = mock_tool_window.slist.brightness_contrast.call_args[1]
    assert call_kwargs["brightness"] == 20
    assert call_kwargs["contrast"] == 30
    assert call_kwargs["page"] == "uuid"


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

    args, _kwargs = mock_dialog_instance.add_actions.call_args
    actions = args[0]
    apply_callback = None
    for action_name, callback in actions:
        if action_name == "gtk-apply":
            apply_callback = callback
            break

    assert apply_callback is not None, "Could not find gtk-apply callback"

    apply_callback()

    mock_tool_window.slist.negate.assert_called_once()
    call_kwargs = mock_tool_window.slist.negate.call_args[1]
    assert call_kwargs["page"] == "uuid"


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

    args, _kwargs = mock_dialog_instance.add_actions.call_args
    actions = args[0]
    apply_callback = None
    for action_name, callback in actions:
        if action_name == "gtk-apply":
            apply_callback = callback
            break

    assert apply_callback is not None, "Could not find gtk-apply callback"

    apply_callback()

    mock_tool_window.slist.unsharp.assert_called_once()
    call_kwargs = mock_tool_window.slist.unsharp.call_args[1]
    assert call_kwargs["radius"] == 5.0
    assert call_kwargs["percent"] == 100
    assert call_kwargs["threshold"] == 10
    assert call_kwargs["page"] == "uuid"


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

    args, _kwargs = mock_crop_instance.add_actions.call_args
    actions = args[0]
    apply_callback = None
    for action_name, callback in actions:
        if action_name == "gtk-apply":
            apply_callback = callback
            break

    assert apply_callback is not None, "Could not find gtk-apply callback"

    apply_callback()

    mock_tool_window.slist.crop.assert_called_once()
    call_kwargs = mock_tool_window.slist.crop.call_args[1]
    assert call_kwargs["x"] == 10
    assert call_kwargs["y"] == 10
    assert call_kwargs["w"] == 50
    assert call_kwargs["h"] == 50
    assert call_kwargs["page"] == "uuid"


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

    args, _kwargs = mock_dialog_instance.add_actions.call_args
    actions = args[0]
    apply_callback = None
    for action_name, callback in actions:
        if action_name == "gtk-apply":
            apply_callback = callback
            break

    assert apply_callback is not None, "Could not find gtk-apply callback"

    apply_callback()
    mock_tool_window.slist.split_page.assert_called_once()


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

    args, _kwargs = mock_dialog_instance.add_actions.call_args
    actions = args[0]
    apply_callback = None
    for action_name, callback in actions:
        if action_name == "gtk-ok":
            apply_callback = callback
            break

    assert apply_callback is not None, "Could not find gtk-ok callback"

    apply_callback()

    mock_tool_window.slist.unpaper.assert_called_once()
    call_kwargs = mock_tool_window.slist.unpaper.call_args[1]
    assert call_kwargs["options"]["command"] == ["unpaper"]
    assert call_kwargs["options"]["direction"] == "direction"
    assert call_kwargs["page"] == "pageobject"


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

    args, _kwargs = mock_dialog_instance.add_actions.call_args
    actions = args[0]
    apply_callback = None
    for action_name, callback in actions:
        if action_name == "gtk-ok":
            apply_callback = callback
            break

    assert apply_callback is not None, "Could not find gtk-ok callback"

    apply_callback()

    mock_tool_window.slist.ocr_pages.assert_called_once()
    call_kwargs = mock_tool_window.slist.ocr_pages.call_args[1]
    assert call_kwargs["engine"] == "tesseract"
    assert call_kwargs["language"] == "eng"
    assert call_kwargs["threshold"] == 50
    assert call_kwargs["pages"] == ["pageobject"]


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

    args, _kwargs = mock_dialog_instance.add_actions.call_args
    actions = args[0]
    apply_callback = None
    for action_name, callback in actions:
        if action_name == "gtk-ok":
            apply_callback = callback
            break

    assert apply_callback is not None, "Could not find gtk-ok callback"

    apply_callback()

    mock_tool_window.slist.user_defined.assert_called_once()
    call_kwargs = mock_tool_window.slist.user_defined.call_args[1]
    assert call_kwargs["command"] == "my-tool"
    assert call_kwargs["page"] == "pageobject"


def test_email_dialog(mocker, mock_tool_window):
    "Test the email dialog"

    import datetime  # pylint: disable=import-outside-toplevel

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
        "text_position": "hidden",
        "default filename": "doc",
        "convert whitespace to underscores": True,
    }

    mock_tool_window.session = mocker.Mock()
    mock_tool_window.session.name = "session_name"
    mock_tool_window._list_of_page_uuids = mocker.Mock(return_value=["uuid1", "uuid2"])

    mock_tool_window.email(None, None)

    mock_save_dialog_cls.assert_called()

    args, _kwargs = mock_save_dialog_instance.add_actions.call_args
    actions = args[0]
    apply_callback = None
    for action_name, callback in actions:
        if action_name == "gtk-ok":
            apply_callback = callback
            break

    assert apply_callback is not None, "Could not find gtk-ok callback"

    apply_callback()

    mock_tool_window.slist.save_pdf.assert_called_once()
    call_kwargs = mock_tool_window.slist.save_pdf.call_args[1]
    assert call_kwargs["path"] == "session_name/doc.pdf"
    assert call_kwargs["list_of_pages"] == ["uuid1", "uuid2"]
    assert call_kwargs["options"]["user-password"] == "password"


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
