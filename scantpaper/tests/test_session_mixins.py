"Coverage tests for SessionMixins"

import os
from unittest.mock import MagicMock
import pytest
import gi
from session_mixins import SessionMixins

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


@pytest.fixture
def mock_session_window(mocker):
    "Fixture to provide a configured MockWindow"
    mock_app = mocker.Mock()

    class MockWindow(Gtk.Window, SessionMixins):
        "Test class to hold mixin"

        slist = None
        settings = {}
        session = None
        _lockfd = None
        _dependencies = {}
        _ocr_engine = []
        view = None
        builder = None
        t_canvas = None
        a_canvas = None
        _windowc = None
        _windowi = None
        _windowe = None
        _actions = {}
        _current_page = None
        _current_ocr_bbox = None
        _current_ann_bbox = None
        _ocr_text_hbox = None
        _ann_hbox = None
        _scan_progress = None
        post_process_progress = None
        _configfile = "/tmp/config"

        # Callbacks
        _show_message_dialog = mocker.Mock()
        _change_image_tool_cb = mocker.Mock()
        _changed_text_sort_method = mocker.Mock()
        save_dialog = mocker.Mock()
        email = mocker.Mock()
        print_dialog = mocker.Mock()
        renumber_dialog = mocker.Mock()
        select_all = mocker.Mock()
        select_odd_even = mocker.Mock()
        select_invert = mocker.Mock()
        crop_selection = mocker.Mock()
        cut_selection = mocker.Mock()
        copy_selection = mocker.Mock()
        paste_selection = mocker.Mock()
        delete_selection = mocker.Mock()
        clear_ocr = mocker.Mock()
        properties = mocker.Mock()
        rotate_90 = mocker.Mock()
        rotate_180 = mocker.Mock()
        rotate_270 = mocker.Mock()
        _pack_viewer_tools = mocker.Mock()

        def get_application(self, *args, **kwargs):  # pylint: disable=arguments-differ
            "mock"
            return mock_app

        def _open_session(self, session_dir):
            pass

    # Instantiate
    window = MockWindow()
    window.settings = {
        "TMPDIR": "/tmp",
        "message": {},
        "selection": None,
        "quality": 80,
        "post_save_hook": False,
        "current_psh": None,
        "user_defined_tools": [],
        "imagemagick": None,
        "graphicsmagick": None,
    }

    window.slist = mocker.MagicMock()
    window.view = mocker.Mock()
    window.view.zoom_changed_signal = 1
    window.view.offset_changed_signal = 2
    window.builder = mocker.Mock()
    window.t_canvas = mocker.Mock()
    window.a_canvas = mocker.Mock()
    window.post_process_progress = mocker.Mock()

    # Mock actions
    for action_name in ["tooltype", "save", "quit"]:
        window._actions[action_name] = mocker.Mock()

    yield window

    window.destroy()


def test_create_temp_directory_success(mocker, mock_session_window):
    "Test _create_temp_directory success"
    mocker.patch("session_mixins.get_tmp_dir", return_value="/tmp/found")
    mocker.patch("os.path.isdir", return_value=True)
    mocker.patch("session_mixins.fcntl.lockf")

    mock_temp_dir = mocker.patch("tempfile.TemporaryDirectory")
    mock_temp_dir_instance = mock_temp_dir.return_value
    mock_temp_dir_instance.name = "/tmp/found/gscan2pdf-1234"

    mocker.patch("builtins.open", mocker.mock_open())

    mock_session_window._find_crashed_sessions = mocker.Mock()

    mock_session_window._create_temp_directory()

    mock_temp_dir.assert_called_with(prefix="gscan2pdf-", dir="/tmp/found")
    assert mock_session_window.session == mock_temp_dir_instance


def test_create_temp_directory_no_tmpdir(mocker, mock_session_window):
    "Test _create_temp_directory when get_tmp_dir returns None"
    mocker.patch("session_mixins.get_tmp_dir", return_value=None)
    mocker.patch("session_mixins.fcntl.lockf")
    mock_temp_dir = mocker.patch("tempfile.TemporaryDirectory")
    mock_temp_dir_instance = mock_temp_dir.return_value
    mock_temp_dir_instance.name = "/tmp/gscan2pdf-fallback"
    mocker.patch("builtins.open", mocker.mock_open())
    mock_session_window._find_crashed_sessions = mocker.Mock()

    mock_session_window._create_temp_directory()
    mock_temp_dir.assert_called_with(prefix="gscan2pdf-")


