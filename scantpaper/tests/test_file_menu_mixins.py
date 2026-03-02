"test file_menu_mixins"

import datetime
import unittest.mock
import gi
import pytest
from file_menu_mixins import (
    FileMenuMixins,
    add_filter,
    launch_default_for_file,
    file_exists,
)

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


class MockSlist:
    "A mock class simulating a simple list for testing purposes."

    def __init__(self):
        "Initialize mock slist"
        self.data = [[0, 0, "uuid1"], [0, 0, "uuid2"], [0, 0, "uuid3"]]
        self.row_changed_signal = "row-changed"
        self.selection_changed_signal = "selection-changed"
        self.thread = unittest.mock.Mock()

    def get_model(self):
        "Return the current instance as the model."
        return self

    def get_selection(self):
        "Return the current selection object."
        return self

    def handler_block(self, signal):
        "Block the handler for the specified signal (currently a placeholder)."

    def handler_unblock(self, signal):
        "Unblock the handler for the specified signal (currently a placeholder)."

    def unselect_all(self):
        "Deselects all currently selected items."

    def import_files(self, **kwargs):
        "Mock import_files"

    def open_session(self, _dir, delete, error_callback):
        "Mock open_session"

    def save_pdf(self, **kwargs):
        "Mock save_pdf"

    def save_djvu(self, **kwargs):
        "Mock save_djvu"

    def save_tiff(self, **kwargs):
        "Mock save_tiff"

    def save_text(self, **kwargs):
        "Mock save_text"

    def save_hocr(self, **kwargs):
        "Mock save_hocr"

    def save_image(self, **kwargs):
        "Mock save_image"

    def save_session(self, filename, version):
        "Mock save_session"


class MockView:  # pylint: disable=too-few-public-methods
    "A mock view class"

    def set_pixbuf(self, pixbuf):
        "Set the pixbuf for the view."


class MockCanvas:  # pylint: disable=too-few-public-methods
    "A mock canvas class"

    def clear_text(self):
        "clear the text on the canvas."


class MockWindows:
    "A mock scan window class"

    def reset_start_page(self):
        "Reset the start page to its default value."

    def get_size(self):
        "Return the size of the window."
        return (100, 100)

    def __bool__(self):
        "Mock boolean"
        return True

    @property
    def thread(self):
        "Mock thread property"
        return unittest.mock.Mock()


class MockApp(unittest.mock.Mock, FileMenuMixins):
    "A mock application class"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.slist = MockSlist()
        self.settings = {"cwd": "/tmp"}
        self.view = MockView()
        self.t_canvas = MockCanvas()
        self.a_canvas = MockCanvas()
        self._windows = MockWindows()
        self.session = unittest.mock.Mock()
        self.post_process_progress = unittest.mock.Mock()
        self._dependencies = {}
        self.print_settings = None
        self._configfile = "/tmp/scantpaperrc"
        self._lockfd = 9
        self._hpaned = unittest.mock.Mock()
        self._hpaned.get_position.return_value = 100
        self._current_page = 1
        self._ask_question = unittest.mock.Mock()
        self._import_files = unittest.mock.Mock()
        self._error_callback = unittest.mock.Mock()
        self._windowi = None
        self._windowe = None

    def get_size(self):
        "Mock get_size"
        return (800, 600)

    def get_position(self):
        "Mock get_position"
        return (0, 0)

    def _show_message_dialog(self, **kwargs):
        "Mock _show_message_dialog"


class TestStandaloneFunctions(unittest.TestCase):
    "Test standalone functions in file_menu_mixins"

    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_add_filter(self, mock_gtk):
        "add_filter adds correct filters and patterns."
        mock_file_chooser = unittest.mock.Mock()
        mock_filter = unittest.mock.Mock()
        mock_gtk.FileFilter.return_value = mock_filter

        add_filter(mock_file_chooser, "Image files", ["jpg", "png"])

        mock_file_chooser.add_filter.assert_has_calls(
            [
                unittest.mock.call(mock_filter),
                unittest.mock.call(mock_filter),
            ]
        )
        mock_filter.add_pattern.assert_has_calls(
            [
                unittest.mock.call("*.[Jj][Pp][Gg]"),
                unittest.mock.call("*.[Pp][Nn][Gg]"),
                unittest.mock.call("*"),
            ]
        )
        mock_filter.set_name.assert_has_calls(
            [
                unittest.mock.call("Image files (*.jpg, *.png)"),
                unittest.mock.call("All files"),
            ]
        )

    @unittest.mock.patch("file_menu_mixins.os.path.isfile")
    @unittest.mock.patch("file_menu_mixins.GLib")
    def test_file_exists_true(self, mock_glib, mock_isfile):
        "file_exists returns True if file exists"
        mock_isfile.return_value = True
        chooser = unittest.mock.Mock()

        assert file_exists(chooser, "test.txt")
        chooser.set_filename.assert_called_with("test.txt")
        mock_glib.idle_add.assert_called()

    @unittest.mock.patch("file_menu_mixins.os.path.isfile")
    def test_file_exists_false(self, mock_isfile):
        "file_exists returns False if file does not exist"
        mock_isfile.return_value = False
        chooser = unittest.mock.Mock()

        assert not file_exists(chooser, "test.txt")
        chooser.set_filename.assert_not_called()

    @unittest.mock.patch("file_menu_mixins.Gio")
    def test_launch_default_for_file_success(self, mock_gio):
        "Test successful launch"
        mock_context = unittest.mock.Mock()
        mock_gio.AppLaunchContext.return_value = mock_context

        launch_default_for_file("test.pdf")

        mock_gio.AppInfo.launch_default_for_uri.assert_called()

    @unittest.mock.patch("file_menu_mixins.Gio")
    @unittest.mock.patch("file_menu_mixins.logger")
    def test_launch_default_for_file_error(self, mock_logger, mock_gio):
        "Test launch with error"
        mock_gio.Error = Exception
        mock_gio.AppInfo.launch_default_for_uri.side_effect = Exception("error")

        launch_default_for_file("test.pdf")

        mock_logger.error.assert_called()


