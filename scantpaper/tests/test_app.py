"Tests for app.py"

import logging
import sys
from unittest.mock import MagicMock, patch
import pytest

# Import the module under test
import app as app_module
from app import Application, _parse_arguments, main, PROG_NAME
import gi

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
    mocker.patch("app.os.remove")


def test_application_do_activate(mock_deps, mocker):
    "Test Application.do_activate"
    app = Application()
    app.window = None

    # Mock ApplicationWindow constructor
    mock_window_cls = app_module.ApplicationWindow
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


def test_parse_arguments_default(mock_deps, mocker):
    "Test _parse_arguments with default arguments"
    with patch("sys.argv", ["prog"]):
        args = _parse_arguments()

        assert args.log_level == logging.WARNING
        app_module.logging.basicConfig.assert_called_with(level=logging.WARNING)


def test_parse_arguments_debug(mock_deps, mocker):
    "Test _parse_arguments with --debug"
    with patch("sys.argv", ["prog", "--debug"]):
        args = _parse_arguments()
        assert args.log_level == logging.DEBUG


def test_parse_arguments_log_file(mock_deps, mocker):
    "Test _parse_arguments with --log"
    with patch("sys.argv", ["prog", "--log", "test.log"]):
        _parse_arguments()

        # Check basic config
        app_module.logging.basicConfig.assert_called()
        call_args = app_module.logging.basicConfig.call_args[1]
        assert "filename" in call_args
        assert call_args["filename"].endswith("test.log")
        assert call_args["level"] == logging.DEBUG  # Default when log file is set

        # Check atexit registration
        app_module.atexit.register.assert_called()

        # Verify the cleanup function
        cleanup_func = app_module.atexit.register.call_args[0][0]

        # Test the cleanup function
        mock_open = mocker.patch("builtins.open", mocker.mock_open(read_data=b"data"))
        mock_lzma_open = app_module.lzma.open
        mock_shutil_copy = app_module.shutil.copyfileobj
        mock_remove = app_module.os.remove

        cleanup_func()

        mock_open.assert_called()
        mock_lzma_open.assert_called()
        mock_shutil_copy.assert_called()
        mock_remove.assert_called()


def test_parse_arguments_log_compression_error(mock_deps, mocker):
    "Test log compression error handling"
    with patch("sys.argv", ["prog", "--log", "test.log"]):
        _parse_arguments()
        cleanup_func = app_module.atexit.register.call_args[0][0]

        mocker.patch("builtins.open", side_effect=OSError("Error"))
        logger = MagicMock()
        mocker.patch("app.logging.getLogger", return_value=logger)

        cleanup_func()

        logger.error.assert_called()


def test_parse_arguments_locale(mock_deps, mocker):
    "Test _parse_arguments with --locale"
    # Test specific locale path (starts with /)
    with patch("sys.argv", ["prog", "--locale", "/usr/share/locale"]):
        mocker.patch(
            "app.re.search", return_value=True
        )  # Mocking re.search to simulate match

        _parse_arguments()

        app_module.gettext.bindtextdomain.assert_called_with(
            PROG_NAME, "/usr/share/locale"
        )

    # Test relative locale (no /)
    with patch("sys.argv", ["prog", "--locale", "local_locale"]):
        mocker.patch("app.re.search", return_value=False)
        with patch("os.getcwd", return_value="/current/dir"):
            _parse_arguments()

            app_module.gettext.bindtextdomain.assert_called_with(
                PROG_NAME, "/current/dir/local_locale"
            )


def test_parse_arguments_multiple_instances(mock_deps, mocker):
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


def test_main(mock_deps, mocker):
    "Test main function"
    mock_app_cls = mocker.patch("app.Application")
    mock_app = mock_app_cls.return_value

    with patch("sys.argv", ["prog"]):
        main()

        mock_app_cls.assert_called()
        mock_app.run.assert_called()


def test_application_init_iconpath_fallback(mock_deps, mocker):
    "Test Application.__init__ with iconpath fallback"
    mocker.patch("app.os.path.isdir", return_value=False)
    # Gtk.IconTheme.get_default() was already mocked in mock_deps
    app = Application()
    app_module.os.path.isdir.assert_called()
    # It should have called prepend_search_path with the fallback path
    app_module.Gtk.IconTheme.get_default().prepend_search_path.assert_called_with(
        "/usr/share/scantpaper/icons"
    )


def test_application_do_startup(mock_deps, mocker):
    "Test Application.do_startup"
    app = Application()
    app.do_startup()
    app_module.Gtk.Application.do_startup.assert_called_with(app)


def test_pyinstaller_path(mocker):
    "Test that base_dir is set correctly when running as a PyInstaller bundle"
    import importlib

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
    import runpy

    with patch("sys.argv", ["scantpaper", "--version"]):
        try:
            runpy.run_module("app", run_name="__main__")
        except SystemExit:
            pass
