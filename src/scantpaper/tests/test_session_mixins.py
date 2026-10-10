"""Coverage tests for SessionMixins."""

from __future__ import annotations

import logging
import pathlib
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock

import gi
import pytest

from scantpaper.basethread import Request, Response, ResponseType
from scantpaper.const import EMPTY
from scantpaper.document import Document
from scantpaper.file_menu_mixins import FileMenuMixins
from scantpaper.session_mixins import SessionMixins

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from typing import ClassVar

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gtk  # noqa: E402


@pytest.fixture
def mock_session_window(
    mocker: pytest.MockerFixture,
) -> Generator[object, None, None]:
    """Fixture to provide a configured MockWindow."""
    mock_app = mocker.Mock()

    class MockWindow(Gtk.Window, SessionMixins):
        """Test class to hold mixin."""

        slist = None
        settings: dict[str, object]
        _dependencies: ClassVar[dict[str, object]] = {}
        _ocr_engine: ClassVar[list[list[str]]] = []
        _actions: ClassVar[dict[str, object]] = {}
        session = None
        _lockfd = None
        view = None
        builder = None
        t_canvas = None
        a_canvas = None
        _windowc = None
        _windowi = None
        _windowe = None
        _current_page = None
        _text_editor = None
        _ann_editor = None
        _scan_progress = None
        post_process_progress = None
        _configfile = "/tmp/config"

        # Callbacks
        _show_message_dialog = mocker.Mock()
        save_dialog = mocker.Mock()
        email = mocker.Mock()
        print_dialog = mocker.Mock()
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

        def get_application(self, *_args: object, **_kwargs: object) -> object:
            """Mock."""
            return mock_app

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
    window.builder = mocker.Mock()
    window.t_canvas = mocker.Mock()
    window.a_canvas = mocker.Mock()
    window._text_editor = mocker.Mock()
    window._ann_editor = mocker.Mock()
    window.post_process_progress = mocker.Mock()

    # Mock actions
    for action_name in ["tooltype", "save", "quit"]:
        window._actions[action_name] = mocker.Mock()

    yield window

    window.destroy()


def test_create_temp_directory_success(
    mocker: pytest.MockerFixture, mock_session_window: object
) -> None:
    """Test _create_temp_directory success."""
    mocker.patch("scantpaper.session_mixins.get_tmp_dir", return_value="/tmp/found")
    mocker.patch.object(pathlib.Path, "is_dir", return_value=True)
    mocker.patch("scantpaper.session_mixins.fcntl.lockf")

    mock_temp_dir = mocker.patch("tempfile.TemporaryDirectory")
    mock_temp_dir_instance = mock_temp_dir.return_value
    mock_temp_dir_instance.name = "/tmp/found/scantpaper-1234"

    mocker.patch.object(pathlib.Path, "open", mocker.mock_open())

    mock_session_window._find_crashed_sessions = mocker.Mock()

    mock_session_window._create_temp_directory()

    mock_temp_dir.assert_called_with(prefix="scantpaper-", dir="/tmp/found")
    assert mock_session_window.session == mock_temp_dir_instance


def test_create_temp_directory_no_tmpdir(
    mocker: pytest.MockerFixture, mock_session_window: object
) -> None:
    """Test _create_temp_directory when get_tmp_dir returns None."""
    mocker.patch("scantpaper.session_mixins.get_tmp_dir", return_value=None)
    mocker.patch("scantpaper.session_mixins.fcntl.lockf")
    mock_temp_dir = mocker.patch("tempfile.TemporaryDirectory")
    mock_temp_dir_instance = mock_temp_dir.return_value
    mock_temp_dir_instance.name = "/tmp/scantpaper-fallback"
    mocker.patch.object(pathlib.Path, "open", mocker.mock_open())
    mock_session_window._find_crashed_sessions = mocker.Mock()

    mock_session_window._create_temp_directory()
    mock_temp_dir.assert_called_with(prefix="scantpaper-")


def test_create_temp_directory_unconfigured_tmpdir_no_warning(
    mocker: pytest.MockerFixture, mock_session_window: object
) -> None:
    """No misleading 'unable to use None' warning when TMPDIR is unset."""
    mock_session_window.settings["TMPDIR"] = None
    mocker.patch("scantpaper.session_mixins.get_tmp_dir", return_value=None)
    mocker.patch("scantpaper.session_mixins.fcntl.lockf")
    mock_temp_dir = mocker.patch("tempfile.TemporaryDirectory")
    mock_temp_dir_instance = mock_temp_dir.return_value
    mock_temp_dir_instance.name = "/tmp/scantpaper-fallback"
    mocker.patch.object(pathlib.Path, "open", mocker.mock_open())
    mock_session_window._find_crashed_sessions = mocker.Mock()
    mock_logger = mocker.patch("scantpaper.session_mixins.logger")

    mock_session_window._create_temp_directory()

    assert mock_session_window.settings["TMPDIR"] == "/tmp", (
        "unset TMPDIR silently adopts the resolved directory"
    )
    mock_logger.warning.assert_not_called()