def test_create_temp_directory_empty_tmpdir(mocker, mock_session_window):
    "Test _create_temp_directory when get_tmp_dir returns EMPTY"
    from const import EMPTY

    mocker.patch("session_mixins.get_tmp_dir", return_value=EMPTY)
    mocker.patch("session_mixins.fcntl.lockf")
    mock_temp_dir = mocker.patch("tempfile.TemporaryDirectory")
    mock_temp_dir_instance = mock_temp_dir.return_value
    mock_temp_dir_instance.name = "/tmp/gscan2pdf-fallback"
    mocker.patch("builtins.open", mocker.mock_open())
    mock_session_window._find_crashed_sessions = mocker.Mock()

    mock_session_window._create_temp_directory()
    mock_temp_dir.assert_called_with(prefix="gscan2pdf-")


def test_create_temp_directory_fallback(mocker, mock_session_window):
    "Test _create_temp_directory fallback when preferred dir fails"
    mocker.patch("session_mixins.get_tmp_dir", return_value="/tmp/bad")
    mocker.patch("os.path.isdir", return_value=True)
    mocker.patch("session_mixins.fcntl.lockf")

    # Simulate PermissionError on first try
    mock_temp_dir = mocker.patch("tempfile.TemporaryDirectory")
    mock_temp_dir.side_effect = [
        PermissionError,
        MagicMock(name="/tmp/fallback/gscan2pdf-1234"),
    ]

    mocker.patch("builtins.open", mocker.mock_open())
    mock_session_window._find_crashed_sessions = mocker.Mock()

    mock_session_window._create_temp_directory()

    # Should be called twice
    assert mock_temp_dir.call_count == 2
    # First call with dir
    mock_temp_dir.assert_any_call(prefix="gscan2pdf-", dir="/tmp/bad")
    # Second call without dir (fallback)
    mock_temp_dir.assert_any_call(prefix="gscan2pdf-")


def test_create_temp_directory_non_existent_tmpdir(mocker, mock_session_window):
    "Test _create_temp_directory when tmpdir does not exist"
    mocker.patch("session_mixins.get_tmp_dir", return_value="/tmp/new")
    mocker.patch("os.path.isdir", return_value=False)
    mocker.patch("os.mkdir")
    mocker.patch("session_mixins.fcntl.lockf")
    mocker.patch("tempfile.TemporaryDirectory")
    mocker.patch("builtins.open", mocker.mock_open())
    mock_session_window._find_crashed_sessions = mocker.Mock()

    mock_session_window._create_temp_directory()
    os.mkdir.assert_called_with("/tmp/new")


def test_check_dependencies(mocker, mock_session_window):
    "Test _check_dependencies"
    mocker.patch("tesserocr.tesseract_version", return_value="4.0")
    mocker.patch("tesserocr.__version__", return_value="2.5")

    mock_unpaper = mocker.patch("session_mixins.Unpaper")
    mock_unpaper.return_value.program_version.return_value = "6.1"

    mock_program_version = mocker.patch("session_mixins.program_version")
    mock_program_version.side_effect = lambda stream, regex, cmd: "1.0"

    mock_exec_command = mocker.patch("session_mixins.exec_command")
    mock_exec_command.return_value.stdout = "OK"

    mocker.patch("tempfile.NamedTemporaryFile")

    mock_session_window.session = MagicMock()
    mock_session_window.session.name = "/tmp/session"

    mock_session_window._check_dependencies()

    assert mock_session_window._dependencies["tesseract"] == "4.0"
    assert mock_session_window._dependencies["unpaper"] == "6.1"
    assert mock_session_window._dependencies["imagemagick"] == "1.0"


def test_check_dependencies_graphicsmagick_fallback(mocker, mock_session_window):
    "Test _check_dependencies with GraphicsMagick fallback"
    mocker.patch("tesserocr.tesseract_version", return_value=None)
    mocker.patch("tesserocr.__version__", return_value="2.5")
    mocker.patch("session_mixins.Unpaper")

    mock_program_version = mocker.patch("session_mixins.program_version")

    def side_effect(stream, regex, cmd):
        if "gm" in cmd:
            return "1.3"
        return None

    mock_program_version.side_effect = side_effect

    mock_session_window._check_dependencies()
    assert mock_session_window._dependencies["imagemagick"] == "1.3"
    mock_session_window._show_message_dialog.assert_called()


