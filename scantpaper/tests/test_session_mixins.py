"Tests for the SessionMixins."

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

        # Callbacks
        _show_message_dialog = mocker.Mock()

        def get_application(self, *args, **kwargs):  # pylint: disable=arguments-differ
            "mock"
            return mock_app

    # Instantiate
    window = MockWindow()
    window.settings = {
        "TMPDIR": "/tmp",
        "message": {},
    }

    window.slist = mocker.MagicMock()
    window.view = mocker.Mock()

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

    mock_open = mocker.patch("builtins.open", mocker.mock_open())

    mock_session_window._find_crashed_sessions = mocker.Mock()

    mock_session_window._create_temp_directory()

    mock_temp_dir.assert_called_with(prefix="gscan2pdf-", dir="/tmp/found")
    assert mock_session_window.session == mock_temp_dir_instance
    mock_open.assert_called()  # Lockfile creation


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