def test_create_temp_directory_empty_tmpdir(
    mocker: pytest.MockerFixture, mock_session_window: object
) -> None:
    """Test _create_temp_directory when get_tmp_dir returns EMPTY."""
    mocker.patch("scantpaper.session_mixins.get_tmp_dir", return_value=EMPTY)
    mocker.patch("scantpaper.session_mixins.fcntl.lockf")
    mock_temp_dir = mocker.patch("tempfile.TemporaryDirectory")
    mock_temp_dir_instance = mock_temp_dir.return_value
    mock_temp_dir_instance.name = "/tmp/scantpaper-fallback"
    mocker.patch.object(pathlib.Path, "open", mocker.mock_open())
    mock_session_window._find_crashed_sessions = mocker.Mock()

    mock_session_window._create_temp_directory()
    mock_temp_dir.assert_called_with(prefix="scantpaper-")


def test_create_temp_directory_fallback(
    mocker: pytest.MockerFixture, mock_session_window: object
) -> None:
    """Test _create_temp_directory fallback when preferred dir fails."""
    mocker.patch("scantpaper.session_mixins.get_tmp_dir", return_value="/tmp/bad")
    mocker.patch.object(pathlib.Path, "is_dir", return_value=True)
    mocker.patch("scantpaper.session_mixins.fcntl.lockf")

    # Simulate PermissionError on first try
    mock_temp_dir = mocker.patch("tempfile.TemporaryDirectory")
    mock_temp_dir.side_effect = [
        PermissionError,
        MagicMock(name="/tmp/fallback/scantpaper-1234"),
    ]

    mocker.patch.object(pathlib.Path, "open", mocker.mock_open())
    mock_session_window._find_crashed_sessions = mocker.Mock()

    mock_session_window._create_temp_directory()

    # Should be called twice
    assert mock_temp_dir.call_count == 2
    # First call with dir
    mock_temp_dir.assert_any_call(prefix="scantpaper-", dir="/tmp/bad")
    # Second call without dir (fallback)
    mock_temp_dir.assert_any_call(prefix="scantpaper-")


def test_create_temp_directory_non_existent_tmpdir(
    mocker: pytest.MockerFixture, mock_session_window: object
) -> None:
    """Test _create_temp_directory when tmpdir does not exist."""
    mocker.patch("scantpaper.session_mixins.get_tmp_dir", return_value="/tmp/new")
    mocker.patch.object(pathlib.Path, "is_dir", return_value=False)
    mock_mkdir = mocker.patch.object(pathlib.Path, "mkdir")
    mocker.patch("scantpaper.session_mixins.fcntl.lockf")
    mocker.patch("tempfile.TemporaryDirectory")
    mocker.patch.object(pathlib.Path, "open", mocker.mock_open())
    mock_session_window._find_crashed_sessions = mocker.Mock()

    mock_session_window._create_temp_directory()
    mock_mkdir.assert_called_once_with()


def test_check_dependencies(
    mocker: pytest.MockerFixture, mock_session_window: object
) -> None:
    """Test _check_dependencies."""
    mocker.patch("tesserocr.tesseract_version", return_value="4.0")
    mocker.patch("tesserocr.__version__", return_value="2.5")

    mock_unpaper = mocker.patch("scantpaper.session_mixins.Unpaper")
    mock_unpaper.return_value.program_version.return_value = "6.1"

    mock_program_version = mocker.patch("scantpaper.session_mixins.program_version")
    mock_program_version.side_effect = lambda _stream, _regex, _cmd: "1.0"

    mocker.patch("tempfile.NamedTemporaryFile")

    mock_session_window.session = MagicMock()
    mock_session_window.session.name = "/tmp/session"

    mock_session_window._check_dependencies()

    assert mock_session_window._dependencies["tesseract"] == "4.0"
    assert mock_session_window._dependencies["unpaper"] == "6.1"
    assert mock_session_window._dependencies["imagemagick"] == "1.0"


def test_check_dependencies_graphicsmagick_fallback(
    mocker: pytest.MockerFixture, mock_session_window: object
) -> None:
    """Test _check_dependencies with GraphicsMagick fallback."""
    mocker.patch("tesserocr.tesseract_version", return_value=None)
    mocker.patch("tesserocr.__version__", return_value="2.5")
    mocker.patch("scantpaper.session_mixins.Unpaper")

    mock_program_version = mocker.patch("scantpaper.session_mixins.program_version")

    def side_effect(stream: str, regex: object, cmd: list[str]) -> str | None:
        del stream, regex
        if "gm" in cmd:
            return "1.3"
        return None

    mock_program_version.side_effect = side_effect

    mock_session_window._check_dependencies()
    assert mock_session_window._dependencies["imagemagick"] == "1.3"
    mock_session_window._show_message_dialog.assert_called()


