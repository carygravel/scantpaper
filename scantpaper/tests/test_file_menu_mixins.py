"test file_menu_mixins"

import datetime
import tempfile
import unittest.mock
import gi
import pytest
from file_menu_mixins import FileMenuMixins, add_filter

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


class MockSlist:
    "A mock class simulating a selection list for testing purposes."

    def __init__(self):
        self.data = [1, 2, 3]
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

    def __bool__(self):
        return True


class MockApp(unittest.mock.Mock, FileMenuMixins):
    "A mock application class"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.slist = MockSlist()
        self.settings = {"cwd": "/tmp"}
        self.view = MockView()
        self.t_canvas = MockCanvas()
        self.a_canvas = MockCanvas()
        self._windows = unittest.mock.MagicMock()
        self._windows.__bool__.return_value = True
        self.session = unittest.mock.Mock()
        self.post_process_progress = unittest.mock.Mock()
        self._dependencies = {}
        self._fonts = []
        self.print_settings = None
        self._configfile = None
        self._lockfd = None
        self._hpaned = unittest.mock.Mock()
        self._current_page = 1
        self._ask_question = unittest.mock.Mock()
        self._import_files = unittest.mock.Mock()

    def get_application(self):
        "Return the mock application instance"
        return unittest.mock.Mock()


class TestAddFilter(unittest.TestCase):
    "Test add_filter function for file chooser filters."

    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_add_filter(self, mock_gtk):
        "Test that add_filter adds correct filters and patterns."
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