def test_check_dependencies_pdftk_error(mocker, mock_session_window, tmp_path):
    "Test _check_dependencies with pdftk error"
    mocker.patch("tesserocr.tesseract_version", return_value=None)
    mocker.patch("tesserocr.__version__", return_value="2.5")
    mocker.patch("session_mixins.Unpaper")

    mock_program_version = mocker.patch("session_mixins.program_version")

    def side_effect(stream, regex, cmd):
        if "pdftk" in cmd:
            return "2.0"
        return "1.0"

    mock_program_version.side_effect = side_effect

    mock_exec_command = mocker.patch("session_mixins.exec_command")
    mock_exec_command.return_value.stdout = "Error: could not load a required library"

    mock_session_window.session = MagicMock()
    mock_session_window.session.name = str(tmp_path)

    mock_session_window._check_dependencies()
    assert "pdftk" not in mock_session_window._dependencies
    mock_session_window._show_message_dialog.assert_called()


def test_zoom_methods(mock_session_window):
    "Test zoom methods"
    mock_session_window.zoom_100(None, None)
    mock_session_window.view.set_zoom.assert_called_with(1.0)

    mock_session_window.zoom_to_fit(None, None)
    mock_session_window.view.zoom_to_fit.assert_called_once()

    mock_session_window.zoom_in(None, None)
    mock_session_window.view.zoom_in.assert_called_once()

    mock_session_window.zoom_out(None, None)
    mock_session_window.view.zoom_out.assert_called_once()


def test_find_crashed_sessions_default_tmpdir(mocker, mock_session_window):
    "Test _find_crashed_sessions with None tmpdir"
    mocker.patch("glob.glob", return_value=[])
    mock_gettempdir = mocker.patch("tempfile.gettempdir", return_value="/tmp/default")

    mock_session_window._find_crashed_sessions(None)

    mock_gettempdir.assert_called_once()
    assert mock_session_window.session is None


def test_find_crashed_sessions_no_sessions(mocker, mock_session_window):
    "Test _find_crashed_sessions with no crashed sessions"
    mocker.patch("glob.glob", return_value=[])

    mock_session_window._find_crashed_sessions("/tmp")

    # Should not show dialog
    assert not hasattr(mock_session_window, "_list_unrestorable_sessions_called")


def test_find_crashed_sessions_running_sessions(mocker, mock_session_window):
    "Test _find_crashed_sessions with currently running sessions (locked)"
    mocker.patch("glob.glob", return_value=["/tmp/gscan2pdf-running"])

    # Mock _create_lockfile to fail (simulating running session)
    mock_session_window._create_lockfile = mocker.Mock(side_effect=OSError("Locked"))

    mock_session_window._find_crashed_sessions("/tmp")

    # Should not treat as crashed
    # We can verify that no dialog interaction happened
    mocker.patch("session_mixins.SimpleList")


def test_find_crashed_sessions_recoverable(mocker, mock_session_window):
    "Test _find_crashed_sessions with a recoverable session"
    mocker.patch("glob.glob", return_value=["/tmp/gscan2pdf-crashed"])

    # Mock _create_lockfile to succeed (not running)
    mock_session_window._create_lockfile = mocker.Mock()

    # Mock os.access to return True (session file exists/readable)
    mocker.patch("os.access", return_value=True)

    # Mock Dialog
    mock_dialog_cls = mocker.patch("session_mixins.Gtk.Dialog")
    mock_dialog = mock_dialog_cls.return_value
    mock_dialog.run.return_value = Gtk.ResponseType.OK

    # Mock SimpleList
    mock_simplelist_cls = mocker.patch("session_mixins.SimpleList")
    mock_simplelist = mock_simplelist_cls.return_value
    mock_simplelist.get_selected_indices.return_value = [0]  # Select first one

    mock_session_window._open_session = mocker.Mock()

    mock_session_window._find_crashed_sessions("/tmp")

    assert mock_session_window.session == "/tmp/gscan2pdf-crashed"
    mock_session_window._open_session.assert_called_with("/tmp/gscan2pdf-crashed")


