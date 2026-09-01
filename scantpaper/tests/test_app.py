"Tests for app.py"

# pylint: disable=protected-access  # tests access private members

import contextlib
import importlib
import logging
import pathlib
import runpy
import sys
from unittest.mock import MagicMock, patch

# Import the module under test
import app as app_module
import gi
import pytest
from app import PROG_NAME, Application, _parse_arguments, main

gi.require_version("Gtk", "3.0")


@pytest.fixture
def mock_deps(mocker):
    "Mock external dependencies"
    mocker.patch("app.Gtk")

    # Mock Gio but ensure flags are valid
    mock_gio = mocker.patch("app.Gio")
    # GApplicationFlags.HANDLES_OPEN is a flag, usually an int or enum.
    # We can just use an int.
    mock_gio.ApplicationFlags.HANDLES_OPEN = 1

    mocker.patch("app.ApplicationWindow")
    mocker.patch("app.gettext")
    mocker.patch("app.locale")

    # Mock logging with real levels
    mock_logging = mocker.patch("app.logging")
    mock_logging.DEBUG = logging.DEBUG
    mock_logging.INFO = logging.INFO
    mock_logging.WARNING = logging.WARNING
    mock_logging.ERROR = logging.ERROR
    mock_logging.CRITICAL = logging.CRITICAL

    # Mock lzma with real Exception for LZMAError
    mock_lzma = mocker.patch("app.lzma")
    mock_lzma.LZMAError = type("LZMAError", (Exception,), {})

    mocker.patch("app.shutil")
    mocker.patch("app.atexit")


@pytest.mark.usefixtures("mock_deps")
def test_application_do_activate(mocker):
    "Test Application.do_activate"
    app = Application()
    app.window = None

    # Mock ApplicationWindow constructor
    mock_window_cls = mocker.patch("app.ApplicationWindow")
    mock_window = mock_window_cls.return_value

    app.do_activate()

    mock_window_cls.assert_called_with(application=app)
    mock_window.present.assert_called_once()
    assert app.window == mock_window

    # Test subsequent activation (window already exists)
    mock_window.reset_mock()
    mock_window_cls.reset_mock()

    app.do_activate()

    mock_window_cls.assert_not_called()
    mock_window.present.assert_called_once()


@pytest.mark.usefixtures("mock_deps")
def test_parse_arguments_default(mocker):
    "Test _parse_arguments with default arguments"
    with patch("sys.argv", ["prog"]):
        mock_basicconfig = mocker.patch.object(app_module.logging, "basicConfig")
        args = _parse_arguments()

        assert args.log_level == logging.WARNING
        mock_basicconfig.assert_called_with(level=logging.WARNING)


@pytest.mark.usefixtures("mock_deps")
def test_parse_arguments_debug():
    "Test _parse_arguments with --debug"
    with patch("sys.argv", ["prog", "--debug"]):
        args = _parse_arguments()
        assert args.log_level == logging.DEBUG


@pytest.mark.usefixtures("mock_deps")
def test_parse_arguments_log_file(mocker):
    "Test _parse_arguments with --log"
    with patch("sys.argv", ["prog", "--log", "test.log"]):
        mock_basicconfig = mocker.patch.object(app_module.logging, "basicConfig")
        _parse_arguments()

        # Check basic config
        mock_basicconfig.assert_called()
        call_args = mock_basicconfig.call_args[1]
        assert "filename" in call_args
        assert call_args["filename"].endswith("test.log")
        assert call_args["level"] == logging.DEBUG  # Default when log file is set

        # Check atexit registration
        app_module.atexit.register.assert_called()

        # Verify the cleanup function
        cleanup_func = app_module.atexit.register.call_args[0][0]

        # Test the cleanup function
        mock_open = mocker.patch.object(
            pathlib.Path, "open", mocker.mock_open(read_data=b"data")
        )
        mock_lzma_open = mocker.patch.object(app_module.lzma, "open")
        mock_shutil_copy = mocker.patch.object(app_module.shutil, "copyfileobj")
        mock_remove = mocker.patch.object(pathlib.Path, "unlink")

        cleanup_func()

        mock_open.assert_called()
        mock_lzma_open.assert_called()
        mock_shutil_copy.assert_called()
        mock_remove.assert_called()


@pytest.mark.usefixtures("mock_deps")
def test_parse_arguments_log_compression_error(mocker):
    "Test log compression error handling"
    with patch("sys.argv", ["prog", "--log", "test.log"]):
        _parse_arguments()
        cleanup_func = app_module.atexit.register.call_args[0][0]

        mocker.patch.object(pathlib.Path, "open", side_effect=OSError("Error"))
        logger = MagicMock()
        mocker.patch("app.logging.getLogger", return_value=logger)

        cleanup_func()

        logger.exception.assert_called()