def test_zoom_methods(mock_session_window: object) -> None:
    """Test zoom methods."""
    mock_session_window.zoom_100(None, None)
    mock_session_window.view.set_zoom.assert_called_with(1.0)

    mock_session_window.zoom_to_fit(None, None)
    mock_session_window.view.zoom_to_fit.assert_called_once()

    mock_session_window.zoom_in(None, None)
    mock_session_window.view.zoom_in.assert_called_once()

    mock_session_window.zoom_out(None, None)
    mock_session_window.view.zoom_out.assert_called_once()


def test_find_crashed_sessions_default_tmpdir_none(
    mocker: pytest.MockerFixture, mock_session_window: object
) -> None:
    """Test _find_crashed_sessions when get_tmp_dir returns None."""
    mocker.patch.object(pathlib.Path, "glob", return_value=[])
    mocker.patch("scantpaper.session_mixins.get_tmp_dir", return_value=None)
    mock_gettempdir = mocker.patch(
        "scantpaper.session_mixins.tempfile.gettempdir", return_value="/fallback"
    )
    mock_session_window._open_session = mocker.Mock()
    mock_session_window._find_crashed_sessions()
    mock_gettempdir.assert_called_once()
    mock_session_window._open_session.assert_not_called()


def test_find_crashed_sessions_default_tmpdir_empty(
    mocker: pytest.MockerFixture, mock_session_window: object
) -> None:
    """Test _find_crashed_sessions when get_tmp_dir returns EMPTY."""
    mocker.patch.object(pathlib.Path, "glob", return_value=[])
    mocker.patch("scantpaper.session_mixins.get_tmp_dir", return_value=EMPTY)
    mock_gettempdir = mocker.patch(
        "scantpaper.session_mixins.tempfile.gettempdir", return_value="/fallback"
    )
    mock_session_window._open_session = mocker.Mock()
    mock_session_window._find_crashed_sessions()
    mock_gettempdir.assert_called_once()
    mock_session_window._open_session.assert_not_called()


def test_find_crashed_sessions_running_sessions(
    mocker: pytest.MockerFixture, mock_session_window: object
) -> None:
    """Test _find_crashed_sessions with currently running sessions (locked)."""
    mocker.patch.object(
        pathlib.Path, "glob", return_value=["/tmp/scantpaper-other.sdb"]
    )
    mock_session_window.session = mocker.Mock()
    mock_session_window.session.name = "/tmp/scantpaper-running"
    mocker.patch("scantpaper.session_mixins.get_tmp_dir", return_value="/tmp")

    # Mock _create_lockfile to fail (simulating running session)
    mocker.patch.object(pathlib.Path, "is_dir", return_value=True)
    mock_session_window._create_lockfile = mocker.Mock(side_effect=OSError("Locked"))
    mock_session_window._open_session = mocker.Mock()
    mock_session_window._find_crashed_sessions()
    mock_session_window._open_session.assert_not_called()


def test_find_crashed_sessions_skips_current(
    mocker: pytest.MockerFixture, mock_session_window: object
) -> None:
    """Test _find_crashed_sessions skips the current running session."""
    mocker.patch.object(
        pathlib.Path, "glob", return_value=["/tmp/scantpaper-running.sdb"]
    )
    mock_session_window.session = mocker.Mock()
    mock_session_window.session.name = "/tmp/scantpaper-running"
    mocker.patch("scantpaper.session_mixins.get_tmp_dir", return_value="/tmp")
    mock_session_window._open_session = mocker.Mock()
    mock_session_window._create_lockfile = mocker.Mock()

    mock_session_window._find_crashed_sessions()

    mock_session_window._create_lockfile.assert_not_called()
    mock_session_window._open_session.assert_not_called()


def test_find_crashed_sessions_recoverable(
    mocker: pytest.MockerFixture, mock_session_window: object
) -> None:
    """Test _find_crashed_sessions with a recoverable session."""
    mocker.patch.object(
        pathlib.Path, "glob", return_value=["/tmp/scantpaper-crashed.sdb"]
    )
    mock_session_window.session = mocker.Mock()
    mock_session_window.session.name = "/tmp/scantpaper-running"

    # Mock _create_lockfile to succeed (not running)
    mocker.patch.object(pathlib.Path, "is_dir", return_value=True)
    mock_session_window._create_lockfile = mocker.Mock()

    # Mock Dialog
    mock_dialog_cls = mocker.patch("scantpaper.session_mixins.Gtk.Dialog")
    mock_dialog = mock_dialog_cls.return_value
    mock_dialog.run.return_value = Gtk.ResponseType.OK

    # Mock SimpleList
    mock_simplelist_cls = mocker.patch("scantpaper.session_mixins.SimpleList")
    mock_simplelist = mock_simplelist_cls.return_value
    mock_simplelist.get_selected_indices.return_value = [0]  # Select first one

    mock_session_window._open_session = mocker.Mock()
    mock_session_window._find_crashed_sessions()

    mock_session_window._open_session.assert_called_with("/tmp/scantpaper-crashed.sdb")