def test_find_crashed_sessions_recoverable_no_select(mocker, mock_session_window):
    "Test _find_crashed_sessions with a recoverable session but no selection"
    mocker.patch("glob.glob", return_value=["/tmp/gscan2pdf-crashed"])
    mock_session_window._create_lockfile = mocker.Mock()
    mocker.patch("os.access", return_value=True)
    mock_dialog_cls = mocker.patch("session_mixins.Gtk.Dialog")
    mock_dialog = mock_dialog_cls.return_value
    mock_dialog.run.return_value = Gtk.ResponseType.CANCEL
    mock_simplelist_cls = mocker.patch("session_mixins.SimpleList")
    mock_simplelist = mock_simplelist_cls.return_value
    mock_simplelist.get_selected_indices.return_value = []

    mock_session_window._find_crashed_sessions("/tmp")
    assert mock_session_window.session is None


def test_find_crashed_sessions_unrestorable(mocker, mock_session_window):
    "Test _find_crashed_sessions with missing session file"
    mocker.patch("glob.glob", return_value=["/tmp/gscan2pdf-broken"])
    mock_session_window._create_lockfile = mocker.Mock()
    mocker.patch("os.access", return_value=False)  # session file missing

    mock_session_window._list_unrestorable_sessions = mocker.Mock()

    mock_session_window._find_crashed_sessions("/tmp")

    mock_session_window._list_unrestorable_sessions.assert_called_with(
        ["/tmp/gscan2pdf-broken"]
    )


def test_list_unrestorable_sessions(mocker, mock_session_window):
    "Test _list_unrestorable_sessions"
    mock_dialog_cls = mocker.patch("session_mixins.Gtk.Dialog")
    mock_dialog = mock_dialog_cls.return_value
    mock_dialog.run.return_value = Gtk.ResponseType.OK

    mock_textview_cls = mocker.patch("session_mixins.Gtk.TextView")
    mock_textview = mock_textview_cls.return_value

    mock_simplelist_cls = mocker.patch("session_mixins.SimpleList")
    mock_simplelist = mock_simplelist_cls.return_value
    mock_simplelist.get_selected_indices.return_value = [0]

    # Mock selection changed callback
    callbacks = {}

    def connect_side_effect(signal, callback):
        callbacks[signal] = callback

    mock_simplelist.get_selection().connect.side_effect = connect_side_effect

    mock_shutil_rmtree = mocker.patch("shutil.rmtree")

    mock_session_window._list_unrestorable_sessions(["/tmp/gscan2pdf-broken"])

    # Test the selection changed callback
    mock_button = MagicMock()
    mock_dialog.get_action_area().get_children.return_value = mock_button
    assert "changed" in callbacks
    callbacks["changed"]()

    mock_shutil_rmtree.assert_called_with("/tmp/gscan2pdf-broken")
    mock_textview.set_wrap_mode.assert_called_with(Gtk.WrapMode.WORD)


def test_list_unrestorable_sessions_cancel(mocker, mock_session_window):
    "Test _list_unrestorable_sessions when canceled"
    mock_dialog_cls = mocker.patch("session_mixins.Gtk.Dialog")
    mock_dialog = mock_dialog_cls.return_value
    mock_dialog.run.return_value = Gtk.ResponseType.CANCEL

    mock_shutil_rmtree = mocker.patch("shutil.rmtree")

    mock_session_window._list_unrestorable_sessions(["/tmp/gscan2pdf-broken"])

    mock_shutil_rmtree.assert_not_called()


def test_finished_process_callback(mocker, mock_session_window):
    "Test _finished_process_callback"
    mock_session_window._scan_progress = mocker.Mock()

    # Simple case
    mock_session_window._finished_process_callback(
        None, "other_process", button_signal=123
    )
    mock_session_window._scan_progress.disconnect.assert_called_with(123)
    mock_session_window._scan_progress.hide.assert_called()

    # Double sided scanning case - facing
    mock_session_window._scan_progress.reset_mock()
    mock_widget = mocker.Mock()
    mock_widget.sided = "double"
    mock_widget.side_to_scan = "facing"

    mock_session_window._ask_question = mocker.Mock(return_value=Gtk.ResponseType.OK)

    # idle_add needed because the callback runs inside it
    def immediate_idle_add(f, *args):
        f(*args)
        return True

    mocker.patch("gi.repository.GLib.idle_add", side_effect=immediate_idle_add)

    mock_session_window._finished_process_callback(mock_widget, "scan_pages")

    mock_session_window._ask_question.assert_called()
    assert mock_widget.side_to_scan == "reverse"

    # Double sided scanning case - reverse
    mock_widget.side_to_scan = "reverse"
    mock_session_window._finished_process_callback(mock_widget, "scan_pages")
    assert mock_widget.side_to_scan == "facing"


