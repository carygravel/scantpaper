"Test tool_menu_mixins.py"

from tools_menu_mixins import ToolsMenuMixins
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


def test_about_dialog_runs(mocker):
    "Test that ToolsMenuMixins.about runs without error"

    # Mock the Gtk.AboutDialog to avoid GUI interaction
    mock_about_dialog = mocker.patch("gi.repository.Gtk.AboutDialog")

    # Mock GdkPixbuf.Pixbuf.new_from_file to prevent file loading errors
    mocker.patch("gi.repository.GdkPixbuf.Pixbuf.new_from_file")

    # The 'about' method needs a 'self' that is a Gtk.Window
    # and has a get_application().iconpath
    mock_app = mocker.Mock()
    mock_app.iconpath = "."

    class MockWindow(Gtk.Window, ToolsMenuMixins):
        "Test class to hold mixin"

        def get_application(self, *args, **kwargs):  # pylint: disable=arguments-differ
            "mock"
            return mock_app

    container = MockWindow()

    # Call the method from the mixin on our container instance
    container.about(None, None)

    # Check that the dialog was created and shown
    mock_about_dialog.assert_called_once()
    instance = mock_about_dialog.return_value
    instance.run.assert_called_once()
    instance.destroy.assert_called_once()

    # Check a few key properties were set
    instance.set_program_name.assert_called()
    instance.set_version.assert_called()
    instance.set_website.assert_called()
    instance.set_logo.assert_called()

    container.destroy()


def test_split_dialog(mocker):
    "Test the split dialog"

    # The 'split_dialog' method needs a 'self' that is a Gtk.Window
    mock_app = mocker.Mock()

    class MockWindow(Gtk.Window, ToolsMenuMixins):
        "Test class to hold mixin"

        _current_page = None
        view = None
        slist = None
        settings = {}
        _error_callback = None
        post_process_progress = None
        _display_callback = None

        def get_application(self, *args, **kwargs):  # pylint: disable=arguments-differ
            "mock"
            return mock_app

    mock_window = MockWindow()
    mock_page = mocker.patch.object(mock_window, "_current_page")
    mocker.patch.object(mock_page, "get_size", return_value=(100, 50))
    mocker.patch.object(mock_window, "view")
    mock_slist = mocker.patch.object(mock_window, "slist")
    mock_slist.get_page_index.return_value = [0]
    mocker.patch.object(mock_window, "post_process_progress")
    mocker.patch.object(mock_window, "_display_callback")

    # Call the method from the mixin on our container instance
    mock_window.split_dialog(None, None)

    split_dialog = mock_window._windowsp
    assert split_dialog is not None, "split_dialog"

    # apply
    split_dialog.response(Gtk.ResponseType.OK)
    mock_slist.split_page.assert_called_once()

    mock_window.destroy()