def test_find_crashed_sessions_recoverable_no_select(
    mocker: pytest.MockerFixture, mock_session_window: object
) -> None:
    """Test _find_crashed_sessions with a recoverable session but no selection."""
    mocker.patch.object(pathlib.Path, "glob", return_value=["/tmp/scantpaper-crashed"])
    mock_session_window.session = mocker.Mock()
    mock_session_window.session.name = "/tmp/scantpaper-running"
    mock_session_window._create_lockfile = mocker.Mock()
    mocker.patch("os.access", return_value=True)
    mock_dialog_cls = mocker.patch("scantpaper.session_mixins.Gtk.Dialog")
    mock_dialog = mock_dialog_cls.return_value
    mock_dialog.run.return_value = Gtk.ResponseType.CANCEL
    mock_simplelist_cls = mocker.patch("scantpaper.session_mixins.SimpleList")
    mock_simplelist = mock_simplelist_cls.return_value
    mock_simplelist.get_selected_indices.return_value = []
    mock_session_window._open_session = mocker.Mock()

    mock_session_window._find_crashed_sessions()
    mock_session_window._open_session.assert_not_called()


def test_find_crashed_sessions_with_path_objects(
    mocker: pytest.MockerFixture, mock_session_window: object
) -> None:
    """Real Path results from glob never reach the str-typed SimpleList.

    Regression test for a startup TypeError where a pathlib.Path value from
    Path.glob was appended unchanged to a str-typed SimpleList column.
    """
    mocker.patch.object(
        pathlib.Path,
        "glob",
        return_value=[pathlib.Path("/tmp/scantpaper-crashed.sdb")],
    )
    mock_session_window.session = mocker.Mock()
    mock_session_window.session.name = "/tmp/scantpaper-running"
    mocker.patch("scantpaper.session_mixins.get_tmp_dir", return_value="/tmp")
    mocker.patch.object(pathlib.Path, "is_dir", return_value=True)
    mock_session_window._create_lockfile = mocker.Mock()

    mock_dialog_cls = mocker.patch("scantpaper.session_mixins.Gtk.Dialog")
    mock_dialog = mock_dialog_cls.return_value
    mock_dialog.run.return_value = Gtk.ResponseType.CANCEL

    mock_session_window._open_session = mocker.Mock()

    mock_session_window._find_crashed_sessions()
    mock_session_window._open_session.assert_not_called()


def test_finished_process_callback(
    mocker: pytest.MockerFixture, mock_session_window: object
) -> None:
    """Test _finished_process_callback."""
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
    def immediate_idle_add(f: Callable[..., object], *args: object) -> bool:
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


def test_display_callback(
    mocker: pytest.MockerFixture, mock_session_window: object
) -> None:
    """Test _display_callback."""
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