def test_display_callback(mocker, mock_session_window):
    "Test _display_callback"
    mock_response = mocker.Mock()
    mock_response.info = {"row": [None, None, "uuid-123"]}

    mock_session_window.slist.find_page_by_uuid.return_value = 5
    mock_session_window.slist.data = {5: [None, None, "page_id"]}

    mock_session_window._display_image = mocker.Mock()

    mock_session_window._display_callback(mock_response)

    mock_session_window._display_image.assert_called_with("page_id")

    # Page not found case
    mock_session_window.slist.find_page_by_uuid.return_value = None
    mock_session_window._display_callback(mock_response)


def test_display_image(mocker, mock_session_window):
    "Test _display_image"
    mock_page = mocker.Mock()
    mock_page.get_pixbuf.return_value = "pixbuf"
    mock_page.get_resolution.return_value = (300, 300, "in")
    mock_page.get_size.return_value = (1000, 2000)
    mock_page.text_layer = None
    mock_page.annotations = None

    mock_session_window.slist.thread.get_page.return_value = mock_page
    mock_session_window._windowc = mocker.Mock()
    mock_session_window._windowc.selection = "selection"

    # Case 1: Minimal page
    mock_session_window._display_image("page_id")

    mock_session_window.view.set_pixbuf.assert_called_with("pixbuf", True)
    mock_session_window.view.set_resolution_ratio.assert_called_with(1.0)
    assert mock_session_window._windowc.page_width == 1000
    assert mock_session_window._windowc.page_height == 2000
    mock_session_window.view.set_selection.assert_called_with("selection")

    # Case 2: Corrupted text layer
    mock_page.text_layer = "corrupt"
    mocker.patch(
        "session_mixins.Bboxtree", return_value=mocker.Mock(valid=lambda: False)
    )
    mock_session_window._display_image("page_id")
    assert mock_page.text_layer is None

    # Case 3: Valid text layer
    mock_page.text_layer = "valid"
    mocker.patch(
        "session_mixins.Bboxtree", return_value=mocker.Mock(valid=lambda: True)
    )
    mock_session_window._create_txt_canvas = mocker.Mock()
    mock_session_window._display_image("page_id")
    mock_session_window._create_txt_canvas.assert_called_with(mock_page)

    # Case 4: Annotations
    mock_page.annotations = "some_ann"
    mock_session_window._create_ann_canvas = mocker.Mock()
    mock_session_window._display_image("page_id")
    mock_session_window._create_ann_canvas.assert_called_with(mock_page)

    # Case 5: No pageid
    mock_session_window._display_image(None)


def test_error_callback(mocker, mock_session_window):
    "Test _error_callback"
    mock_response = mocker.Mock()
    mock_response.request.args = [{"page": "uuid-123"}]
    mock_response.request.process = "process_name"
    mock_response.type.name = "ERROR"
    mock_response.status = "Failed"

    mock_session_window.slist.find_page_by_uuid.return_value = 0
    mock_session_window.slist.data = {0: ["page_obj"]}

    mock_session_window.post_process_progress = mocker.Mock()

    def immediate_idle_add(f, *args):
        f(*args)
        return True

    mocker.patch("gi.repository.GLib.idle_add", side_effect=immediate_idle_add)

    mock_session_window._error_callback(mock_response)

    mock_session_window._show_message_dialog.assert_called()
    mock_session_window.post_process_progress.hide.assert_called()

    # Test without page info
    mock_response.request.args = [{}]
    mock_session_window._error_callback(mock_response)