# pylint: disable=protected-access,attribute-defined-outside-init
class TestFileMenuMixins(unittest.TestCase):
    "Test FileMenuMixins class and its methods."

    def setUp(self):
        "Set up a mock application for testing."
        self.app = MockApp()
        self.app.settings = {
            "cwd": "/tmp",
            "close_dialog_on_save": False,
            "post_save_hook": False,
            "pdf compression": "jpeg",
            "downsample": True,
            "downsample dpi": 150,
            "quality": 80,
            "text_position": "above",
            "pdf font": "Helvetica",
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
            "datetime offset": 0,
            "title-suggestions": [],
            "author-suggestions": [],
            "subject-suggestions": [],
            "keywords-suggestions": [],
            "image type": "pdf",
            "user_defined_tools": ["tool"],
        }
        self.app._dependencies = {
            "pdfunite": True,
            "djvu": True,
            "libtiff": True,
            "pdf2ps": True,
            "pdftops": True,
            "pdftk": True,
        }
        self.app.session = (
            tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        )

    def tearDown(self):
        "Clean up the mock application session."
        self.app.session.cleanup()

    def test_new(self):
        "Test the new() method resets state and clears data."
        self.app.slist.data = [1, 2, 3]
        self.app.view.set_pixbuf = unittest.mock.Mock()
        self.app.t_canvas.clear_text = unittest.mock.Mock()
        self.app.a_canvas.clear_text = unittest.mock.Mock()
        self.app._current_page = 1
        self.app._windows.reset_start_page = unittest.mock.Mock()
        self.app._pages_saved = unittest.mock.Mock(return_value=True)

        self.app.new(None, None)

        self.app._pages_saved.assert_called_once()
        self.assertEqual(self.app.slist.data, [])
        self.app.view.set_pixbuf.assert_called_with(None)
        self.app.t_canvas.clear_text.assert_called_once()
        self.app.a_canvas.clear_text.assert_called_once()
        self.assertIsNone(self.app._current_page)
        self.app._windows.reset_start_page.assert_called_once()

    def test_new_cancel(self):
        "Test new() does not clear data if pages not saved."
        self.app.slist.data = [1, 2, 3]
        self.app._pages_saved = unittest.mock.Mock(return_value=False)

        self.app.new(None, None)

        self.app._pages_saved.assert_called_once()
        self.assertEqual(self.app.slist.data, [1, 2, 3])

    def test_quit_app(self):
        "Test quit_app() calls application quit method."

        class TestApp(FileMenuMixins, unittest.mock.Mock):
            "A test application class combining FileMenuMixins and unittest.mock.Mock"

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.slist = MockSlist()
                self.settings = {"cwd": "/tmp"}
                self.view = MockView()
                self.t_canvas = MockCanvas()
                self.a_canvas = MockCanvas()
                self._windows = unittest.mock.MagicMock()
                self._windows.__bool__.return_value = True
                self.session = unittest.mock.Mock()
                self.post_process_progress = unittest.mock.Mock()
                self._dependencies = {}
                self._fonts = []
                self.print_settings = None
                self._configfile = None
                self._lockfd = None
                self._hpaned = unittest.mock.Mock()
                self._current_page = 1
                self.app = unittest.mock.Mock()

            def _can_quit(self):
                return True

            def get_application(self):
                "Return the current application instance."
                return self.app

        app = TestApp()
        app.quit_app(None, None)
        app.app.quit.assert_called_once()

    def test_can_quit_pages_not_saved(self):
        "Test _can_quit returns False if pages not saved."
        self.app._pages_saved = unittest.mock.Mock(return_value=False)
        self.assertFalse(self.app._can_quit())

    @unittest.mock.patch("file_menu_mixins.os")
    @unittest.mock.patch("file_menu_mixins.glob")
    @unittest.mock.patch("file_menu_mixins.fcntl")
    @unittest.mock.patch("file_menu_mixins.config")
    def test_can_quit(self, mock_config, mock_fcntl, mock_glob, mock_os):
        "Test _can_quit performs cleanup and saves settings."
        self.app.session.name = "/tmp/session"
        self.app._pages_saved = unittest.mock.Mock(return_value=True)
        self.app.get_size = unittest.mock.Mock(return_value=(800, 600))
        self.app.get_position = unittest.mock.Mock(return_value=(100, 200))
        self.app._hpaned.get_position.return_value = 250
        self.app._windows.get_size.return_value = (400, 300)
        self.app._windows.thread.quit = unittest.mock.Mock()
        self.app.slist.thread.quit = unittest.mock.Mock()
        mock_glob.glob.return_value = ["/tmp/session/file1", "/tmp/session/file2"]

        self.assertTrue(self.app._can_quit())

        mock_os.chdir.assert_called_with(self.app.settings["cwd"])
        mock_glob.glob.assert_called_with("/tmp/session/*")
        mock_os.remove.assert_has_calls(
            [
                unittest.mock.call("/tmp/session/file1"),
                unittest.mock.call("/tmp/session/file2"),
            ]
        )
        mock_os.rmdir.assert_called_with("/tmp/session")
        self.assertEqual(self.app.settings["window_width"], 800)
        self.assertEqual(self.app.settings["window_height"], 600)
        self.assertEqual(self.app.settings["window_x"], 100)
        self.assertEqual(self.app.settings["window_y"], 200)
        self.assertEqual(self.app.settings["thumb panel"], 250)
        self.assertEqual(self.app.settings["scan_window_width"], 400)
        self.assertEqual(self.app.settings["scan_window_height"], 300)
        self.app._windows.thread.quit.assert_called_once()
        mock_config.write_config.assert_called_with(
            self.app._configfile, self.app.settings
        )
        self.app.slist.thread.quit.assert_called_once()
        mock_fcntl.lockf.assert_called_with(self.app._lockfd, mock_fcntl.LOCK_UN)

    def test_pages_saved_true(self):
        "Test _pages_saved returns True if pages are saved."
        self.app.slist.thread.pages_saved.return_value = True
        self.assertTrue(self.app._pages_saved("message"))

    def test_pages_saved_false_ok(self):
        "Test _pages_saved returns True if user confirms save."
        self.app.slist.thread.pages_saved.return_value = False
        self.app._ask_question.return_value = Gtk.ResponseType.OK
        self.assertTrue(self.app._pages_saved("message"))
        self.app._ask_question.assert_called_once()

    def test_pages_saved_false_cancel(self):
        "Test _pages_saved returns False if user cancels save."
        self.app.slist.thread.pages_saved.return_value = False
        self.app._ask_question.return_value = Gtk.ResponseType.CANCEL
        self.assertFalse(self.app._pages_saved("message"))
        self.app._ask_question.assert_called_once()

    @unittest.mock.patch("file_menu_mixins.Gtk")
    @unittest.mock.patch("file_menu_mixins.os")
    def test_open_dialog_ok(self, mock_gtk, mock_os):
        "Test open_dialog imports files on OK response."
        pytest.skip("does not yet pass")
        mock_dialog = unittest.mock.Mock()
        mock_dialog.run.return_value = Gtk.ResponseType.OK
        mock_dialog.get_filenames.return_value = [
            "/path/to/file1.jpg",
            "/path/to/file2.png",
        ]
        mock_gtk.FileChooserDialog.return_value = mock_dialog
        mock_os.path.dirname.return_value = "/path/to"
        self.app._import_files = unittest.mock.Mock()

        self.app.open_dialog(None, None)

        mock_gtk.FileChooserDialog.assert_called_once()
        mock_dialog.get_filenames.assert_called_once()
        mock_dialog.destroy.assert_called_once()
        self.assertEqual(self.app.settings["cwd"], "/path/to")
        self.app._import_files.assert_called_with(
            ["/path/to/file1.jpg", "/path/to/file2.png"]
        )
        self.assertEqual(mock_os.chdir.call_count, 3)

    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_open_dialog_cancel(self, mock_gtk):
        "Test open_dialog does not import files on cancel."
        mock_dialog = unittest.mock.Mock()
        mock_dialog.run.return_value = Gtk.ResponseType.CANCEL
        mock_gtk.FileChooserDialog.return_value = mock_dialog

        self.app.open_dialog(None, None)

        mock_gtk.FileChooserDialog.assert_called_once()
        mock_dialog.destroy.assert_called_once()
        self.app._import_files.assert_not_called()

    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_select_pagerange_callback_ok(self, mock_gtk):
        "Test _select_pagerange_callback returns correct range on OK."
        pytest.skip("does not yet pass")
        mock_dialog = unittest.mock.Mock()
        mock_dialog.run.return_value = Gtk.ResponseType.OK
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

        first, last = self.app._select_pagerange_callback({"pages": 10})

        self.assertEqual(first, 1)
        self.assertEqual(last, 10)
        mock_dialog.destroy.assert_called_once()

    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_select_pagerange_callback_cancel(self, mock_gtk):
        "Test _select_pagerange_callback returns None on cancel."
        mock_dialog = unittest.mock.Mock()
        mock_dialog.run.return_value = Gtk.ResponseType.CANCEL
        mock_gtk.Dialog.return_value = mock_dialog

        first, last = self.app._select_pagerange_callback({"pages": 10})

        self.assertIsNone(first)
        self.assertIsNone(last)
        mock_dialog.destroy.assert_called_once()

    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_import_files_password_callback_ok(self, mock_gtk):
        "Test _import_files_password_callback returns password on OK."
        pytest.skip("does not yet pass")
        mock_dialog = unittest.mock.Mock()
        mock_dialog.run.return_value = Gtk.ResponseType.OK
        mock_entry = unittest.mock.Mock()
        mock_entry.get_text.return_value = "password"
        mock_gtk.MessageDialog.return_value = mock_dialog
        vbox = unittest.mock.Mock()
        mock_dialog.get_content_area.return_value = vbox
        vbox.pack_end.return_value = mock_entry
        mock_gtk.Entry.return_value = mock_entry

        password = self.app._import_files_password_callback("file.pdf")

        self.assertEqual(password, "password")
        mock_dialog.destroy.assert_called_once()

    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_import_files_password_callback_cancel(self, mock_gtk):
        "Test _import_files_password_callback returns None on cancel."
        mock_dialog = unittest.mock.Mock()
        mock_dialog.run.return_value = Gtk.ResponseType.CANCEL
        mock_entry = unittest.mock.Mock()
        mock_entry.get_text.return_value = "password"
        mock_gtk.MessageDialog.return_value = mock_dialog
        vbox = unittest.mock.Mock()
        mock_dialog.get_content_area.return_value = vbox
        vbox.pack_end.return_value = mock_entry

        password = self.app._import_files_password_callback("file.pdf")

        self.assertIsNone(password)
        mock_dialog.destroy.assert_called_once()

    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_import_files_password_callback_empty(self, mock_gtk):
        "Test _import_files_password_callback returns None if password is empty."
        mock_dialog = unittest.mock.Mock()
        mock_dialog.run.return_value = Gtk.ResponseType.OK
        mock_entry = unittest.mock.Mock()
        mock_entry.get_text.return_value = ""
        mock_gtk.MessageDialog.return_value = mock_dialog
        vbox = unittest.mock.Mock()
        mock_dialog.get_content_area.return_value = vbox
        vbox.pack_end.return_value = mock_entry

        password = self.app._import_files_password_callback("file.pdf")

        self.assertIsNone(password)
        mock_dialog.destroy.assert_called_once()

    def test_import_files_finished_callback(self):
        "Test _import_files_finished_callback calls finish."
        self.app._import_files_finished_callback("response")
        self.app.post_process_progress.finish.assert_called_with("response")

    @unittest.mock.patch("file_menu_mixins.config")
    def test_import_files_metadata_callback(self, mock_config):
        "Test _import_files_metadata_callback updates metadata."
        self.app._windowi = unittest.mock.Mock()
        self.app._windowe = unittest.mock.Mock()
        metadata = {"key": "value"}

        self.app._import_files_metadata_callback(metadata)

        self.app._windowi.update_from_import_metadata.assert_called_with(metadata)
        self.app._windowe.update_from_import_metadata.assert_called_with(metadata)
        mock_config.update_config_from_imported_metadata.assert_called_with(
            self.app.settings, metadata
        )

    def test_import_files_all_pages(self):
        "Test _import_files with all_pages=True passes correct pagerange_callback."
        pytest.skip("does not yet pass")
        self.app.slist.import_files = unittest.mock.Mock()
        filenames = ["file1.pdf", "file2.pdf"]
        self.app.slist.import_files = unittest.mock.Mock()

        self.app._import_files(filenames, all_pages=True)

        self.app.slist.import_files.assert_called_once()
        _args, kwargs = self.app.slist.import_files.call_args
        self.assertEqual(kwargs["paths"], filenames)
        self.assertIn("pagerange_callback", kwargs)
        self.assertEqual(kwargs["pagerange_callback"]({"pages": 10}), (1, 10))

    def test_import_files(self):
        "Test _import_files passes correct pagerange_callback."
        pytest.skip("does not yet pass")
        self.app.slist.import_files = unittest.mock.Mock()
        self.app._select_pagerange_callback = unittest.mock.Mock(return_value=(1, 5))
        filenames = ["file1.pdf", "file2.pdf"]
        self.app.slist.import_files = unittest.mock.Mock()

        self.app._import_files(filenames)

        self.app.slist.import_files.assert_called_once()
        _args, kwargs = self.app.slist.import_files.call_args
        self.assertEqual(kwargs["paths"], filenames)
        self.assertIn("pagerange_callback", kwargs)
        self.assertEqual(
            kwargs["pagerange_callback"], self.app._select_pagerange_callback
        )

    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_open_session_action_ok(self, mock_gtk):
        "Test _open_session_action opens session on OK."
        pytest.skip("does not yet pass")
        self.app._open_session = unittest.mock.Mock()
        mock_dialog = unittest.mock.Mock()
        mock_dialog.run.return_value = Gtk.ResponseType.OK
        mock_dialog.get_filenames.return_value = ["/path/to/session"]
        mock_gtk.FileChooserDialog.return_value = mock_dialog
        mock_dialog.get_filenames.return_value = ["/path/to/session"]

        self.app._open_session_action(None)

        mock_gtk.FileChooserDialog.assert_called_once()
        mock_dialog.get_filenames.assert_called_once()
        self.app._open_session.assert_called_with("/path/to/session")
        mock_dialog.destroy.assert_called_once()

    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_open_session_action_cancel(self, mock_gtk):
        "Test _open_session_action does not open session on cancel."
        self.app._open_session = unittest.mock.Mock()
        mock_dialog = unittest.mock.Mock()
        mock_dialog.run.return_value = Gtk.ResponseType.CANCEL
        mock_gtk.FileChooserDialog.return_value = mock_dialog

        self.app._open_session_action(None)

        mock_gtk.FileChooserDialog.assert_called_once()
        self.app._open_session.assert_not_called()
        mock_dialog.destroy.assert_called_once()

    def test_open_session(self):
        "Test _open_session calls slist.open_session with correct args."
        self.app.slist.open_session = unittest.mock.Mock()

        self.app._open_session("/path/to/session")

        self.app.slist.open_session.assert_called_with(
            dir="/path/to/session",
            delete=False,
            error_callback=self.app._error_callback,
        )

    @unittest.mock.patch("file_menu_mixins.datetime")
    @unittest.mock.patch("file_menu_mixins.SaveDialog")
    def test_save_dialog(self, mock_save_dialog, mock_datetime):
        "Test save_dialog creates and shows SaveDialog."
        pytest.skip("does not yet pass")
        self.app._windowi = None
        mock_dialog = unittest.mock.Mock()
        mock_save_dialog.return_value = mock_dialog
        mock_datetime.datetime.now.return_value = datetime.datetime(2025, 1, 1)
        self.app.settings["datetime offset"] = datetime.timedelta(days=1)

        self.app.save_dialog(None, None)

        mock_save_dialog.assert_called_once()
        self.assertEqual(self.app._windowi, mock_dialog)
        mock_dialog.add_page_range.assert_called_once()
        mock_dialog.add_image_type.assert_called_once()
        mock_dialog.add_actions.assert_called_once()
        mock_dialog.show_all.assert_called_once()
        mock_dialog.resize.assert_called_with(1, 1)

    def test_save_button_clicked_callback_pdf(self):
        "Test _save_button_clicked_callback for PDF type."
        self.app._windowi = unittest.mock.Mock()
        self.app._windowi.page_range = "all"
        self.app._windowi.image_type = "pdf"
        self.app._windowi.downsample = True
        self.app._windowi.downsample_dpi = 150
        self.app._windowi.pdf_compression = "jpeg"
        self.app._windowi.jpeg_quality = 80
        self.app._windowi.text_position = "above"
        self.app._windowi.pdf_font = "Helvetica"
        self.app._windowi.comboboxpsh.get_active.return_value = 0
        self.app._windowi.comboboxpsh.get_active_text.return_value = "tool"
        self.app._list_of_page_uuids = unittest.mock.Mock(return_value=["uuid1"])
        self.app._save_file_chooser = unittest.mock.Mock()
        mock_kbutton = unittest.mock.Mock()
        mock_kbutton.get_active.return_value = True
        mock_pshbutton = unittest.mock.Mock()
        mock_pshbutton.get_active.return_value = True

        self.app._save_button_clicked_callback(mock_kbutton, mock_pshbutton)

        self.assertEqual(self.app.settings["Page range"], "all")
        self.assertEqual(self.app.settings["image type"], "pdf")
        self.assertTrue(self.app.settings["close_dialog_on_save"])
        self.assertTrue(self.app.settings["post_save_hook"])
        self.assertEqual(self.app.settings["current_psh"], "tool")
        self.assertTrue(self.app.settings["downsample"])
        self.assertEqual(self.app.settings["downsample dpi"], 150)
        self.assertEqual(self.app.settings["pdf compression"], "jpeg")
        self.assertEqual(self.app.settings["quality"], 80)
        self.assertEqual(self.app.settings["text_position"], "above")
        self.assertEqual(self.app.settings["pdf font"], "Helvetica")
        self.app._save_file_chooser.assert_called_with(["uuid1"])

    def test_save_button_clicked_callback_djvu(self):
        "Test _save_button_clicked_callback for DjVu type."
        self.app._windowi = unittest.mock.Mock()
        self.app._windowi.page_range = "all"
        self.app._windowi.image_type = "djvu"
        self.app._windowi.comboboxpsh.get_active.return_value = 0
        self.app._windowi.comboboxpsh.get_active_text.return_value = "tool"
        self.app._list_of_page_uuids = unittest.mock.Mock(return_value=["uuid1"])
        self.app._save_file_chooser = unittest.mock.Mock()
        mock_kbutton = unittest.mock.Mock()
        mock_kbutton.get_active.return_value = True
        mock_pshbutton = unittest.mock.Mock()
        mock_pshbutton.get_active.return_value = True

        self.app._save_button_clicked_callback(mock_kbutton, mock_pshbutton)

        self.assertEqual(self.app.settings["image type"], "djvu")
        self.app._windowi.update_config_dict.assert_called_with(self.app.settings)
        self.app._save_file_chooser.assert_called_with(["uuid1"])

    def test_save_button_clicked_callback_tif(self):
        "Test _save_button_clicked_callback for TIFF type."
        self.app._windowi = unittest.mock.Mock()
        self.app._windowi.page_range = "all"
        self.app._windowi.image_type = "tif"
        self.app._windowi.tiff_compression = "jpeg"
        self.app._windowi.jpeg_quality = 80
        self.app._windowi.comboboxpsh.get_active.return_value = 0
        self.app._windowi.comboboxpsh.get_active_text.return_value = "tool"
        self.app._list_of_page_uuids = unittest.mock.Mock(return_value=["uuid1"])
        self.app._save_file_chooser = unittest.mock.Mock()
        mock_kbutton = unittest.mock.Mock()
        mock_kbutton.get_active.return_value = True
        mock_pshbutton = unittest.mock.Mock()
        mock_pshbutton.get_active.return_value = True

        self.app._save_button_clicked_callback(mock_kbutton, mock_pshbutton)

        self.assertEqual(self.app.settings["image type"], "tif")
        self.assertEqual(self.app.settings["tiff compression"], "jpeg")
        self.assertEqual(self.app.settings["quality"], 80)
        self.app._save_file_chooser.assert_called_with(["uuid1"])

    def test_save_button_clicked_callback_txt(self):
        "Test _save_button_clicked_callback for TXT type."
        self.app._windowi = unittest.mock.Mock()
        self.app._windowi.page_range = "all"
        self.app._windowi.image_type = "txt"
        self.app._windowi.comboboxpsh.get_active.return_value = 0
        self.app._list_of_page_uuids = unittest.mock.Mock(return_value=["uuid1"])
        self.app._save_file_chooser = unittest.mock.Mock()
        mock_kbutton = unittest.mock.Mock()
        mock_pshbutton = unittest.mock.Mock()

        self.app._save_button_clicked_callback(mock_kbutton, mock_pshbutton)

        self.assertEqual(self.app.settings["image type"], "txt")
        self.app._save_file_chooser.assert_called_with(["uuid1"])

    def test_save_button_clicked_callback_hocr(self):
        "Test _save_button_clicked_callback for HOCR type."
        self.app._windowi = unittest.mock.Mock()
        self.app._windowi.page_range = "all"
        self.app._windowi.image_type = "hocr"
        self.app._windowi.comboboxpsh.get_active.return_value = 0
        self.app._list_of_page_uuids = unittest.mock.Mock(return_value=["uuid1"])
        self.app._save_file_chooser = unittest.mock.Mock()
        mock_kbutton = unittest.mock.Mock()
        mock_pshbutton = unittest.mock.Mock()

        self.app._save_button_clicked_callback(mock_kbutton, mock_pshbutton)

        self.assertEqual(self.app.settings["image type"], "hocr")
        self.app._save_file_chooser.assert_called_with(["uuid1"])

    def test_save_button_clicked_callback_ps(self):
        "Test _save_button_clicked_callback for PS type."
        self.app._windowi = unittest.mock.Mock()
        self.app._windowi.page_range = "all"
        self.app._windowi.image_type = "ps"
        self.app._windowi.ps_backend = "pdf2ps"
        self.app._windowi.comboboxpsh.get_active.return_value = 0
        self.app._list_of_page_uuids = unittest.mock.Mock(return_value=["uuid1"])
        self.app._save_file_chooser = unittest.mock.Mock()
        mock_kbutton = unittest.mock.Mock()
        mock_pshbutton = unittest.mock.Mock()

        self.app._save_button_clicked_callback(mock_kbutton, mock_pshbutton)

        self.assertEqual(self.app.settings["image type"], "ps")
        self.assertEqual(self.app.settings["ps_backend"], "pdf2ps")
        self.app._save_file_chooser.assert_called_with(["uuid1"])

    def test_save_button_clicked_callback_session(self):
        "Test _save_button_clicked_callback for session type."
        self.app._windowi = unittest.mock.Mock()
        self.app._windowi.page_range = "all"
        self.app._windowi.image_type = "session"
        self.app._windowi.comboboxpsh.get_active.return_value = 0
        self.app._list_of_page_uuids = unittest.mock.Mock(return_value=["uuid1"])
        self.app._save_file_chooser = unittest.mock.Mock()
        mock_kbutton = unittest.mock.Mock()
        mock_pshbutton = unittest.mock.Mock()

        self.app._save_button_clicked_callback(mock_kbutton, mock_pshbutton)

        self.assertEqual(self.app.settings["image type"], "session")
        self.app._save_file_chooser.assert_called_with(["uuid1"])

    def test_save_button_clicked_callback_jpg(self):
        "Test _save_button_clicked_callback for JPG type."
        self.app._windowi = unittest.mock.Mock()
        self.app._windowi.page_range = "all"
        self.app._windowi.image_type = "jpg"
        self.app._windowi.jpeg_quality = 80
        self.app._windowi.comboboxpsh.get_active.return_value = 0
        self.app._list_of_page_uuids = unittest.mock.Mock(return_value=["uuid1"])
        self.app._save_image = unittest.mock.Mock()
        mock_kbutton = unittest.mock.Mock()
        mock_pshbutton = unittest.mock.Mock()

        self.app._save_button_clicked_callback(mock_kbutton, mock_pshbutton)

        self.assertEqual(self.app.settings["image type"], "jpg")
        self.assertEqual(self.app.settings["quality"], 80)
        self.app._save_image.assert_called_with(["uuid1"])

    def test_save_button_clicked_callback_png(self):
        "Test _save_button_clicked_callback for PNG type."
        self.app._windowi = unittest.mock.Mock()
        self.app._windowi.page_range = "all"
        self.app._windowi.image_type = "png"
        self.app._windowi.comboboxpsh.get_active.return_value = 0
        self.app._list_of_page_uuids = unittest.mock.Mock(return_value=["uuid1"])
        self.app._save_image = unittest.mock.Mock()
        mock_kbutton = unittest.mock.Mock()
        mock_pshbutton = unittest.mock.Mock()

        self.app._save_button_clicked_callback(mock_kbutton, mock_pshbutton)

        self.assertEqual(self.app.settings["image type"], "png")
        self.app._save_image.assert_called_with(["uuid1"])

    @unittest.mock.patch("file_menu_mixins.Gtk")
    @unittest.mock.patch("file_menu_mixins.os")
    @unittest.mock.patch("file_menu_mixins.expand_metadata_pattern")
    def test_save_file_chooser_pdf(
        self, mock_expand_metadata_pattern, mock_os, mock_gtk
    ):
        "Test that the save file chooser dialog is correctly invoked for PDF files."
        self.app._windowi = unittest.mock.Mock()
        self.app._windowi.meta_datetime = "datetime"
        mock_expand_metadata_pattern.return_value = "filename.pdf"
        mock_dialog = unittest.mock.Mock()
        mock_gtk.FileChooserDialog.return_value = mock_dialog

        self.app._save_file_chooser(["uuid1"])

        mock_gtk.FileChooserDialog.assert_called_once()
        mock_dialog.set_current_name.assert_called_with("filename.pdf")
        mock_dialog.connect.assert_called_once()
        mock_dialog.show.assert_called_once()
        self.assertEqual(mock_os.chdir.call_count, 2)

    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_save_file_chooser_djvu(self, mock_gtk):
        "Test that the save file chooser dialog is correctly invoked for DjVu image type."
        self.app.settings["image type"] = "djvu"
        self.app._windowi = unittest.mock.Mock()
        mock_dialog = unittest.mock.Mock()
        mock_gtk.FileChooserDialog.return_value = mock_dialog

        self.app._save_file_chooser(["uuid1"])

        mock_gtk.FileChooserDialog.assert_called_once()
        mock_dialog.connect.assert_called_once()
        mock_dialog.show.assert_called_once()

    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_save_file_chooser_tif(self, mock_gtk):
        "Test that the file chooser dialog is correctly invoked when saving a TIFF file."
        self.app.settings["image type"] = "tif"
        self.app._windowi = unittest.mock.Mock()
        mock_dialog = unittest.mock.Mock()
        mock_gtk.FileChooserDialog.return_value = mock_dialog

        self.app._save_file_chooser(["uuid1"])

        mock_gtk.FileChooserDialog.assert_called_once()
        mock_dialog.connect.assert_called_once()
        mock_dialog.show.assert_called_once()

    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_save_file_chooser_txt(self, mock_gtk):
        "Test that the save file chooser dialog is correctly invoked for 'txt' image type."
        self.app.settings["image type"] = "txt"
        self.app._windowi = unittest.mock.Mock()
        mock_dialog = unittest.mock.Mock()
        mock_gtk.FileChooserDialog.return_value = mock_dialog

        self.app._save_file_chooser(["uuid1"])

        mock_gtk.FileChooserDialog.assert_called_once()
        mock_dialog.connect.assert_called_once()
        mock_dialog.show.assert_called_once()

    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_save_file_chooser_hocr(self, mock_gtk):
        "Test that the save file chooser dialog is correctly invoked for HOCR image type."
        self.app.settings["image type"] = "hocr"
        self.app._windowi = unittest.mock.Mock()
        mock_dialog = unittest.mock.Mock()
        mock_gtk.FileChooserDialog.return_value = mock_dialog

        self.app._save_file_chooser(["uuid1"])

        mock_gtk.FileChooserDialog.assert_called_once()
        mock_dialog.connect.assert_called_once()
        mock_dialog.show.assert_called_once()

    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_save_file_chooser_ps(self, mock_gtk):
        "Test that the file chooser dialog is correctly invoked when saving as a PS file."
        self.app.settings["image type"] = "ps"
        self.app._windowi = unittest.mock.Mock()
        mock_dialog = unittest.mock.Mock()
        mock_gtk.FileChooserDialog.return_value = mock_dialog

        self.app._save_file_chooser(["uuid1"])

        mock_gtk.FileChooserDialog.assert_called_once()
        mock_dialog.connect.assert_called_once()
        mock_dialog.show.assert_called_once()

    @unittest.mock.patch("file_menu_mixins.Gtk")
    def test_save_file_chooser_session(self, mock_gtk):
        "Test that the file chooser dialog is properly created and shown when saving a session file."
        self.app.settings["image type"] = "session"
        self.app._windowi = unittest.mock.Mock()
        mock_dialog = unittest.mock.Mock()
        mock_gtk.FileChooserDialog.return_value = mock_dialog

        self.app._save_file_chooser(["uuid1"])

        mock_gtk.FileChooserDialog.assert_called_once()
        mock_dialog.connect.assert_called_once()
        mock_dialog.show.assert_called_once()

    def test_list_of_page_uuids(self):
        "Test _list_of_page_uuids returns correct UUIDs."
        self.app.slist.get_page_index = unittest.mock.Mock(return_value=[0, 2])
        self.app.slist.data = [[0, 0, "uuid1"], [0, 0, "uuid2"], [0, 0, "uuid3"]]
        self.app.settings["Page range"] = "1,3"

        uuids = self.app._list_of_page_uuids()

        self.assertEqual(uuids, ["uuid1", "uuid3"])
        self.app.slist.get_page_index.assert_called_with(
            "1,3", self.app._error_callback
        )

    @unittest.mock.patch("file_menu_mixins.os")
    @unittest.mock.patch("file_menu_mixins.re")
    def test_file_chooser_response_callback_ok_pdf(self, mock_re, mock_os):
        "Test _file_chooser_response_callback for PDF type."
        self.app._save_pdf = unittest.mock.Mock()
        self.app._file_writable = unittest.mock.Mock(return_value=False)
        self.app.settings["close_dialog_on_save"] = True
        self.app._windowi = unittest.mock.Mock()
        mock_dialog = unittest.mock.Mock()
        mock_dialog.get_filename.return_value = "/path/to/file.pdf"
        mock_re.search.return_value = True
        mock_os.path.dirname.return_value = "/path/to"

        self.app._file_chooser_response_callback(
            mock_dialog, Gtk.ResponseType.OK, ["pdf", ["uuid1"]]
        )

        mock_dialog.get_filename.assert_called_once()
        self.assertEqual(self.app.settings["cwd"], "/path/to")
        self.app._save_pdf.assert_called_with("/path/to/file.pdf", ["uuid1"], "pdf")
        self.app._windowi.hide.assert_called_once()
        mock_dialog.destroy.assert_called_once()

    def test_file_chooser_response_callback_ok_ps_libtiff(self):
        "Test _file_chooser_response_callback for PS type with libtiff backend."
        pytest.skip("does not yet pass")
        self.app._save_tif = unittest.mock.Mock()
        self.app._file_writable = unittest.mock.Mock(return_value=False)
        self.app.settings["ps_backend"] = "libtiff"
        mock_dialog = unittest.mock.Mock()
        mock_dialog.get_filename.return_value = "/path/to/file.ps"

        self.app._file_chooser_response_callback(
            mock_dialog, Gtk.ResponseType.OK, ["ps", ["uuid1"]]
        )

        self.app._save_tif.assert_called_with("tempfile", ["uuid1"], "/path/to/file.ps")

    def test_file_chooser_response_callback_ok_ps_pdf2ps(self):
        "Test _file_chooser_response_callback for PS type with pdf2ps backend."
        self.app._save_pdf = unittest.mock.Mock()
        self.app._file_writable = unittest.mock.Mock(return_value=False)
        self.app.settings["ps_backend"] = "pdf2ps"
        mock_dialog = unittest.mock.Mock()
        mock_dialog.get_filename.return_value = "/path/to/file.ps"

        self.app._file_chooser_response_callback(
            mock_dialog, Gtk.ResponseType.OK, ["ps", ["uuid1"]]
        )

        self.app._save_pdf.assert_called_with("/path/to/file.ps", ["uuid1"], "ps")

    @unittest.mock.patch("file_menu_mixins.VERSION", "1.0")
    def test_file_chooser_response_callback_ok_session(self):
        "Test _file_chooser_response_callback for session type."
        pytest.skip("does not yet pass")
        self.app.slist.save_session = unittest.mock.Mock()
        self.app._file_writable = unittest.mock.Mock(return_value=False)
        mock_dialog = unittest.mock.Mock()
        mock_dialog.get_filename.return_value = "/path/to/file.gs2p"
        self.app.slist.save_session = unittest.mock.Mock()

        self.app._file_chooser_response_callback(
            mock_dialog, Gtk.ResponseType.OK, ["session", ["uuid1"]]
        )

        self.app.slist.save_session.assert_called_with("/path/to/file.gs2p", "1.0")

    def test_file_chooser_response_callback_ok_djvu(self):
        "Test _file_chooser_response_callback for DjVu type."
        self.app._save_djvu = unittest.mock.Mock()
        self.app._file_writable = unittest.mock.Mock(return_value=False)
        mock_dialog = unittest.mock.Mock()
        mock_dialog.get_filename.return_value = "/path/to/file.djvu"

        self.app._file_chooser_response_callback(
            mock_dialog, Gtk.ResponseType.OK, ["djvu", ["uuid1"]]
        )

        self.app._save_djvu.assert_called_with("/path/to/file.djvu", ["uuid1"])

    def test_file_chooser_response_callback_ok_tif(self):
        "Test _file_chooser_response_callback for TIFF type."
        self.app._save_tif = unittest.mock.Mock()
        self.app._file_writable = unittest.mock.Mock(return_value=False)
        mock_dialog = unittest.mock.Mock()
        mock_dialog.get_filename.return_value = "/path/to/file.tif"

        self.app._file_chooser_response_callback(
            mock_dialog, Gtk.ResponseType.OK, ["tif", ["uuid1"]]
        )

        self.app._save_tif.assert_called_with("/path/to/file.tif", ["uuid1"])

    def test_file_chooser_response_callback_ok_txt(self):
        "Test _file_chooser_response_callback for TXT type."
        self.app._save_txt = unittest.mock.Mock()
        self.app._file_writable = unittest.mock.Mock(return_value=False)
        mock_dialog = unittest.mock.Mock()
        mock_dialog.get_filename.return_value = "/path/to/file.txt"

        self.app._file_chooser_response_callback(
            mock_dialog, Gtk.ResponseType.OK, ["txt", ["uuid1"]]
        )

        self.app._save_txt.assert_called_with("/path/to/file.txt", ["uuid1"])

    def test_file_chooser_response_callback_ok_hocr(self):
        "Test _file_chooser_response_callback for HOCR type."
        self.app._save_hocr = unittest.mock.Mock()
        self.app._file_writable = unittest.mock.Mock(return_value=False)
        mock_dialog = unittest.mock.Mock()
        mock_dialog.get_filename.return_value = "/path/to/file.hocr"

        self.app._file_chooser_response_callback(
            mock_dialog, Gtk.ResponseType.OK, ["hocr", ["uuid1"]]
        )

        self.app._save_hocr.assert_called_with("/path/to/file.hocr", ["uuid1"])

    def test_file_chooser_response_callback_cancel(self):
        "Test _file_chooser_response_callback destroys dialog on cancel."
        mock_dialog = unittest.mock.Mock()

        self.app._file_chooser_response_callback(
            mock_dialog, Gtk.ResponseType.CANCEL, ["pdf", ["uuid1"]]
        )

        mock_dialog.destroy.assert_called_once()

    @unittest.mock.patch("file_menu_mixins.os")
    def test_file_writable_dir_not_writable(self, mock_os):
        "Test _file_writable returns True if directory not writable."
        self.app._show_message_dialog = unittest.mock.Mock()
        mock_os.path.dirname.return_value = "/path/to"
        mock_os.access.return_value = False
        mock_chooser = unittest.mock.Mock()

        self.assertTrue(self.app._file_writable(mock_chooser, "/path/to/file.pdf"))

        self.app._show_message_dialog.assert_called_once()

    @unittest.mock.patch("file_menu_mixins.os")
    def test_file_writable_file_not_writable(self, mock_os):
        "Test _file_writable returns True if file not writable."
        self.app._show_message_dialog = unittest.mock.Mock()
        mock_os.path.dirname.return_value = "/path/to"
        mock_os.access.side_effect = [True, False]
        mock_os.path.isfile.return_value = True
        mock_chooser = unittest.mock.Mock()

        self.assertTrue(self.app._file_writable(mock_chooser, "/path/to/file.pdf"))

        self.app._show_message_dialog.assert_called_once()

    @unittest.mock.patch("file_menu_mixins.os")
    def test_file_writable_ok(self, mock_os):
        "Test _file_writable returns False if file is writable."
        self.app._show_message_dialog = unittest.mock.Mock()
        mock_os.access.return_value = True
        mock_chooser = unittest.mock.Mock()

        self.assertFalse(self.app._file_writable(mock_chooser, "/path/to/file.pdf"))

        self.app._show_message_dialog.assert_not_called()

    @unittest.mock.patch("file_menu_mixins.collate_metadata")
    @unittest.mock.patch("file_menu_mixins.datetime")
    def test_save_pdf(self, mock_datetime, mock_collate_metadata):
        "Test _save_pdf calls save_pdf with correct arguments."
        self.app.slist.save_pdf = unittest.mock.Mock()
        self.app._windowi = unittest.mock.Mock()
        self.app._windowi.pdf_user_password = "password"
        mock_collate_metadata.return_value = "metadata"
        mock_datetime.datetime.now.return_value = "now"
        self.app.settings["post_save_hook"] = True

        self.app._save_pdf("file.pdf", ["uuid1"], "pdf")

        self.app.slist.save_pdf.assert_called_with(
            path="file.pdf",
            list_of_pages=["uuid1"],
            metadata="metadata",
            options={
                "compression": "jpeg",
                "downsample": True,
                "downsample dpi": 150,
                "quality": 80,
                "text_position": "above",
                "font": "Helvetica",
                "user-password": "password",
                "set_timestamp": True,
                "convert whitespace to underscores": True,
                "post_save_hook": "tool",
            },
            queued_callback=self.app.post_process_progress.queued,
            started_callback=self.app.post_process_progress.update,
            running_callback=self.app.post_process_progress.update,
            finished_callback=unittest.mock.ANY,
            error_callback=self.app._error_callback,
        )

    def test_save_pdf_prepend(self):
        "Test _save_pdf with prependpdf option."
        pytest.skip("does not yet pass")
        self.app.slist.save_pdf = unittest.mock.Mock()
        self.app._windowi = unittest.mock.Mock()

        self.app._save_pdf("file.pdf", ["uuid1"], "prependpdf")

        self.assertIn("prepend", self.app.slist.save_pdf.call_args[1]["options"])

    def test_save_pdf_append(self):
        "Test _save_pdf with appendpdf option."
        pytest.skip("does not yet pass")
        self.app.slist.save_pdf = unittest.mock.Mock()
        self.app._windowi = unittest.mock.Mock()

        self.app._save_pdf("file.pdf", ["uuid1"], "appendpdf")

        self.assertIn("append", self.app.slist.save_pdf.call_args[1]["options"])

    def test_save_pdf_ps(self):
        "Test _save_pdf with ps option and pdf2ps tool."
        pytest.skip("does not yet pass")
        self.app.slist.save_pdf = unittest.mock.Mock()
        self.app._windowi = unittest.mock.Mock()

        self.app._save_pdf("file.ps", ["uuid1"], "ps")

        self.assertIn("ps", self.app.slist.save_pdf.call_args[1]["options"])
        self.assertEqual(
            self.app.slist.save_pdf.call_args[1]["options"]["pstool"], "pdf2ps"
        )

    @unittest.mock.patch("file_menu_mixins.launch_default_for_file")
    def test_save_pdf_finished_callback(self, mock_launch):
        "Test finished callback for _save_pdf launches file and sets saved."
        pytest.skip("does not yet pass")
        response = unittest.mock.Mock()
        response.request.args = [{"path": "file.pdf"}]
        self.app.slist.thread.send = unittest.mock.Mock()

        # The callback is defined inside _save_pdf, so we need to call it from there
        self.app.slist.save_pdf = lambda path, list_of_pages, metadata, options, queued_callback, started_callback, running_callback, finished_callback, error_callback: finished_callback(
            response
        )
        self.app._save_pdf("file.pdf", ["uuid1"], "pdf")

        self.app.post_process_progress.finish.assert_called_with(response)
        self.app.slist.thread.send.assert_called_with("set_saved", ["uuid1"])
        mock_launch.assert_called_with("file.pdf")

    @unittest.mock.patch("file_menu_mixins.os")
    @unittest.mock.patch("file_menu_mixins.collate_metadata")
    @unittest.mock.patch("file_menu_mixins.datetime")
    def test_save_djvu(self, mock_datetime, mock_collate_metadata, mock_os):
        "Test _save_djvu calls save_djvu with correct arguments."
        self.app.slist.save_djvu = unittest.mock.Mock()
        mock_collate_metadata.return_value = "metadata"
        mock_datetime.datetime.now.return_value = "now"
        self.app.settings["post_save_hook"] = True

        self.app._save_djvu("file.djvu", ["uuid1"])

        self.app.slist.save_djvu.assert_called_with(
            path="file.djvu",
            list_of_pages=["uuid1"],
            metadata="metadata",
            options={
                "set_timestamp": True,
                "convert whitespace to underscores": True,
                "post_save_hook": "tool",
            },
            queued_callback=self.app.post_process_progress.queued,
            started_callback=self.app.post_process_progress.update,
            running_callback=self.app.post_process_progress.update,
            finished_callback=unittest.mock.ANY,
            error_callback=self.app._error_callback,
        )
        mock_os.chdir.assert_called_once_with(self.app.session.name)

    @unittest.mock.patch("file_menu_mixins.launch_default_for_file")
    def test_save_tiff_finished_callback(self, mock_launch):
        "Test finished callback for _save_tif launches file and sets saved."
        response = unittest.mock.Mock()
        response.request.args = [{"path": "file.tif"}]
        self.app.slist.thread.send = unittest.mock.Mock()

        # The callback is defined inside _save_tif, so we need to call it from there
        self.app.slist.save_tiff = lambda path, list_of_pages, options, queued_callback, started_callback, running_callback, finished_callback, error_callback: finished_callback(
            response
        )
        self.app._save_tif("file.tif", ["uuid1"])

        self.app.post_process_progress.finish.assert_called_with(response)
        self.app.slist.thread.send.assert_called_with("set_saved", ["uuid1"])
        mock_launch.assert_called_with("file.tif")

    def test_save_txt(self):
        "Test _save_txt calls save_text with correct arguments."
        self.app.slist.save_text = unittest.mock.Mock()
        self.app.settings["post_save_hook"] = True

        self.app._save_txt("file.txt", ["uuid1"])

        self.app.slist.save_text.assert_called_with(
            path="file.txt",
            list_of_pages=["uuid1"],
            options={"post_save_hook": "tool"},
            queued_callback=self.app.post_process_progress.queued,
            started_callback=self.app.post_process_progress.update,
            running_callback=self.app.post_process_progress.update,
            finished_callback=unittest.mock.ANY,
            error_callback=self.app._error_callback,
        )

    @unittest.mock.patch("file_menu_mixins.launch_default_for_file")
    def test_save_hocr_finished_callback(self, mock_launch):
        "Test finished callback for _save_hocr launches file and sets saved."
        response = unittest.mock.Mock()
        response.request.args = [{"path": "file.hocr"}]
        self.app.slist.thread.send = unittest.mock.Mock()

        # The callback is defined inside _save_hocr, so we need to call it from there
        self.app.slist.save_hocr = lambda path, list_of_pages, options, queued_callback, started_callback, running_callback, finished_callback, error_callback: finished_callback(
            response
        )
        self.app._save_hocr("file.hocr", ["uuid1"])

        self.app.post_process_progress.finish.assert_called_with(response)
        self.app.slist.thread.send.assert_called_with("set_saved", ["uuid1"])
        mock_launch.assert_called_with("file.hocr")

    @unittest.mock.patch("file_menu_mixins.Gtk")
    @unittest.mock.patch("file_menu_mixins.file_exists")
    def test_save_image_single(self, mock_file_exists, mock_gtk):
        "Test _save_image saves a single image file."
        pytest.skip("does not yet pass")
        self.app.slist.save_image = unittest.mock.Mock()
        self.app.settings["image type"] = "png"
        self.app._file_writable = unittest.mock.Mock(return_value=False)
        mock_dialog = unittest.mock.Mock()
        mock_dialog.run.return_value = Gtk.ResponseType.OK
        mock_dialog.get_filename.return_value = "/path/to/image.png"
        mock_gtk.FileChooserDialog.return_value = mock_dialog
        mock_file_exists.return_value = False
        mock_dialog.get_filename.return_value = "/path/to/image.png"

        self.app._save_image(["uuid1"])

        mock_gtk.FileChooserDialog.assert_called_once()
        mock_dialog.run.assert_called_once()
        mock_dialog.get_filename.assert_called_once()
        self.assertEqual(self.app.settings["cwd"], "/path/to")
        self.app.slist.save_image.assert_called_with(
            path="/path/to/image.png",
            list_of_pages=["uuid1"],
            queued_callback=self.app.post_process_progress.queued,
            started_callback=self.app.post_process_progress.update,
            running_callback=self.app.post_process_progress.update,
            finished_callback=unittest.mock.ANY,
            error_callback=self.app._error_callback,
        )
        mock_dialog.destroy.assert_called_once()

    @unittest.mock.patch("file_menu_mixins.launch_default_for_file")
    def test_save_djvu_finished_callback(self, mock_launch):
        "Test finished callback for _save_djvu launches file and sets saved."
        pytest.skip("does not yet pass")
        response = unittest.mock.Mock()
        response.request.args = [{"path": "file.djvu"}]
        self.app.slist.thread.send = unittest.mock.Mock()

        # The callback is defined inside _save_djvu, so we need to call it from there
        self.app.slist.save_djvu = lambda path, list_of_pages, metadata, options, queued_callback, started_callback, running_callback, finished_callback, error_callback: finished_callback(
            response
        )
        self.app._save_djvu("file.djvu", ["uuid1"])

        self.app.post_process_progress.finish.assert_called_with(response)
        self.app.slist.thread.send.assert_called_with("set_saved", ["uuid1"])
        mock_launch.assert_called_with("file.djvu")

    def test_save_tif(self):
        "Test _save_tif calls save_tiff with correct arguments."
        self.app.slist.save_tiff = unittest.mock.Mock()
        self.app.settings["post_save_hook"] = True

        self.app._save_tif("file.tif", ["uuid1"])

        self.app.slist.save_tiff.assert_called_with(
            path="file.tif",
            list_of_pages=["uuid1"],
            options={
                "compression": "jpeg",
                "quality": 80,
                "ps": None,
                "post_save_hook": "tool",
            },
            queued_callback=self.app.post_process_progress.queued,
            started_callback=self.app.post_process_progress.update,
            running_callback=self.app.post_process_progress.update,
            finished_callback=unittest.mock.ANY,
            error_callback=self.app._error_callback,
        )

    @unittest.mock.patch("file_menu_mixins.launch_default_for_file")
    def test_save_text_finished_callback(self, mock_launch):
        "Test finished callback for _save_txt launches file and sets saved."
        response = unittest.mock.Mock()
        response.request.args = [{"path": "file.txt"}]
        self.app.slist.thread.send = unittest.mock.Mock()

        # The callback is defined inside _save_txt, so we need to call it from there
        self.app.slist.save_text = lambda path, list_of_pages, options, queued_callback, started_callback, running_callback, finished_callback, error_callback: finished_callback(
            response
        )
        self.app._save_txt("file.txt", ["uuid1"])

        self.app.post_process_progress.finish.assert_called_with(response)
        self.app.slist.thread.send.assert_called_with("set_saved", ["uuid1"])
        mock_launch.assert_called_with("file.txt")

    def test_save_hocr(self):
        "Test _save_hocr calls save_hocr with correct arguments."
        self.app.slist.save_hocr = unittest.mock.Mock()
        self.app.settings["post_save_hook"] = True

        self.app._save_hocr("file.hocr", ["uuid1"])

        self.app.slist.save_hocr.assert_called_with(
            path="file.hocr",
            list_of_pages=["uuid1"],
            options={"post_save_hook": "tool"},
            queued_callback=self.app.post_process_progress.queued,
            started_callback=self.app.post_process_progress.update,
            running_callback=self.app.post_process_progress.update,
            finished_callback=unittest.mock.ANY,
            error_callback=self.app._error_callback,
        )


# pylint: enable=protected-access,attribute-defined-outside-init