def test_display_image(
    mocker: pytest.MockerFixture, mock_session_window: object
) -> None:
    """Test _display_image."""
    mock_page = mocker.Mock()
    mock_page.get_pixbuf.return_value = "pixbuf"
    mock_page.get_resolution.return_value = (300, 300, "in")
    mock_page.get_size.return_value = (1000, 2000)
    mock_page.text_layer = None
    mock_page.annotations = None

    mock_session_window._windowc = mocker.Mock()
    mock_session_window._windowc.selection = "selection"

    # Mock the thumbnail pixbuf in data
    mock_thumbnail = mocker.Mock()
    mock_session_window.slist.data = [["page_num", mock_thumbnail, "page_id"]]
    mock_session_window.slist.find_page_by_uuid.return_value = 0

    # Capture the callbacks passed to send()
    captured_callbacks = {}

    def capture_send(process: object, *_args: object, **kwargs: object) -> object:
        del process
        captured_callbacks["finished_callback"] = kwargs.get("finished_callback")
        captured_callbacks["error_callback"] = kwargs.get("error_callback")
        return mocker.Mock()

    mock_session_window.slist.thread.send.side_effect = capture_send

    # Case 1: Minimal page
    mock_session_window._display_image("page_id")

    # Thumbnail should be set immediately
    mock_session_window.view.set_pixbuf.assert_called_with(
        mock_thumbnail, zoom_to_fit=True
    )

    # Simulate async response by calling the finished callback
    mock_response = mocker.Mock()
    mock_response.info = mock_page
    captured_callbacks["finished_callback"](mock_response)

    # Now the full-res pixbuf should be set
    mock_session_window.view.set_pixbuf.assert_called_with("pixbuf", zoom_to_fit=True)
    mock_session_window.view.set_resolution_ratio.assert_called_with(1.0)
    assert mock_session_window._windowc.page_width == 1000
    assert mock_session_window._windowc.page_height == 2000
    mock_session_window.view.set_selection.assert_called_with("selection")

    # Case 2: Corrupted text layer
    mock_page.text_layer = "corrupt"
    mocker.patch(
        "scantpaper.session_mixins.Bboxtree",
        return_value=mocker.Mock(valid=lambda: False),
    )
    mock_session_window._display_image("page_id")
    captured_callbacks["finished_callback"](mock_response)
    assert mock_page.text_layer is None

    # Case 3: Valid text layer
    mock_page.text_layer = "valid"
    mocker.patch(
        "scantpaper.session_mixins.Bboxtree",
        return_value=mocker.Mock(valid=lambda: True),
    )
    mock_session_window._text_editor = mocker.Mock()
    mock_session_window._display_image("page_id")
    captured_callbacks["finished_callback"](mock_response)
    mock_session_window._text_editor.create.assert_called()
    assert mock_session_window._text_editor.create.call_args[0][0] is mock_page

    # Case 4: Annotations
    mock_page.annotations = "some_ann"
    mock_session_window._ann_editor = mocker.Mock()
    mock_session_window._display_image("page_id")
    captured_callbacks["finished_callback"](mock_response)
    mock_session_window._ann_editor.create.assert_called()
    assert mock_session_window._ann_editor.create.call_args[0][0] is mock_page


def test_edit_undo_reload_rebuilds_layer_from_restored_text(
    mocker: pytest.MockerFixture, mock_session_window: object
) -> None:
    """Loading a page after an undone layer edit rebuilds from the restored layer.

    The thread-side round-trip (set_text -> undo -> old layer, asserted in
    test_docthread.py) hands the window a page carrying the pre-edit layer;
    the editor must rebuild its canvas from that restored text, never the
    edited text.
    """
    restored_layer = (
        '[{"type":"page","bbox":[0,0,10,10],"depth":0},'
        '{"type":"word","bbox":[0,0,5,5],"text":"ALPHA",'
        '"confidence":80,"depth":1}]'
    )
    page = mocker.Mock()
    page.get_pixbuf.return_value = "pixbuf"
    page.get_resolution.return_value = (300, 300, "in")
    page.get_size.return_value = (10, 10)
    page.text_layer = restored_layer
    page.annotations = None

    mock_session_window._windowc = None
    mock_session_window.settings["selection"] = None
    mock_session_window.slist.data = [["page_num", None, "page_id"]]
    mock_session_window.slist.find_page_by_uuid.return_value = 0

    captured = {}

    def capture_send(process: object, *_args: object, **kwargs: object) -> object:
        del process
        captured["finished_callback"] = kwargs.get("finished_callback")
        return mocker.Mock()

    mock_session_window.slist.thread.send.side_effect = capture_send
    mocker.patch(
        "scantpaper.session_mixins.Bboxtree",
        return_value=mocker.Mock(valid=lambda: True),
    )
    mock_session_window._text_editor = mocker.Mock()
    mock_session_window._ann_editor = mocker.Mock()

    mock_session_window._display_image("page_id")
    captured["finished_callback"](mocker.Mock(info=page))

    mock_session_window._text_editor.create.assert_called_once()
    loaded_page = mock_session_window._text_editor.create.call_args[0][0]
    assert loaded_page is page
    assert "ALPHA" in cast("str", loaded_page.text_layer)
    assert "CORRECTED" not in cast("str", loaded_page.text_layer)

    # Case 5: No pageid (page not found)
    mock_session_window.slist.find_page_by_uuid.return_value = None
    mock_session_window._display_image("nonexistent_page")


def test_display_image_error(
    caplog: pytest.LogCaptureFixture,
    mocker: pytest.MockerFixture,
    mock_session_window: object,
) -> None:
    """Test _display_image error callback."""
    mock_session_window.slist.find_page_by_uuid.return_value = 0
    mock_session_window.slist.data = [["page_num", None, "page_id"]]

    captured_callbacks = {}

    def capture_send(process: object, *_args: object, **kwargs: object) -> object:
        del process
        captured_callbacks["error_callback"] = kwargs.get("error_callback")
        return mocker.Mock()

    mock_session_window.slist.thread.send.side_effect = capture_send

    mock_session_window._display_image("page_id")

    mock_response = mocker.Mock()
    mock_response.status = "Some error"
    with caplog.at_level(logging.ERROR):
        captured_callbacks["error_callback"](mock_response)

    assert "Error loading page page_id: Some error" in caplog.text