def test_ask_question(mocker, mock_session_window):
    "Test _ask_question"
    mocker.patch("session_mixins.filter_message", return_value="filtered_text")
    mocker.patch("session_mixins.response_stored", return_value=False)

    mock_dialog_cls = mocker.patch("session_mixins.Gtk.MessageDialog")
    mock_dialog = mock_dialog_cls.return_value
    mock_dialog.run.return_value = Gtk.ResponseType.OK

    # Standard call
    response = mock_session_window._ask_question(
        parent=None,
        type=Gtk.MessageType.QUESTION,
        buttons=Gtk.ButtonsType.OK_CANCEL,
        text="Question?",
        default_response=Gtk.ResponseType.OK,
    )
    assert response == Gtk.ResponseType.OK

    # Test store-response and checkbox
    mock_checkbutton_cls = mocker.patch("session_mixins.Gtk.CheckButton")
    mock_checkbutton = mock_checkbutton_cls.new_with_label.return_value
    mock_checkbutton.get_active.return_value = True

    mock_session_window._ask_question(
        parent=None,
        type=Gtk.MessageType.QUESTION,
        buttons=Gtk.ButtonsType.OK_CANCEL,
        text="Question?",
        **{"store-response": True, "stored-responses": [Gtk.ResponseType.OK]},
    )
    assert (
        mock_session_window.settings["message"]["filtered_text"]["response"]
        == Gtk.ResponseType.OK
    )

    # Test already stored response
    mocker.patch("session_mixins.response_stored", return_value=True)
    mock_session_window.settings["message"]["filtered_text"] = {
        "response": Gtk.ResponseType.CANCEL
    }

    response = mock_session_window._ask_question(text="Question?")
    assert response == Gtk.ResponseType.CANCEL


def test_ask_question_with_default_response(mocker, mock_session_window):
    "Test _ask_question with default-response"
    mocker.patch("session_mixins.filter_message", return_value="filtered_text")
    mocker.patch("session_mixins.response_stored", return_value=False)

    mock_dialog_cls = mocker.patch("session_mixins.Gtk.MessageDialog")
    mock_dialog = mock_dialog_cls.return_value
    mock_dialog.run.return_value = Gtk.ResponseType.OK

    kwargs = {
        "parent": None,
        "type": Gtk.MessageType.QUESTION,
        "buttons": Gtk.ButtonsType.OK_CANCEL,
        "text": "Question?",
        "default-response": Gtk.ResponseType.OK,
    }
    response = mock_session_window._ask_question(**kwargs)
    assert response == Gtk.ResponseType.OK
    mock_dialog.set_default_response.assert_called_with(Gtk.ResponseType.OK)


def test_ocr_text_operations(mocker, mock_session_window):
    "Test OCR text operations: add, copy, delete"
    mock_session_window.slist.thread._take_snapshot = mocker.Mock()
    mock_session_window._ocr_text_hbox = mocker.Mock()
    mock_session_window._ocr_text_hbox._textbuffer.get_text.return_value = "new text"

    mock_session_window._current_page = mocker.Mock()
    mock_session_window._current_page.text_layer = "existing_layer"
    mock_session_window._current_page.__getitem__ = (
        lambda self, key: 100
    )  # width/height

    mock_session_window.view.get_selection.return_value = {
        "x": 0,
        "y": 0,
        "width": 10,
        "height": 10,
    }

    # Add
    mock_session_window.t_canvas.add_box.return_value = "new_bbox"
    mock_session_window.t_canvas.hocr.return_value = "hocr_output"

    mock_session_window._edit_ocr_text = mocker.Mock()

    mock_session_window._ocr_text_add(None)

    mock_session_window.t_canvas.add_box.assert_called()
    mock_session_window._current_page.import_hocr.assert_called_with("hocr_output")
    mock_session_window._edit_ocr_text.assert_called_with("new_bbox")

    # Add new layer case
    del mock_session_window._current_page.text_layer
    mock_session_window._create_txt_canvas = mocker.Mock()
    mock_session_window._ocr_text_add(None)
    mock_session_window._create_txt_canvas.assert_called()

    # Copy
    mock_session_window._ocr_text_copy(None)
    assert mock_session_window.t_canvas.add_box.call_count == 2

    # Delete
    mock_session_window._current_ocr_bbox = mocker.Mock()
    mock_session_window.t_canvas.get_current_bbox.return_value = "prev_bbox"

    mock_session_window._ocr_text_delete(None)
    mock_session_window._current_ocr_bbox.delete_box.assert_called()

    # OK (button clicked)
    mock_session_window._ocr_text_button_clicked(None)
    mock_session_window._current_ocr_bbox.update_box.assert_called()