class TestFileMenuMixins:
    "Test FileMenuMixins class and its methods."

    @pytest.fixture(autouse=True)
    def app(self, tmp_path):
        "Set up a mock application for testing."
        app = MockApp()
        app.settings = {
            "cwd": "/tmp",
            "close_dialog_on_save": False,
            "post_save_hook": False,
            "pdf compression": "jpeg",
            "downsample": True,
            "downsample dpi": 150,
            "quality": 80,
            "set_timestamp": True,
            "convert whitespace to underscores": True,
            "current_psh": "tool",
            "tiff compression": "jpeg",
            "default filename": "default",
            "author": "author",
            "title": "title",
            "subject": "subject",
            "keywords": "keywords",
            "view files toggle": True,
            "ps_backend": "pdf2ps",
            "Page range": "all",
            "use_time": True,
            "datetime offset": datetime.timedelta(0),
            "title-suggestions": [],
            "author-suggestions": [],
            "subject-suggestions": [],
            "keywords-suggestions": [],
            "image type": "pdf",
            "user_defined_tools": ["tool"],
        }
        app._dependencies = {
            "pdfunite": True,
            "djvu": True,
            "libtiff": True,
            "pdf2ps": True,
            "pdftops": True,
            "pdftk": True,
        }
        app.session = unittest.mock.Mock()
        app.session.name = str(tmp_path)
        return app

    def test_new(self, app):
        "new_() resets state and clears data."
        app.slist.data = [1, 2, 3]
        app.view.set_pixbuf = unittest.mock.Mock()
        app.t_canvas.clear_text = unittest.mock.Mock()
        app.a_canvas.clear_text = unittest.mock.Mock()
        app._current_page = 1
        app._windows.reset_start_page = unittest.mock.Mock()
        app._pages_saved = unittest.mock.Mock(return_value=True)

        app.new_(None, None)

        app._pages_saved.assert_called_once()
        assert app.slist.data == []
        app.view.set_pixbuf.assert_called_with(None)
        app.t_canvas.clear_text.assert_called_once()
        app.a_canvas.clear_text.assert_called_once()
        assert app._current_page is None
        app._windows.reset_start_page.assert_called_once()

    def test_new_before_scan_dialog(self, app):
        "Verify fix for #28 File/New straight after start causes Traceback"
        app._windows = None
        app.slist.data = [1, 2, 3]
        app.new_(None, None)
        assert app.slist.data == []

    def test_new_cancel(self, app):
        "Test new_() does not clear data if pages not saved."
        app.slist.data = [1, 2, 3]
        app._pages_saved = unittest.mock.Mock(return_value=False)

        app.new_(None, None)

        app._pages_saved.assert_called_once()
        assert app.slist.data == [1, 2, 3]

    def test_quit_app(self, app):
        "Test quit_app() calls application quit method."
        app._can_quit = unittest.mock.Mock(return_value=True)
        app_mock = unittest.mock.Mock()
        app.get_application = unittest.mock.Mock(return_value=app_mock)

        app.quit_app(None, None)
        app_mock.quit.assert_called_once()

    def test_can_quit_pages_not_saved(self, app):
        "Test _can_quit returns False if pages not saved."
        app._pages_saved = unittest.mock.Mock(return_value=False)
        assert not app._can_quit()

    @unittest.mock.patch("file_menu_mixins.os")
    @unittest.mock.patch("file_menu_mixins.glob")
    @unittest.mock.patch("file_menu_mixins.fcntl")
    @unittest.mock.patch("file_menu_mixins.config")
    def test_can_quit(self, mock_config, mock_fcntl, mock_glob, mock_os, app):
        "Test _can_quit performs cleanup and saves settings."
        app._pages_saved = unittest.mock.Mock(return_value=True)
        mock_glob.glob.return_value = ["file1", "file2"]

        assert app._can_quit()

        mock_os.chdir.assert_called_with(app.settings["cwd"])
        mock_glob.glob.assert_called()
        mock_os.remove.assert_has_calls(
            [
                unittest.mock.call("file1"),
                unittest.mock.call("file2"),
            ]
        )
        mock_os.rmdir.assert_called()
        mock_config.write_config.assert_called_with(app._configfile, app.settings)
        mock_fcntl.lockf.assert_called_with(app._lockfd, mock_fcntl.LOCK_UN)

    def test_pages_saved_true(self, app):
        "Test _pages_saved returns True if pages are saved."
        app.slist.thread.pages_saved.return_value = True
        assert app._pages_saved("message")

    def test_pages_saved_false_ok(self, app):
        "Test _pages_saved returns True if user confirms save."
        app.slist.thread.pages_saved.return_value = False
        app._ask_question.return_value = Gtk.ResponseType.OK
        assert app._pages_saved("message")
        app._ask_question.assert_called_once()

    def test_pages_saved_false_cancel(self, app):
        "Test _pages_saved returns False if user cancels save."
        app.slist.thread.pages_saved.return_value = False
        app._ask_question.return_value = Gtk.ResponseType.CANCEL
        assert not app._pages_saved("message")
        app._ask_question.assert_called_once()

    @unittest.mock.patch("file_menu_mixins.Gtk")
    @unittest.mock.patch("file_menu_mixins.os")
    def test_open_dialog_ok(self, mock_os, mock_gtk, app):
        "Test open_dialog imports files on OK response."
        mock_dialog = unittest.mock.Mock()
        mock_dialog.run.return_value = mock_gtk.ResponseType.OK
        mock_dialog.get_filenames.return_value = [
            "/path/to/file1.jpg",
            "/path/to/file2.png",
        ]
        mock_gtk.FileChooserDialog.return_value = mock_dialog
        mock_os.path.dirname.return_value = "/path/to"
        app._import_files = unittest.mock.Mock()

        app.open_dialog(None, None)

        mock_gtk.FileChooserDialog.assert_called_once()
        mock_dialog.get_filenames.assert_called_once()
        mock_dialog.destroy.assert_called_once()
        assert app.settings["cwd"] == "/path/to"
        app._import_files.assert_called_with(
            ["/path/to/file1.jpg", "/path/to/file2.png"]
        )
        assert mock_os.chdir.call_count >= 3

    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_open_dialog_cancel(self, mock_gtk, app):
        "Test open_dialog does not import files on cancel."
        mock_dialog = unittest.mock.Mock()
        mock_dialog.run.return_value = mock_gtk.ResponseType.CANCEL
        mock_gtk.FileChooserDialog.return_value = mock_dialog
        app._import_files = unittest.mock.Mock()

        app.open_dialog(None, None)

        mock_gtk.FileChooserDialog.assert_called_once()
        mock_dialog.destroy.assert_called_once()
        app._import_files.assert_not_called()

    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_select_pagerange_callback_ok(self, mock_gtk, app):
        "Test _select_pagerange_callback returns correct range on OK."
        mock_dialog = unittest.mock.Mock()
        mock_dialog.run.return_value = mock_gtk.ResponseType.OK
        mock_gtk.Dialog.return_value = mock_dialog
        mock_spinbuttonf = unittest.mock.Mock()
        mock_spinbuttonf.get_value.return_value = 1
        mock_spinbuttonl = unittest.mock.Mock()
        mock_spinbuttonl.get_value.return_value = 10
        mock_gtk.SpinButton.new_with_range.side_effect = [
            mock_spinbuttonf,
            mock_spinbuttonl,
        ]
        vbox = unittest.mock.Mock()
        mock_dialog.get_content_area.return_value = vbox

        first, last = app._select_pagerange_callback({"pages": 10})

        assert first == 1
        assert last == 10
        mock_dialog.destroy.assert_called_once()

    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_select_pagerange_callback_cancel(self, mock_gtk, app):
        "Test _select_pagerange_callback returns None on cancel."
        mock_dialog = unittest.mock.Mock()
        mock_dialog.run.return_value = mock_gtk.ResponseType.CANCEL
        mock_gtk.Dialog.return_value = mock_dialog

        first, last = app._select_pagerange_callback({"pages": 10})

        assert first is None
        assert last is None
        mock_dialog.destroy.assert_called_once()

    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_import_files_password_callback_ok(self, mock_gtk, app):
        "Test _import_files_password_callback returns password on OK."
        mock_dialog = unittest.mock.Mock()
        mock_dialog.run.return_value = mock_gtk.ResponseType.OK
        mock_entry = unittest.mock.Mock()
        mock_entry.get_text.return_value = "password"
        mock_gtk.MessageDialog.return_value = mock_dialog
        vbox = unittest.mock.Mock()
        mock_dialog.get_content_area.return_value = vbox
        mock_gtk.Entry.return_value = mock_entry

        password = app._import_files_password_callback("file.pdf")

        assert password == "password"
        mock_dialog.destroy.assert_called_once()

    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_import_files_password_callback_cancel(self, mock_gtk, app):
        "Test _import_files_password_callback returns None on cancel."
        mock_dialog = unittest.mock.Mock()
        mock_dialog.run.return_value = mock_gtk.ResponseType.CANCEL
        mock_entry = unittest.mock.Mock()
        mock_entry.get_text.return_value = "password"
        mock_gtk.MessageDialog.return_value = mock_dialog
        vbox = unittest.mock.Mock()
        mock_dialog.get_content_area.return_value = vbox
        mock_gtk.Entry.return_value = mock_entry

        password = app._import_files_password_callback("file.pdf")

        assert password is None
        mock_dialog.destroy.assert_called_once()

    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_import_files_password_callback_empty(self, mock_gtk, app):
        "Test _import_files_password_callback returns None if empty"
        mock_dialog = unittest.mock.Mock()
        mock_dialog.run.return_value = mock_gtk.ResponseType.OK
        mock_entry = unittest.mock.Mock()
        mock_entry.get_text.return_value = ""
        mock_gtk.MessageDialog.return_value = mock_dialog
        vbox = unittest.mock.Mock()
        mock_dialog.get_content_area.return_value = vbox
        mock_gtk.Entry.return_value = mock_entry

        password = app._import_files_password_callback("file.pdf")

        assert password is None
        mock_dialog.destroy.assert_called_once()

    def test_import_files_finished_callback(self, app):
        "Test _import_files_finished_callback calls finish."
        app._import_files_finished_callback("response")
        app.post_process_progress.finish.assert_called_with("response")

    @unittest.mock.patch("file_menu_mixins.config")
    def test_import_files_metadata_callback(self, mock_config, app):
        "Test _import_files_metadata_callback updates metadata."
        app._windowi = unittest.mock.Mock()
        app._windowe = unittest.mock.Mock()
        metadata = {"key": "value"}

        app._import_files_metadata_callback(metadata)

        app._windowi.update_from_import_metadata.assert_called_with(metadata)
        app._windowe.update_from_import_metadata.assert_called_with(metadata)
        mock_config.update_config_from_imported_metadata.assert_called_with(
            app.settings, metadata
        )

    def test_import_files_all_pages(self, app):
        "Test _import_files with all_pages=True passes correct pagerange_callback."
        app.slist.import_files = unittest.mock.Mock()
        filenames = ["file1.pdf", "file2.pdf"]

        FileMenuMixins._import_files(app, filenames, all_pages=True)

        app.slist.import_files.assert_called_once()
        _args, kwargs = app.slist.import_files.call_args
        assert kwargs["paths"] == filenames
        assert "pagerange_callback" in kwargs
        assert kwargs["pagerange_callback"]({"pages": 10}) == (1, 10)

    def test_import_files(self, app):
        "Test _import_files passes correct pagerange_callback."
        app.slist.import_files = unittest.mock.Mock()
        app._select_pagerange_callback = unittest.mock.Mock(return_value=(1, 5))
        filenames = ["file1.pdf", "file2.pdf"]

        FileMenuMixins._import_files(app, filenames)

        app.slist.import_files.assert_called_once()
        _args, kwargs = app.slist.import_files.call_args
        assert kwargs["paths"] == filenames
        assert "pagerange_callback" in kwargs
        assert kwargs["pagerange_callback"] == app._select_pagerange_callback

    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_open_session_action_ok(self, mock_gtk, app):
        "Test _open_session_action opens session on OK."
        app._open_session = unittest.mock.Mock()
        mock_dialog = unittest.mock.Mock()
        mock_dialog.run.return_value = mock_gtk.ResponseType.OK
        mock_dialog.get_filenames.return_value = ["/path/to/session"]
        mock_gtk.FileChooserDialog.return_value = mock_dialog

        app._open_session_action(None, None)

        mock_gtk.FileChooserDialog.assert_called_once()
        mock_dialog.get_filenames.assert_called_once()
        app._open_session.assert_called_with("/path/to/session")
        mock_dialog.destroy.assert_called_once()

    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_open_session_action_cancel(self, mock_gtk, app):
        "Test _open_session_action does not open session on cancel."
        app._open_session = unittest.mock.Mock()
        mock_dialog = unittest.mock.Mock()
        mock_dialog.run.return_value = mock_gtk.ResponseType.CANCEL
        mock_gtk.FileChooserDialog.return_value = mock_dialog

        app._open_session_action(None, None)

        mock_gtk.FileChooserDialog.assert_called_once()
        app._open_session.assert_not_called()
        mock_dialog.destroy.assert_called_once()

    def test_open_session(self, app):
        "Test _open_session calls slist.open_session with correct args."
        app.slist.open_session = unittest.mock.Mock()

        app._open_session("/path/to/session")

        app.slist.open_session.assert_called_with(
            dir="/path/to/session",
            delete=False,
            error_callback=app._error_callback,
        )

    def test_open_session_actual(self, app):
        "Call _open_session via FileMenuMixins class to hit the logic."
        app.slist.open_session = unittest.mock.Mock()
        FileMenuMixins._open_session(app, "/some/path")
        app.slist.open_session.assert_called_with(
            dir="/some/path", delete=False, error_callback=app._error_callback
        )

    @unittest.mock.patch("file_menu_mixins.datetime")
    @unittest.mock.patch("file_menu_mixins.SaveDialog")
    def test_save_dialog(self, mock_save_dialog, mock_datetime, app):
        "Test save_dialog creates and shows SaveDialog."
        app._windowi = None
        mock_dialog = unittest.mock.Mock()
        mock_dialog.comboboxpsh.get_num_rows.return_value = 0
        mock_save_dialog.return_value = mock_dialog
        mock_datetime.datetime.now.return_value = datetime.datetime(2025, 1, 1)

        # Test with windowi as None
        app.save_dialog(None, None)

        mock_save_dialog.assert_called_once()
        assert app._windowi == mock_dialog
        mock_dialog.add_page_range.assert_called_once()
        mock_dialog.add_image_type.assert_called_once()
        mock_dialog.add_actions.assert_called_once()
        mock_dialog.show_all.assert_called_once()
        mock_dialog.resize.assert_called_with(1, 1)

        # Test existing windowi
        app.save_dialog(None, None)
        mock_dialog.present.assert_called_once()

    def test_save_button_clicked_callback_pdf(self, app):
        "Test _save_button_clicked_callback for PDF type."
        app._windowi = unittest.mock.Mock()
        app._windowi.page_range = "all"
        app._windowi.image_type = "pdf"
        app._windowi.downsample = True
        app._windowi.downsample_dpi = 150
        app._windowi.pdf_compression = "jpeg"
        app._windowi.jpeg_quality = 80
        app._windowi.comboboxpsh.get_active.return_value = 0
        app._windowi.comboboxpsh.get_active_text.return_value = "tool"
        app._list_of_page_uuids = unittest.mock.Mock(return_value=["uuid1"])
        app._save_file_chooser = unittest.mock.Mock()
        mock_kbutton = unittest.mock.Mock()
        mock_kbutton.get_active.return_value = True
        mock_pshbutton = unittest.mock.Mock()
        mock_pshbutton.get_active.return_value = True

        app._save_button_clicked_callback(mock_kbutton, mock_pshbutton)

        assert app.settings["Page range"] == "all"
        assert app.settings["image type"] == "pdf"
        assert app.settings["close_dialog_on_save"]
        assert app.settings["post_save_hook"]
        assert app.settings["current_psh"] == "tool"
        assert app.settings["downsample"]
        assert app.settings["downsample dpi"] == 150
        assert app.settings["pdf compression"] == "jpeg"
        assert app.settings["quality"] == 80
        app._save_file_chooser.assert_called_with(["uuid1"])

    def test_save_button_clicked_callback_djvu(self, app):
        "Test _save_button_clicked_callback for DjVu type."
        app._windowi = unittest.mock.Mock()
        app._windowi.page_range = "all"
        app._windowi.image_type = "djvu"
        app._windowi.comboboxpsh.get_active.return_value = 0
        app._windowi.comboboxpsh.get_active_text.return_value = "tool"
        app._list_of_page_uuids = unittest.mock.Mock(return_value=["uuid1"])
        app._save_file_chooser = unittest.mock.Mock()
        mock_kbutton = unittest.mock.Mock()
        mock_kbutton.get_active.return_value = True
        mock_pshbutton = unittest.mock.Mock()
        mock_pshbutton.get_active.return_value = True

        app._save_button_clicked_callback(mock_kbutton, mock_pshbutton)

        assert app.settings["image type"] == "djvu"
        app._windowi.update_config_dict.assert_called_with(app.settings)
        app._save_file_chooser.assert_called_with(["uuid1"])

    def test_save_button_clicked_callback_tif(self, app):
        "Test _save_button_clicked_callback for TIFF type."
        app._windowi = unittest.mock.Mock()
        app._windowi.page_range = "all"
        app._windowi.image_type = "tif"
        app._windowi.tiff_compression = "jpeg"
        app._windowi.jpeg_quality = 80
        app._windowi.comboboxpsh.get_active.return_value = 0
        app._windowi.comboboxpsh.get_active_text.return_value = "tool"
        app._list_of_page_uuids = unittest.mock.Mock(return_value=["uuid1"])
        app._save_file_chooser = unittest.mock.Mock()
        mock_kbutton = unittest.mock.Mock()
        mock_kbutton.get_active.return_value = True
        mock_pshbutton = unittest.mock.Mock()
        mock_pshbutton.get_active.return_value = True

        app._save_button_clicked_callback(mock_kbutton, mock_pshbutton)

        assert app.settings["image type"] == "tif"
        assert app.settings["tiff compression"] == "jpeg"
        assert app.settings["quality"] == 80
        app._save_file_chooser.assert_called_with(["uuid1"])

    def test_save_button_clicked_callback_txt(self, app):
        "Test _save_button_clicked_callback for TXT type."
        app._windowi = unittest.mock.Mock()
        app._windowi.image_type = "txt"
        app._windowi.comboboxpsh.get_active.return_value = -1
        app._list_of_page_uuids = unittest.mock.Mock(return_value=["uuid1"])
        app._save_file_chooser = unittest.mock.Mock()
        mock_kbutton = unittest.mock.Mock()
        mock_pshbutton = unittest.mock.Mock()

        app._save_button_clicked_callback(mock_kbutton, mock_pshbutton)

        assert app.settings["image type"] == "txt"
        app._save_file_chooser.assert_called_with(["uuid1"])

    def test_save_button_clicked_callback_ps(self, app):
        "Test _save_button_clicked_callback for PS type."
        app._windowi = unittest.mock.Mock()
        app._windowi.image_type = "ps"
        app._windowi.ps_backend = "libtiff"
        app._windowi.comboboxpsh.get_active.return_value = -1
        app._list_of_page_uuids = unittest.mock.Mock(return_value=["uuid1"])
        app._save_file_chooser = unittest.mock.Mock()
        mock_kbutton = unittest.mock.Mock()
        mock_pshbutton = unittest.mock.Mock()

        app._save_button_clicked_callback(mock_kbutton, mock_pshbutton)

        assert app.settings["image type"] == "ps"
        assert app.settings["ps_backend"] == "libtiff"
        app._save_file_chooser.assert_called_with(["uuid1"])

    def test_save_button_clicked_callback_jpg(self, app):
        "Test _save_button_clicked_callback for JPG type."
        app._windowi = unittest.mock.Mock()
        app._windowi.image_type = "jpg"
        app._windowi.jpeg_quality = 90
        app._windowi.comboboxpsh.get_active.return_value = -1
        app._list_of_page_uuids = unittest.mock.Mock(return_value=["uuid1"])
        app._save_image = unittest.mock.Mock()
        mock_kbutton = unittest.mock.Mock()
        mock_pshbutton = unittest.mock.Mock()

        app._save_button_clicked_callback(mock_kbutton, mock_pshbutton)

        assert app.settings["image type"] == "jpg"
        assert app.settings["quality"] == 90
        app._save_image.assert_called_with(["uuid1"])

    @unittest.mock.patch("file_menu_mixins.Gtk")
    @unittest.mock.patch("file_menu_mixins.os")
    @unittest.mock.patch("file_menu_mixins.expand_metadata_pattern")
    def test_save_file_chooser_pdf(
        self, mock_expand_metadata_pattern, mock_os, mock_gtk, app
    ):
        "The save file chooser dialog is correctly invoked for PDF files."
        app._windowi = unittest.mock.Mock()
        app._windowi.meta_datetime = "datetime"
        mock_expand_metadata_pattern.return_value = "filename.pdf"
        mock_dialog = unittest.mock.Mock()
        mock_gtk.FileChooserDialog.return_value = mock_dialog

        app._save_file_chooser(["uuid1"])

        mock_gtk.FileChooserDialog.assert_called_once()
        mock_dialog.set_current_name.assert_called_with("filename.pdf")
        mock_dialog.connect.assert_called_once()
        mock_dialog.show.assert_called_once()
        assert mock_os.chdir.call_count >= 2

    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_save_file_chooser_djvu(self, mock_gtk, app):
        "The save file chooser dialog is correctly invoked for DjVu image type."
        app.settings["image type"] = "djvu"
        app._windowi = unittest.mock.Mock()
        mock_dialog = unittest.mock.Mock()
        mock_gtk.FileChooserDialog.return_value = mock_dialog

        app._save_file_chooser(["uuid1"])

        mock_gtk.FileChooserDialog.assert_called_once()
        mock_dialog.connect.assert_called_once()
        mock_dialog.show.assert_called_once()

    def test_list_of_page_uuids(self, app):
        "_list_of_page_uuids returns correct UUIDs."
        app.slist.get_page_index = unittest.mock.Mock(return_value=[0, 2])
        app.slist.data = [[0, 0, "uuid1"], [0, 0, "uuid2"], [0, 0, "uuid3"]]
        app.settings["Page range"] = "1,3"

        uuids = app._list_of_page_uuids()

        assert uuids == ["uuid1", "uuid3"]
        app.slist.get_page_index.assert_called_with("1,3", app._error_callback)

    @unittest.mock.patch("file_menu_mixins.os")
    @unittest.mock.patch("file_menu_mixins.re")
    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_file_chooser_response_callback_ok_pdf(
        self, mock_gtk, mock_re, mock_os, app
    ):
        "Test _file_chooser_response_callback for PDF type."
        app._save_pdf = unittest.mock.Mock()
        app._file_writable = unittest.mock.Mock(return_value=True)
        app.settings["close_dialog_on_save"] = True
        app._windowi = unittest.mock.Mock()
        mock_dialog = unittest.mock.Mock()
        mock_dialog.get_filename.return_value = "/path/to/file.pdf"
        mock_re.search.return_value = True
        mock_os.path.dirname.return_value = "/path/to"

        app._file_chooser_response_callback(
            mock_dialog, mock_gtk.ResponseType.OK, ["pdf", ["uuid1"]]
        )

        mock_dialog.get_filename.assert_called_once()
        assert app.settings["cwd"] == "/path/to"
        app._save_pdf.assert_called_with("/path/to/file.pdf", ["uuid1"], "pdf")
        app._windowi.hide.assert_called_once()
        mock_dialog.destroy.assert_called_once()

    @unittest.mock.patch("file_menu_mixins.os")
    @unittest.mock.patch("file_menu_mixins.Gtk")
    @unittest.mock.patch("file_menu_mixins.tempfile")
    def test_file_chooser_response_callback_ok_ps_libtiff(
        self, mock_tempfile, mock_gtk, mock_os, app
    ):
        "Test _file_chooser_response_callback for PS type with libtiff backend."
        app._save_tif = unittest.mock.Mock()
        app._file_writable = unittest.mock.Mock(return_value=True)
        app.settings["ps_backend"] = "libtiff"
        mock_dialog = unittest.mock.Mock()
        mock_dialog.get_filename.return_value = "/path/to/file.ps"
        mock_os.path.dirname.return_value = "/path/to"

        mock_tif = unittest.mock.Mock()
        mock_tif.filename.return_value = "temp.tif"
        mock_tempfile.TemporaryFile.return_value = mock_tif

        app._file_chooser_response_callback(
            mock_dialog, mock_gtk.ResponseType.OK, ["ps", ["uuid1"]]
        )

        app._save_tif.assert_called_with("temp.tif", ["uuid1"], "/path/to/file.ps")

    @unittest.mock.patch("file_menu_mixins.os")
    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_file_chooser_response_callback_ok_ps_pdf(self, mock_gtk, mock_os, app):
        "Test _file_chooser_response_callback for PS type with PDF backend."
        app._save_pdf = unittest.mock.Mock()
        app._file_writable = unittest.mock.Mock(return_value=True)
        app.settings["ps_backend"] = "pdf"
        mock_dialog = unittest.mock.Mock()
        mock_dialog.get_filename.return_value = "/path/to/file.ps"
        mock_os.path.dirname.return_value = "/path/to"

        app._file_chooser_response_callback(
            mock_dialog, mock_gtk.ResponseType.OK, ["ps", ["uuid1"]]
        )

        app._save_pdf.assert_called_with("/path/to/file.ps", ["uuid1"], "ps")

    @unittest.mock.patch("file_menu_mixins.os")
    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_file_chooser_response_callback_ok_formats(self, mock_gtk, mock_os, app):
        "Test _file_chooser_response_callback for multiple formats."
        app._file_writable = unittest.mock.Mock(return_value=True)
        mock_dialog = unittest.mock.Mock()
        mock_os.path.dirname.return_value = "/path/to"

        for fmt in ["djvu", "tif", "txt", "hocr"]:
            mock_dialog.get_filename.return_value = f"/path/to/file.{fmt}"
            save_method = unittest.mock.Mock()
            setattr(app, f"_save_{fmt}", save_method)

            app._file_chooser_response_callback(
                mock_dialog, mock_gtk.ResponseType.OK, [fmt, ["uuid1"]]
            )
            save_method.assert_called_with(f"/path/to/file.{fmt}", ["uuid1"])

    @unittest.mock.patch("file_menu_mixins.os")
    def test_file_writable_errors(self, mock_os, app):
        "Test _file_writable error cases."
        app._show_message_dialog = unittest.mock.Mock()
        mock_chooser = unittest.mock.Mock()

        # Case 1: Directory not writable
        mock_os.path.dirname.return_value = "/read-only-dir"
        mock_os.access.return_value = False
        assert not app._file_writable(mock_chooser, "/read-only-dir/file.pdf")
        app._show_message_dialog.assert_called()

        # Case 2: File exists but not writable
        app._show_message_dialog.reset_mock()
        mock_os.path.dirname.return_value = "/tmp"
        mock_os.access.side_effect = [True, False]  # dir writable, file not
        mock_os.path.isfile.return_value = True
        assert not app._file_writable(mock_chooser, "/tmp/readonly.pdf")
        app._show_message_dialog.assert_called()

    @unittest.mock.patch("file_menu_mixins.collate_metadata")
    @unittest.mock.patch("file_menu_mixins.datetime")
    def test_save_pdf(self, mock_datetime, mock_collate_metadata, app):
        "Test _save_pdf calls save_pdf with correct arguments."
        app.slist.save_pdf = unittest.mock.Mock()
        app._windowi = unittest.mock.Mock()
        app._windowi.pdf_user_password = "password"
        mock_collate_metadata.return_value = "metadata"
        mock_datetime.datetime.now.return_value = "now"
        app.settings["post_save_hook"] = True

        app._save_pdf("file.pdf", ["uuid1"], "pdf")

        app.slist.save_pdf.assert_called_with(
            path="file.pdf",
            list_of_pages=["uuid1"],
            metadata="metadata",
            options={
                "compression": "jpeg",
                "downsample": True,
                "downsample dpi": 150,
                "quality": 80,
                "user-password": "password",
                "set_timestamp": True,
                "convert whitespace to underscores": True,
                "post_save_hook": "tool",
            },
            queued_callback=app.post_process_progress.queued,
            started_callback=app.post_process_progress.update,
            running_callback=app.post_process_progress.update,
            finished_callback=unittest.mock.ANY,
            error_callback=app._error_callback,
        )

    def test_save_pdf_variants(self, app):
        "Test _save_pdf with prepend/append/ps options."
        app.slist.save_pdf = unittest.mock.Mock()
        app._windowi = unittest.mock.Mock()

        app._save_pdf("file.pdf", ["uuid1"], "prependpdf")
        assert app.slist.save_pdf.call_args[1]["options"]["prepend"] == "file.pdf"

        app._save_pdf("file.pdf", ["uuid1"], "appendpdf")
        assert app.slist.save_pdf.call_args[1]["options"]["append"] == "file.pdf"

        app.settings["ps_backend"] = "pdf2ps"
        app._save_pdf("file.ps", ["uuid1"], "ps")
        assert app.slist.save_pdf.call_args[1]["options"]["ps"] == "file.ps"
        assert app.slist.save_pdf.call_args[1]["options"]["pstool"] == "pdf2ps"

    @unittest.mock.patch("file_menu_mixins.launch_default_for_file")
    def test_save_pdf_finished_callback(self, mock_launch, app):
        "Test finished callback for _save_pdf launches file and sets saved."
        response = unittest.mock.Mock()
        app.slist.thread.send = unittest.mock.Mock()
        app._windowi = unittest.mock.Mock()

        # The callback is defined inside _save_pdf, so we need to call it from there
        app.slist.save_pdf = lambda path, list_of_pages, metadata, options, queued_callback, started_callback, running_callback, finished_callback, error_callback: finished_callback(  # pylint: disable=line-too-long
            response
        )
        app._save_pdf("file.pdf", ["uuid1"], "pdf")

        app.post_process_progress.finish.assert_called_with(response)
        app.slist.thread.send.assert_called_with("set_saved", ["uuid1"])
        mock_launch.assert_called_with("file.pdf")

    @unittest.mock.patch("file_menu_mixins.launch_default_for_file")
    def test_save_pdf_finished_callback_ps(self, mock_launch, app):
        "Test finished callback for _save_pdf launches file for ps."
        response = unittest.mock.Mock()
        app.slist.thread.send = unittest.mock.Mock()
        app._windowi = unittest.mock.Mock()

        # The callback is defined inside _save_pdf, so we need to call it from there
        app.slist.save_pdf = lambda path, list_of_pages, metadata, options, queued_callback, started_callback, running_callback, finished_callback, error_callback: finished_callback(  # pylint: disable=line-too-long
            response
        )
        app._save_pdf("file.ps", ["uuid1"], "ps")

        app.post_process_progress.finish.assert_called_with(response)
        app.slist.thread.send.assert_called_with("set_saved", ["uuid1"])
        mock_launch.assert_called_with("file.ps")

    @unittest.mock.patch("file_menu_mixins.launch_default_for_file")
    def test_save_djvu_finished_callback(self, mock_launch, app):
        "Test finished callback for _save_djvu launches file and sets saved."
        response = unittest.mock.Mock()
        response.request.args = [{"path": "file.djvu"}]
        app.slist.thread.send = unittest.mock.Mock()
        app.settings["post_save_hook"] = True

        # The callback is defined inside _save_djvu, so we need to call it from there
        app.slist.save_djvu = lambda path, list_of_pages, metadata, options, queued_callback, started_callback, running_callback, finished_callback, error_callback: finished_callback(  # pylint: disable=line-too-long
            response
        )
        app._save_djvu("file.djvu", ["uuid1"])

        app.post_process_progress.finish.assert_called_with(response)
        app.slist.thread.send.assert_called_with("set_saved", ["uuid1"])
        mock_launch.assert_called_with("file.djvu")

    @unittest.mock.patch("file_menu_mixins.Gtk")
    @unittest.mock.patch("file_menu_mixins.file_exists")
    @unittest.mock.patch("file_menu_mixins.os")
    def test_save_image_logic(self, mock_os, mock_file_exists, mock_gtk, app):
        "Test _save_image with multiple pages and overwrite check."
        app.slist.save_image = unittest.mock.Mock()
        app._windowi = unittest.mock.Mock()
        app.settings["image type"] = "png"
        app._file_writable = unittest.mock.Mock(return_value=True)
        app._show_message_dialog = unittest.mock.Mock()
        mock_dialog = unittest.mock.Mock()
        mock_dialog.run.return_value = mock_gtk.ResponseType.OK
        mock_dialog.get_filename.return_value = "/path/to/image"
        mock_gtk.FileChooserDialog.return_value = mock_dialog
        mock_file_exists.return_value = False

        # Multiple pages overwrite case
        mock_os.path.isfile.return_value = True
        app._save_image(["uuid1", "uuid2"])
        app._show_message_dialog.assert_called()

        # Single page success
        mock_os.path.isfile.return_value = False
        app._save_image(["uuid1"])
        app.slist.save_image.assert_called()
        app._windowi.hide.assert_called_once()

    @unittest.mock.patch("file_menu_mixins.Gtk")
    @unittest.mock.patch("file_menu_mixins.file_exists")
    def test_save_image_file_exists(self, mock_file_exists, mock_gtk, app):
        "Test _save_image with multiple pages and overwrite check."
        app.slist.save_image = unittest.mock.Mock()
        app.settings["image type"] = "png"
        app._show_message_dialog = unittest.mock.Mock()
        mock_dialog = unittest.mock.Mock()
        mock_dialog.run.return_value = mock_gtk.ResponseType.OK
        mock_dialog.get_filename.return_value = "/path/to/image"
        mock_gtk.FileChooserDialog.return_value = mock_dialog
        mock_file_exists.return_value = True
        app._save_image(["uuid1"])
        app.slist.save_image.assert_not_called()

    @unittest.mock.patch("file_menu_mixins.Gtk")
    @unittest.mock.patch("file_menu_mixins.file_exists")
    def test_save_image_file_not_writable(self, mock_file_exists, mock_gtk, app):
        "Test _save_image with multiple pages and overwrite check."
        app.slist.save_image = unittest.mock.Mock()
        app.settings["image type"] = "png"
        app._file_writable = unittest.mock.Mock(return_value=False)
        app._show_message_dialog = unittest.mock.Mock()
        mock_dialog = unittest.mock.Mock()
        mock_dialog.run.return_value = mock_gtk.ResponseType.OK
        mock_dialog.get_filename.return_value = "/path/to/image.png"
        mock_gtk.FileChooserDialog.return_value = mock_dialog
        mock_file_exists.return_value = False
        app._save_image(["uuid1"])
        app._file_writable.assert_called_once_with(mock_dialog, "/path/to/image.png")
        app.slist.save_image.assert_not_called()

    @unittest.mock.patch("file_menu_mixins.PrintOperation")
    def test_print_dialog(self, mock_print_op, app):
        "Test print dialog"
        mock_op = unittest.mock.Mock()
        mock_print_op.return_value = mock_op
        mock_op.run.return_value = Gtk.PrintOperationResult.APPLY
        mock_op.get_print_settings.return_value = "new_settings"

        app.print_dialog(None, None)

        mock_op.run.assert_called()
        assert app.print_settings == "new_settings"

    @unittest.mock.patch("file_menu_mixins.ComboBoxText")
    def test_update_post_save_hooks(self, mock_combobox, app):
        "Test update post save hooks"
        app._windowi = unittest.mock.Mock(spec=[])  # No comboboxpsh

        app._update_post_save_hooks()

        mock_combobox.assert_called()
        assert hasattr(app._windowi, "comboboxpsh")
        app._windowi.comboboxpsh.append_text.assert_called()

    def test_update_post_save_hooks_existing(self, app):
        "Test update post save hooks existing"
        app._windowi = unittest.mock.Mock()
        app._windowi.comboboxpsh = unittest.mock.Mock()
        app._windowi.comboboxpsh.get_num_rows.return_value = 1

        app._update_post_save_hooks()

        app._windowi.comboboxpsh.remove.assert_called()
        app._windowi.comboboxpsh.append_text.assert_called()

    @unittest.mock.patch("file_menu_mixins.os.execv")
    def test_restart(self, mock_execv, app):
        "Test restart"
        app._can_quit = unittest.mock.Mock()

        app._restart()

        app._can_quit.assert_called()
        mock_execv.assert_called()

    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_save_image_multiple(self, mock_gtk, app):
        "Test save image multiple"
        app.slist.save_image = unittest.mock.Mock()
        app.settings["image type"] = "png"
        mock_dialog = unittest.mock.Mock()
        mock_dialog.run.return_value = mock_gtk.ResponseType.OK
        mock_dialog.get_filename.return_value = "/path/to/image.png"
        mock_gtk.FileChooserDialog.return_value = mock_dialog

        app._save_image(["uuid1", "uuid2"])

        app.slist.save_image.assert_called()
        args = app.slist.save_image.call_args[1]
        assert "%0$2d" in args["path"]

    def test_update_post_save_hooks_filter(self, app):
        "Test that tools with %o are filtered out."
        app.settings["user_defined_tools"] = ["tool1", "tool2 %o"]
        app._windowi = unittest.mock.Mock()
        app._windowi.comboboxpsh = unittest.mock.Mock()
        app._windowi.comboboxpsh.get_num_rows.return_value = 0

        app._update_post_save_hooks()

        app._windowi.comboboxpsh.append_text.assert_called_once_with("tool1")

    def test_save_button_clicked_callback_session(self, app):
        "Test _save_button_clicked_callback for session type."
        app._windowi = unittest.mock.Mock()
        app._windowi.image_type = "session"
        app._windowi.comboboxpsh.get_active.return_value = -1
        app._list_of_page_uuids = unittest.mock.Mock(return_value=["uuid1"])
        app._save_file_chooser = unittest.mock.Mock()
        mock_kbutton = unittest.mock.Mock()
        mock_pshbutton = unittest.mock.Mock()

        app._save_button_clicked_callback(mock_kbutton, mock_pshbutton)

        assert app.settings["image type"] == "session"
        app._save_file_chooser.assert_called_with(["uuid1"])

    def test_save_button_clicked_callback_hocr(self, app):
        "Test _save_button_clicked_callback for hocr type."
        app._windowi = unittest.mock.Mock()
        app._windowi.image_type = "hocr"
        app._windowi.comboboxpsh.get_active.return_value = -1
        app._list_of_page_uuids = unittest.mock.Mock(return_value=["uuid1"])
        app._save_file_chooser = unittest.mock.Mock()
        mock_kbutton = unittest.mock.Mock()
        mock_pshbutton = unittest.mock.Mock()

        app._save_button_clicked_callback(mock_kbutton, mock_pshbutton)

        assert app.settings["image type"] == "hocr"
        app._save_file_chooser.assert_called_with(["uuid1"])

    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_save_file_chooser_others(self, mock_gtk, app):
        "Test save file chooser for other types."
        app._windowi = unittest.mock.Mock()
        mock_dialog = unittest.mock.Mock()
        mock_gtk.FileChooserDialog.return_value = mock_dialog

        for image_type in ["tif", "txt", "hocr", "ps", "session"]:
            app.settings["image type"] = image_type
            app._save_file_chooser(["uuid1"])
            mock_gtk.FileChooserDialog.assert_called()
            mock_gtk.FileChooserDialog.reset_mock()

    @unittest.mock.patch("file_menu_mixins.file_exists")
    @unittest.mock.patch("file_menu_mixins.os")
    def test_file_chooser_response_callback_append_extension(
        self, mock_os, mock_file_exists, app
    ):
        "Test appending extension if missing."
        app._save_pdf = unittest.mock.Mock()
        app._file_writable = unittest.mock.Mock(return_value=True)
        mock_dialog = unittest.mock.Mock()
        mock_dialog.get_filename.return_value = "/path/to/file"
        mock_os.path.dirname.return_value = "/path/to"
        mock_file_exists.return_value = False

        app._file_chooser_response_callback(
            mock_dialog, Gtk.ResponseType.OK, ["pdf", ["uuid1"]]
        )

        app._save_pdf.assert_called_with("/path/to/file.pdf", ["uuid1"], "pdf")

    @unittest.mock.patch("file_menu_mixins.file_exists")
    def test_file_chooser_response_callback_file_exists_abort(
        self, mock_file_exists, app
    ):
        "Test abort if file exists and user cancels."
        mock_dialog = unittest.mock.Mock()
        mock_dialog.get_filename.return_value = "/path/to/file.pdf"
        mock_file_exists.return_value = True

        app._file_chooser_response_callback(
            mock_dialog, Gtk.ResponseType.OK, ["pdf", ["uuid1"]]
        )

        app._save_pdf = unittest.mock.Mock()
        app._save_pdf.assert_not_called()

    @unittest.mock.patch("file_menu_mixins.file_exists")
    def test_file_chooser_response_callback_file_exists_suffix(
        self, mock_file_exists, app
    ):
        "Test abort if file exists after adding suffix and user cancels."
        mock_dialog = unittest.mock.Mock()
        mock_dialog.get_filename.return_value = "/path/to/file"
        mock_file_exists.return_value = True

        app._file_chooser_response_callback(
            mock_dialog, Gtk.ResponseType.OK, ["pdf", ["uuid1"]]
        )

        app._save_pdf = unittest.mock.Mock()
        app._save_pdf.assert_not_called()

    @unittest.mock.patch("file_menu_mixins.os")
    def test_file_chooser_response_callback_session(self, mock_os, app):
        "Test saving session."
        app.slist.save_session = unittest.mock.Mock()
        app._file_writable = unittest.mock.Mock(return_value=True)
        mock_dialog = unittest.mock.Mock()
        mock_dialog.get_filename.return_value = "/path/to/session.gs2p"
        mock_os.path.dirname.return_value = "/path/to"
        mock_os.path.isfile.return_value = False

        app._file_chooser_response_callback(
            mock_dialog, Gtk.ResponseType.OK, ["session", []]
        )

        app.slist.save_session.assert_called()

    @unittest.mock.patch("file_menu_mixins.launch_default_for_file")
    def test_save_tif_finished_callback(self, mock_launch, app):
        "Test finished callback for _save_tif."
        response = unittest.mock.Mock()
        response.request.args = [{"path": "file.tif"}]
        app.slist.thread.send = unittest.mock.Mock()
        app.settings["post_save_hook"] = True

        def mock_save_tiff(finished_callback, **_kwargs):
            finished_callback(response)

        app.slist.save_tiff = mock_save_tiff

        app._save_tif("file.tif", ["uuid1"])

        app.post_process_progress.finish.assert_called_with(response)
        app.slist.thread.send.assert_called_with("set_saved", ["uuid1"])
        mock_launch.assert_called_with("file.tif")

    @unittest.mock.patch("file_menu_mixins.launch_default_for_file")
    def test_save_txt_finished_callback(self, mock_launch, app):
        "Test finished callback for _save_txt."
        response = unittest.mock.Mock()
        app.slist.thread.send = unittest.mock.Mock()
        app.settings["post_save_hook"] = True

        def mock_save_text(finished_callback, **_kwargs):
            finished_callback(response)

        app.slist.save_text = mock_save_text

        app._save_txt("file.txt", ["uuid1"])

        app.post_process_progress.finish.assert_called_with(response)
        mock_launch.assert_called_with("file.txt")

    @unittest.mock.patch("file_menu_mixins.launch_default_for_file")
    def test_save_hocr_finished_callback(self, mock_launch, app):
        "Test finished callback for _save_hocr."
        response = unittest.mock.Mock()
        app.slist.thread.send = unittest.mock.Mock()
        app.settings["post_save_hook"] = True

        def mock_save_hocr(finished_callback, **_kwargs):
            finished_callback(response)

        app.slist.save_hocr = mock_save_hocr

        app._save_hocr("file.hocr", ["uuid1"])

        app.post_process_progress.finish.assert_called_with(response)
        mock_launch.assert_called_with("file.hocr")

    @unittest.mock.patch("file_menu_mixins.launch_default_for_file")
    @unittest.mock.patch("file_menu_mixins.Gtk")
    @unittest.mock.patch("file_menu_mixins.os")
    def test_save_image_finished_callback(self, mock_os, mock_gtk, mock_launch, app):
        "Test finished callback for _save_image."
        response = unittest.mock.Mock()
        response.request.args = [{"path": "file%d.jpg"}]
        app.slist.thread.send = unittest.mock.Mock()

        # Mock dialog to return success
        mock_dialog = unittest.mock.Mock()
        mock_dialog.run.return_value = mock_gtk.ResponseType.OK
        mock_dialog.get_filename.return_value = "/path/to/file.jpg"
        mock_gtk.FileChooserDialog.return_value = mock_dialog

        mock_os.path.isfile.return_value = False
        mock_os.path.dirname.return_value = "/path/to"
        mock_os.access.return_value = True

        def mock_save_image(finished_callback, **_kwargs):
            finished_callback(response)

        # Single file
        app.slist.save_image = mock_save_image
        app._save_image(["uuid1"])
        mock_launch.assert_called_with("file%d.jpg")

        # Multiple files
        mock_launch.reset_mock()
        # The callback logic uses the length of uuids captured in closure.
        # calling _save_image(["uuid1", "uuid2"]) -> len(uuids) is 2.
        # filename in launch_default_for_file(filename % (i))
        app._save_image(["uuid1", "uuid2"])
        assert mock_launch.call_count == 2

    def test_list_of_page_uuids_empty(self, app):
        "Test _list_of_page_uuids returning empty."
        app.slist.get_page_index = unittest.mock.Mock(return_value=[])
        assert app._list_of_page_uuids() == []