def test_display_image_suppressed_no_get_page(
    mocker: pytest.MockerFixture, mock_session_window: object
) -> None:
    """Test _display_image shows only the thumbnail while import suppresses full-res."""
    mock_session_window.slist.find_page_by_uuid.return_value = 0
    mock_thumbnail = mocker.Mock()
    mock_session_window.slist.data = [["page_num", mock_thumbnail, "page_id"]]

    sent_requests = []
    mock_session_window.slist.thread.send.side_effect = (
        lambda process, *args, **_kwargs: sent_requests.append((process, args))
    )

    mock_session_window._suppress_full_display = True
    mock_session_window._display_image("page_id")

    mock_session_window.view.set_pixbuf.assert_called_with(
        mock_thumbnail, zoom_to_fit=True
    )
    assert not sent_requests, "no get_page while import is in progress"


def test_display_image_not_suppressed_sends(mock_session_window: object) -> None:
    """Test a _display_image call sends get_page when not suppressed."""
    mock_session_window.slist.find_page_by_uuid.return_value = 0
    mock_session_window.slist.data = [["page_num", None, "page_id"]]
    mock_session_window._suppress_full_display = False

    sent_requests = []
    mock_session_window.slist.thread.send.side_effect = (
        lambda process, *args, **_kwargs: sent_requests.append((process, args))
    )

    mock_session_window._display_image("page_id")

    assert len(sent_requests) == 1
    assert sent_requests[0][0] == "get_page"


def test_import_files_session_opens_full_resolution(
    mocker: pytest.MockerFixture, tmp_path: pathlib.Path
) -> None:
    """File→Open of a saved session releases suppression and loads full-res."""
    mocker.patch("scantpaper.basedocument.DocThread")

    class ImportWindow(Gtk.Window, SessionMixins, FileMenuMixins):
        """Window combining the mixins used to drive a session import."""

    window = ImportWindow()
    window.view = mocker.Mock()
    window.t_canvas = mocker.Mock()
    window.a_canvas = mocker.Mock()
    window._text_editor = mocker.Mock()
    window._ann_editor = mocker.Mock()
    window._current_page = None
    window._windowc = None
    window.settings = {"selection": None, "TMPDIR": "/tmp"}
    window.post_process_progress = mocker.Mock()

    slist = Document(dir=tmp_path)
    window.slist = slist

    session_db = tmp_path / "session.sdb"
    session_db.write_text("saved session", encoding="utf-8")

    page = mocker.Mock()
    page.text_layer = "some text"
    page.annotations = None
    page.get_pixbuf.return_value = mocker.Mock()
    page.get_size.return_value = (100, 200)
    page.get_resolution.return_value = (100.0, 100.0, "mm")
    page_response = mocker.Mock(info=page)

    sent = []

    def fake_get_file_info(
        _path: object, _password: object = None, **kwargs: object
    ) -> None:
        cast("Callable[..., object]", kwargs["finished_callback"])(
            mocker.Mock(info={"format": "session file", "path": str(session_db)})
        )

    def fake_send(process: str, *_args: object, **kwargs: object) -> mocker.Mock:
        sent.append(process)
        if process == "open" and "finished_callback" in kwargs:
            cast("Callable[..., object]", kwargs["finished_callback"])(mocker.Mock())
        elif process == "page_number_table" and "finished_callback" in kwargs:
            cast("Callable[..., object]", kwargs["finished_callback"])(
                mocker.Mock(info=[[1, None, 101]])
            )
        elif process == "get_page" and "finished_callback" in kwargs:
            cast("Callable[..., object]", kwargs["finished_callback"])(page_response)
        return mocker.Mock()

    slist.thread.get_file_info = fake_get_file_info
    slist.thread.send = fake_send

    # Seed the sidebar row so on_table -> select(0) selects it, like the real UI.
    slist.get_model().append([1, None, 101])

    mocker.patch(
        "scantpaper.session_mixins.Bboxtree",
        return_value=mocker.Mock(valid=lambda: True),
    )

    window._import_files([str(session_db)])

    assert window._suppress_full_display is False
    assert window._current_page is page
    window._text_editor.create.assert_called_once()
    window._ann_editor.clear.assert_called_once()
    assert sent.count("get_page") == 1

    # Switching pages afterwards loads each page at full resolution.
    window._display_image(101)
    assert sent.count("get_page") == 2

    window.destroy()