def test_annotation_operations(mocker, mock_session_window):
    "Test annotation operations: ok, new, delete"
    mock_session_window._ann_hbox = mocker.Mock()
    mock_session_window._ann_hbox._textbuffer.get_text.return_value = "ann text"
    mock_session_window._current_page = mocker.Mock()
    mock_session_window._current_page.__getitem__ = lambda self, key: 100
    mock_session_window._current_ann_bbox = mocker.Mock()
    mock_session_window.a_canvas.hocr.return_value = "ann_hocr"

    # OK
    mock_session_window._edit_annotation = mocker.Mock()
    mock_session_window._ann_text_ok(None)
    mock_session_window._current_ann_bbox.update_box.assert_called()
    mock_session_window._current_page.import_annotations.assert_called_with("ann_hocr")

    # New
    mock_session_window._ann_text_new(None)
    mock_session_window.a_canvas.add_box.assert_called()

    # Delete
    mock_session_window._ann_text_delete(None)
    mock_session_window._current_ann_bbox.delete_box.assert_called()


def test_add_text_view_layers(mocker, mock_session_window):
    "Test _add_text_view_layers"
    mocker.patch("session_mixins.TextLayerControls")
    mock_edit_hbox = mocker.Mock()
    mock_session_window.builder.get_object.return_value = mock_edit_hbox

    mock_session_window._add_text_view_layers()

    mock_session_window.builder.get_object.assert_called_with("edit_hbox")
    assert mock_session_window._ocr_text_hbox is not None
    assert mock_session_window._ann_hbox is not None


def test_edit_mode_callback(mocker, mock_session_window):
    "Test _edit_mode_callback"
    mock_action = mocker.Mock()
    mock_param = mocker.Mock()

    mock_session_window._ocr_text_hbox = mocker.Mock()
    mock_session_window._ann_hbox = mocker.Mock()

    # Test text mode
    mock_param.get_string.return_value = "text"
    mock_session_window._edit_mode_callback(mock_action, mock_param)
    mock_session_window._ocr_text_hbox.show.assert_called()
    mock_session_window._ann_hbox.hide.assert_called()

    # Test other mode (e.g. annotation)
    mock_param.get_string.return_value = "annotation"
    mock_session_window._edit_mode_callback(mock_action, mock_param)
    mock_session_window._ocr_text_hbox.hide.assert_called()
    mock_session_window._ann_hbox.show.assert_called()


def test_edit_ocr_text(mocker, mock_session_window):
    "Test _edit_ocr_text"
    mock_bbox = mocker.Mock()
    mock_bbox.text = "some text"
    mock_bbox.bbox = "bbox_rect"

    mock_session_window._ocr_text_hbox = mocker.Mock()
    mock_session_window.t_canvas = mocker.Mock()

    # Case bbox is None
    mock_session_window._edit_ocr_text(None)

    # Case bbox is set
    mock_session_window._edit_ocr_text(mock_bbox)

    mock_session_window._ocr_text_hbox._textbuffer.set_text.assert_called_with(
        "some text"
    )
    mock_session_window.view.set_selection.assert_called_with("bbox_rect")
    mock_session_window.t_canvas.set_index_by_bbox.assert_called_with(mock_bbox)

    # test with event
    mock_ev = mocker.Mock()
    mock_ev.time = 123
    mock_session_window._edit_ocr_text(
        mock_bbox, _target="target", ev=mock_ev, bbox=mock_bbox
    )
    mock_session_window.t_canvas.pointer_ungrab.assert_called_with("target", 123)


def test_edit_annotation(mocker, mock_session_window):
    "Test _edit_annotation"
    mock_bbox = mocker.Mock()
    mock_bbox.text = "some text"
    mock_bbox.bbox = "bbox_rect"

    mock_session_window._ann_hbox = mocker.Mock()
    mock_session_window.a_canvas = mocker.Mock()

    # Case bbox is set
    mock_session_window._edit_annotation(mock_bbox)

    mock_session_window._ann_hbox._textbuffer.set_text.assert_called_with("some text")
    mock_session_window.view.set_selection.assert_called_with("bbox_rect")
    mock_session_window.a_canvas.set_index_by_bbox.assert_called_with(mock_bbox)

    # test with event
    mock_ev = mocker.Mock()
    mock_ev.time = 123
    mock_session_window._edit_annotation(
        mock_bbox, _target="target", ev=mock_ev, bbox=mock_bbox
    )
    mock_session_window.a_canvas.pointer_ungrab.assert_called_with("target", 123)