@pytest.mark.usefixtures("mock_deps")
def test_parse_arguments_locale(mocker):
    "Test _parse_arguments with --locale"
    mock_bindtextdomain = mocker.patch.object(app_module.gettext, "bindtextdomain")
    # Test specific locale path (starts with /)
    with patch("sys.argv", ["prog", "--locale", "/usr/share/locale"]):
        mocker.patch(
            "app.re.search", return_value=True
        )  # Mocking re.search to simulate match

        _parse_arguments()

        mock_bindtextdomain.assert_called_with(PROG_NAME, "/usr/share/locale")

    # Test relative locale (no /)
    with patch("sys.argv", ["prog", "--locale", "local_locale"]):
        mocker.patch("app.re.search", return_value=False)
        with patch("os.getcwd", return_value="/current/dir"):
            _parse_arguments()

            mock_bindtextdomain.assert_called_with(
                PROG_NAME, "/current/dir/local_locale"
            )


@pytest.mark.usefixtures("mock_deps")
def test_parse_arguments_multiple_instances():
    "Test _parse_arguments with multiple instances of --device, --import, and --import-all"
    test_args = [
        "prog",
        "--device",
        "dev1",
        "dev2",
        "--device",
        "dev3",
        "--import",
        "file1.pdf",
        "--import",
        "file2.pdf",
        "file3.pdf",
        "--import-all",
        "dir1",
        "--import-all",
        "dir2",
        "dir3",
    ]
    with patch("sys.argv", test_args):
        args = _parse_arguments()

        assert args.device == ["dev1", "dev2", "dev3"]
        assert args.import_files == ["file1.pdf", "file2.pdf", "file3.pdf"]
        assert args.import_all == ["dir1", "dir2", "dir3"]


@pytest.mark.usefixtures("mock_deps")
def test_main(mocker):
    "Test main function"
    mock_app_cls = mocker.patch("app.Application")
    mock_app = mock_app_cls.return_value

    with patch("sys.argv", ["prog"]):
        main()

        mock_app_cls.assert_called()
        mock_app.run.assert_called()


@pytest.mark.usefixtures("mock_deps")
def test_application_init_iconpath_fallback(mocker):
    "Test Application.__init__ with iconpath fallback"
    mock_is_dir = mocker.patch.object(pathlib.Path, "is_dir", return_value=False)
    mock_icon_theme = mocker.patch.object(app_module.Gtk, "IconTheme")
    # It should have called prepend_search_path with the fallback path
    Application()
    mock_is_dir.assert_called()
    mock_icon_theme.get_default().prepend_search_path.assert_called_with(
        "/usr/share/scantpaper/icons"
    )


@pytest.mark.usefixtures("mock_deps")
def test_application_init_iconpath_in_package(mocker):
    "Test Application.__init__ resolves icons from inside the package"
    mocker.patch.object(pathlib.Path, "is_dir", return_value=True)
    mock_icon_theme = mocker.patch.object(app_module.Gtk, "IconTheme")
    Application()
    in_package = str((pathlib.Path(app_module.__file__).parent / "icons").resolve())
    mock_icon_theme.get_default().prepend_search_path.assert_called_with(in_package)


@pytest.mark.usefixtures("mock_deps")
def test_application_do_startup(mocker):
    "Test Application.do_startup"
    app = Application()
    mock_do_startup = mocker.patch.object(app_module.Gtk.Application, "do_startup")
    app.do_startup()
    mock_do_startup.assert_called_with(app)


def test_pyinstaller_path(mocker):
    "Test that base_dir is set correctly when running as a PyInstaller bundle"
    # Mock sys.frozen and sys._MEIPASS
    mocker.patch.object(sys, "frozen", True, create=True)
    mocker.patch.object(sys, "_MEIPASS", "/fake/meipass", create=True)

    # Mock gi.require_version to avoid errors
    mocker.patch("gi.require_version")

    # Save original sys.path and restore it after the test
    original_path = sys.path[:]
    try:
        importlib.reload(app_module)
        assert sys.path[0] == "/fake/meipass"
    finally:
        sys.path[:] = original_path


def test_script_entry_point():
    "Test that the script entry point calls main() when run as __main__"
    with (
        patch("sys.argv", ["scantpaper", "--version"]),
        contextlib.suppress(SystemExit),
    ):
        runpy.run_module("app", run_name="__main__")


def test_handle_exception(mocker):
    "Test _handle_exception"
    mock_logger = mocker.patch("app.logging.getLogger")
    mock_critical = mock_logger.return_value.critical

    # Test standard exception
    exc_type, exc_value, exc_traceback = ValueError, ValueError("test"), None
    app_module._handle_exception(exc_type, exc_value, exc_traceback)
    mock_critical.assert_called_once()
    assert "Uncaught exception" in mock_critical.call_args[0][0]
    assert mock_critical.call_args[1]["exc_info"] == (
        exc_type,
        exc_value,
        exc_traceback,
    )

    # Test KeyboardInterrupt (should call original excepthook)
    mock_critical.reset_mock()
    with patch("sys.__excepthook__") as mock_orig_hook:
        exc_type = KeyboardInterrupt
        app_module._handle_exception(exc_type, None, None)
        mock_orig_hook.assert_called_once()
        mock_critical.assert_not_called()