def test_error_callback(
    mocker: pytest.MockerFixture, mock_session_window: object
) -> None:
    """Test _error_callback."""
    mock_response = mocker.Mock()
    mock_response.request.args = [{"page": "uuid-123"}]
    mock_response.request.process = "process_name"
    mock_response.type.name = "ERROR"
    mock_response.status = "Failed"

    mock_session_window.slist.find_page_by_uuid.return_value = 0
    mock_session_window.slist.data = {0: ["page_obj"]}

    mock_session_window.post_process_progress = mocker.Mock()

    def immediate_idle_add(f: Callable[..., object], *args: object) -> bool:
        f(*args)
        return True

    mocker.patch("gi.repository.GLib.idle_add", side_effect=immediate_idle_add)

    mock_session_window._error_callback(mock_response)

    mock_session_window._show_message_dialog.assert_called()
    mock_session_window.post_process_progress.hide.assert_called()

    # Test without page info
    mock_response.request.args = [{}]
    mock_session_window._error_callback(mock_response)


def test_ask_question(
    mocker: pytest.MockerFixture, mock_session_window: object
) -> None:
    """Test _ask_question."""
    mocker.patch(
        "scantpaper.session_mixins.filter_message", return_value="filtered_text"
    )
    mocker.patch("scantpaper.session_mixins.response_stored", return_value=False)

    mock_dialog_cls = mocker.patch("scantpaper.session_mixins.Gtk.MessageDialog")
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
    mock_checkbutton_cls = mocker.patch("scantpaper.session_mixins.Gtk.CheckButton")
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
    mocker.patch("scantpaper.session_mixins.response_stored", return_value=True)
    mock_session_window.settings["message"]["filtered_text"] = {
        "response": Gtk.ResponseType.CANCEL
    }

    response = mock_session_window._ask_question(text="Question?")
    assert response == Gtk.ResponseType.CANCEL


def test_ask_question_with_default_response(
    mocker: pytest.MockerFixture, mock_session_window: object
) -> None:
    """Test _ask_question with default-response."""
    mocker.patch(
        "scantpaper.session_mixins.filter_message", return_value="filtered_text"
    )
    mocker.patch("scantpaper.session_mixins.response_stored", return_value=False)

    mock_dialog_cls = mocker.patch("scantpaper.session_mixins.Gtk.MessageDialog")
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


def test_tool_actions(mock_session_window: object) -> None:
    """Test tool action callbacks."""
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


def test_add_text_view_layers(
    mocker: pytest.MockerFixture, mock_session_window: object
) -> None:
    """Test _add_text_view_layers creates and wires the two editors."""
    captured = []

    class FakeEditor:
        def __init__(self, **kwargs: object) -> None:
            captured.append(kwargs)
            self.canvas = mocker.Mock()
            self.controls = mocker.Mock()

    mocker.patch("scantpaper.session_mixins.LayerEditor", FakeEditor)
    mock_session_window.view = mocker.Mock()
    mock_session_window.slist.thread = mocker.Mock()
    mock_session_window._current_page = mocker.Mock()
    mock_edit_hbox = mocker.Mock()
    mock_session_window.builder.get_object.return_value = mock_edit_hbox
    mock_session_window._pack_viewer_tools = mocker.Mock()

    mock_session_window._add_text_view_layers()

    assert len(captured) == 2
    assert mock_session_window.t_canvas is not None
    assert mock_session_window.a_canvas is not None
    mock_edit_hbox.pack_start.assert_called()
    mock_session_window._pack_viewer_tools.assert_called()

    # Exercise the injected get_page closure and verify the shared thread.
    for kwargs in captured:
        assert kwargs["get_page"]() is mock_session_window._current_page
        assert kwargs["thread"] is mock_session_window.slist.thread


def test_edit_mode_callback(
    mocker: pytest.MockerFixture, mock_session_window: object
) -> None:
    """Test _edit_mode_callback toggles the editors via set_active."""
    mock_action = mocker.Mock()
    mock_param = mocker.Mock()
    mock_session_window._text_editor = mocker.Mock()
    mock_session_window._ann_editor = mocker.Mock()

    # Test text mode
    mock_param.get_string.return_value = "text"
    mock_session_window._edit_mode_callback(mock_action, mock_param)
    mock_session_window._text_editor.set_active.assert_called_with(active=True)
    mock_session_window._ann_editor.set_active.assert_called_with(active=False)

    # Test other mode (e.g. annotation)
    mock_session_window._text_editor.reset_mock()
    mock_session_window._ann_editor.reset_mock()
    mock_param.get_string.return_value = "annotation"
    mock_session_window._edit_mode_callback(mock_action, mock_param)
    mock_session_window._text_editor.set_active.assert_called_with(active=False)
    mock_session_window._ann_editor.set_active.assert_called_with(active=True)


class MockApp(SessionMixins):
    """mock application class for testing SessionMixins methods."""

    def __init__(self) -> None:
        """Initialise MockApp."""
        self.slist = MagicMock()
        # Mock slist.data as a list of lists [page_number, pixbuf, page_id]
        self.slist.data = [[1, None, 1]]

        # find_page_by_uuid returns index if found, else None
        def find_side_effect(_page_id: object) -> None:
            return None

        self.slist.find_page_by_uuid.side_effect = find_side_effect

        # Mock other required attributes
        self.post_process_progress = MagicMock()
        self._show_message_dialog = MagicMock()