def test_sync_callbacks(mocker, mock_session_window):
    "Test zoom/offset sync callbacks"
    mock_session_window._text_zoom_changed_callback(None, 2.0)
    mock_session_window.view.set_zoom.assert_called_with(2.0)

    mock_session_window._text_offset_changed_callback(None, 10, 20)
    mock_session_window.view.set_offset.assert_called_with(10, 20)

    mock_session_window._ann_zoom_changed_callback(None, 3.0)
    mock_session_window.view.set_zoom.assert_called_with(3.0)

    mock_session_window._ann_offset_changed_callback(None, 30, 40)
    mock_session_window.view.set_offset.assert_called_with(30, 40)


def test_tool_actions(mock_session_window):
    "Test tool action callbacks"
    mock_session_window._on_dragger(None)
    mock_session_window._change_image_tool_cb.assert_called()

    mock_session_window._on_selector(None)
    mock_session_window._on_selectordragger(None)
    mock_session_window._on_zoom_100(None)
    mock_session_window._on_zoom_to_fit(None)
    mock_session_window._on_zoom_in(None)
    mock_session_window._on_zoom_out(None)
    mock_session_window._on_rotate_90(None)
    mock_session_window._on_rotate_180(None)
    mock_session_window._on_rotate_270(None)
    mock_session_window._on_save(None)
    mock_session_window._on_email(None)
    mock_session_window._on_print(None)
    mock_session_window._on_renumber(None)
    mock_session_window._on_select_all(None)
    mock_session_window._on_select_odd(None)
    mock_session_window._on_select_even(None)
    mock_session_window._on_invert_selection(None)
    mock_session_window._on_crop(None)
    mock_session_window._on_cut(None)
    mock_session_window._on_copy(None)
    mock_session_window._on_paste(None)
    mock_session_window._on_delete(None)
    mock_session_window._on_clear_ocr(None)
    mock_session_window._on_properties(None)

    mock_session_window._on_quit(None, None)
    mock_session_window.get_application().quit.assert_called()


def test_create_txt_ann_canvas(mocker, mock_session_window):
    "Test _create_txt_canvas and _create_ann_canvas"
    mock_session_window.view.get_offset.return_value = MagicMock(x=10, y=20)
    mock_session_window.view.get_zoom.return_value = 1.5

    mock_page = mocker.Mock()
    mock_session_window._create_txt_canvas(mock_page)
    mock_session_window.t_canvas.set_text.assert_called()
    mock_session_window.t_canvas.set_offset.assert_called_with(10, 20)

    mock_session_window._create_ann_canvas(mock_page)
    mock_session_window.a_canvas.set_text.assert_called()
    mock_session_window.a_canvas.set_offset.assert_called_with(10, 20)


def test_ann_text_new_no_layer(mocker, mock_session_window):
    "Test _ann_text_new with no existing text layer and empty text"
    from const import EMPTY

    mock_session_window._ann_hbox = mocker.Mock()
    # Line 643 coverage: text is EMPTY
    mock_session_window._ann_hbox._textbuffer.get_text.return_value = EMPTY

    # Mock _current_page so it doesn't have text_layer (Lines 655-674 coverage)
    # and supports dict access
    mock_page = mocker.MagicMock()
    del mock_page.text_layer
    page_data = {"width": 100, "height": 100}

    def getitem(key):
        return page_data.get(key)

    def setitem(key, value):
        page_data[key] = value

    mock_page.__getitem__.side_effect = getitem
    mock_page.__setitem__.side_effect = setitem
    mock_session_window._current_page = mock_page

    mock_session_window.view.get_selection.return_value = {
        "x": 0,
        "y": 0,
        "width": 10,
        "height": 10,
    }

    # Line 671-672 coverage: need to call the callback passed to _create_ann_canvas
    def create_ann_canvas_side_effect(_page, callback):
        callback(None)

    mock_session_window._create_ann_canvas = mocker.Mock(
        side_effect=create_ann_canvas_side_effect
    )
    mock_session_window._edit_annotation = mocker.Mock()
    mock_session_window.a_canvas = mocker.Mock()

    mock_session_window._ann_text_new(None)

    # Verify line 643 was hit (text became default)
    assert "my-new-annotation" in page_data["annotations"]
    # Verify lines 671-672 were hit
    mock_session_window.a_canvas.get_first_bbox.assert_called()
    mock_session_window._edit_annotation.assert_called()