def test_error_callback_with_corrupted_args(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that _error_callback does not crash on corrupted request args.

    E.g. page UUID replaced by an object, or key missing. It should log
    correctly.
    """
    app = MockApp()

    # 1. Simulate corrupted args where 'page' is an object instead of a UUID
    mock_request = MagicMock(spec=Request)
    mock_request.process = "user_defined"
    mock_request.args = [{"page": object()}]  # Corrupted: object instead of UUID

    response = Response(
        type=ResponseType.ERROR,
        request=mock_request,
        info=None,
        status="Some Error",
        num_completed_jobs=1,
        total_jobs=1,
        pending=False,
    )

    with caplog.at_level(logging.ERROR):
        app._error_callback(response)

    assert (
        "Error running 'error' callback for 'user_defined' process: Some Error"
        in caplog.text
    )


def test_error_callback_with_missing_page_key(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that _error_callback does not crash when the 'page' key is missing.

    It should log correctly.
    """
    app = MockApp()

    mock_request = MagicMock(spec=Request)
    mock_request.process = "analyse"
    mock_request.args = [{}]  # Missing 'page' key

    response = Response(
        type=ResponseType.ERROR,
        request=mock_request,
        info=None,
        status="Analyse Error",
        num_completed_jobs=1,
        total_jobs=1,
        pending=False,
    )

    with caplog.at_level(logging.ERROR):
        app._error_callback(response)

    assert (
        "Error running 'error' callback for 'analyse' process: Analyse Error"
        in caplog.text
    )


def test_error_callback_with_trace(
    mocker: pytest.MockerFixture, mock_session_window: object
) -> None:
    """Test _error_callback with a stack trace."""
    mock_response = mocker.Mock()
    mock_response.request.args = [{}]
    mock_response.request.process = "process_name"
    mock_response.type.name = "ERROR"
    mock_response.status = "Failed"

    # Mock inspect.trace()
    mock_info = mocker.Mock()
    mock_info.filename = "scantpaper/session_mixins.py"
    mock_info.lineno = 123
    mocker.patch("scantpaper.session_mixins.inspect.trace", return_value=[mock_info])

    mock_logger = mocker.patch("scantpaper.session_mixins.logger")

    # Mock idle_add to run the callback immediately
    def immediate_idle_add(f: Callable[..., object], *args: object) -> bool:
        f(*args)
        return True

    mocker.patch("gi.repository.GLib.idle_add", side_effect=immediate_idle_add)

    mock_session_window._error_callback(mock_response)

    # Check if logger.error was called with the filename and line number
    mock_logger.error.assert_any_call(
        "Filename: '%s' line: %s", "scantpaper/session_mixins.py", 123
    )


def test_on_page_loaded_reapplies_selection(
    mocker: pytest.MockerFixture, mock_session_window: object
) -> None:
    """A selection is re-applied against the full-resolution page on load."""
    mock_session_window._windowc = None
    sel = Gdk.Rectangle()
    sel.x, sel.y, sel.width, sel.height = 600, 800, 700, 900
    mock_session_window.settings["selection"] = sel

    page = mocker.Mock()
    page.get_pixbuf.return_value = mocker.Mock()
    page.get_resolution.return_value = (200, 200, "PixelsPerInch")
    page.get_size.return_value = (1500, 2000)
    page.text_layer = None
    page.annotations = None
    response = mocker.Mock()
    response.info = page

    mock_session_window._on_page_loaded(response)

    mock_session_window.view.set_selection.assert_called_once()
    reapplied = mock_session_window.view.set_selection.call_args[0][0]
    assert reapplied is sel
    assert reapplied.width > 0, "re-applied selection is not degenerate"
    assert reapplied.height > 0, "re-applied selection is not degenerate"
    assert mock_session_window.settings["selection"] is sel, (
        "settings selection is not overwritten"
    )
    mock_session_window._text_editor.clear.assert_called_once()
    mock_session_window._ann_editor.clear.assert_called_once()


def test_on_page_loaded_does_not_reapply_when_no_selection(
    mocker: pytest.MockerFixture, mock_session_window: object
) -> None:
    """No selection is re-applied when none is set."""
    mock_session_window._windowc = None
    mock_session_window.settings["selection"] = None

    page = mocker.Mock()
    page.get_pixbuf.return_value = mocker.Mock()
    page.get_resolution.return_value = (200, 200, "PixelsPerInch")
    page.get_size.return_value = (1500, 2000)
    page.text_layer = None
    page.annotations = None
    response = mocker.Mock()
    response.info = page

    mock_session_window._on_page_loaded(response)

    mock_session_window.view.set_selection.assert_not_called()
