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

    mock_dialog_cls = mocker.patch("tools_menu_mixins.Dialog")
    mock_dialog_instance = mock_dialog_cls.return_value
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

    # We expect Dialog to be instantiated
    mock_dialog_cls.assert_called()

    # We expect add_actions to be called. We need to retrieve the apply callback
    # passed to add_actions to simulate clicking 'OK'.
    # add_actions is called with a list of tuples: [("gtk-apply", cb), ("gtk-cancel", cb)]
    args, _kwargs = mock_dialog_instance.add_actions.call_args
    actions = args[0]
    apply_callback = None
    for action_name, callback in actions:
        if action_name == "gtk-apply":
            apply_callback = callback
            break

    assert apply_callback is not None, "Could not find gtk-apply callback"

    # Simulate clicking apply
    apply_callback()
    mock_slist.split_page.assert_called_once()

    mock_window.destroy()


def test_threshold_dialog(mocker):
    "Test the threshold dialog"

    mock_dialog_cls = mocker.patch("tools_menu_mixins.Dialog")
    mock_dialog_instance = mock_dialog_cls.return_value
    # mock get_content_area
    mock_vbox = mocker.Mock()
    mock_dialog_instance.get_content_area.return_value = mock_vbox

    # The 'threshold' method needs a 'self' that is a Gtk.Window
    mock_app = mocker.Mock()

    class MockWindow(Gtk.Window, ToolsMenuMixins):
        "Test class to hold mixin"

        slist = None
        settings = {"threshold tool": 50}
        _error_callback = None
        post_process_progress = None
        _display_callback = None

        def get_application(self, *args, **kwargs):  # pylint: disable=arguments-differ
            "mock"
            return mock_app

    mock_window = MockWindow()
    mock_slist = mocker.patch.object(mock_window, "slist")
    mock_slist.get_page_index.return_value = [0]
    mock_slist.data = [[0, 0, "uuid"]]
    mocker.patch.object(mock_window, "post_process_progress")
    mocker.patch.object(mock_window, "_display_callback")

    # Call the method from the mixin on our container instance
    mock_window.threshold(None, None)

    # We expect Dialog to be instantiated
    mock_dialog_cls.assert_called()

    # We expect add_actions to be called. We need to retrieve the apply callback
    # passed to add_actions to simulate clicking 'OK'.
    # add_actions is called with a list of tuples: [("gtk-apply", cb), ("gtk-cancel", cb)]
    args, _kwargs = mock_dialog_instance.add_actions.call_args
    actions = args[0]
    apply_callback = None
    for action_name, callback in actions:
        if action_name == "gtk-apply":
            apply_callback = callback
            break

    assert apply_callback is not None, "Could not find gtk-apply callback"

    # Simulate clicking apply
    apply_callback()

    # Verify that slist.threshold was called
    mock_slist.threshold.assert_called_once()
    call_kwargs = mock_slist.threshold.call_args[1]
    assert call_kwargs["threshold"] == 50
    assert call_kwargs["page"] == "uuid"

    mock_window.destroy()


def test_brightness_contrast_dialog(mocker):
    "Test the brightness_contrast dialog"

    mock_dialog_cls = mocker.patch("tools_menu_mixins.Dialog")
    mock_dialog_instance = mock_dialog_cls.return_value
    # mock get_content_area
    mock_vbox = mocker.Mock()
    mock_dialog_instance.get_content_area.return_value = mock_vbox

    # The 'brightness_contrast' method needs a 'self' that is a Gtk.Window
    mock_app = mocker.Mock()

    class MockWindow(Gtk.Window, ToolsMenuMixins):
        "Test class to hold mixin"

        slist = None
        settings = {"brightness tool": 20, "contrast tool": 30}
        _error_callback = None
        post_process_progress = None
        _display_callback = None

        def get_application(self, *args, **kwargs):  # pylint: disable=arguments-differ
            "mock"
            return mock_app

    mock_window = MockWindow()
    mock_slist = mocker.patch.object(mock_window, "slist")
    mock_slist.get_page_index.return_value = [0]
    mock_slist.data = [[0, 0, "uuid"]]
    mocker.patch.object(mock_window, "post_process_progress")
    mocker.patch.object(mock_window, "_display_callback")

    # Call the method from the mixin on our container instance
    mock_window.brightness_contrast(None, None)

    # We expect Dialog to be instantiated
    mock_dialog_cls.assert_called()

    # We expect add_actions to be called. We need to retrieve the apply callback
    # passed to add_actions to simulate clicking 'OK'.
    args, _kwargs = mock_dialog_instance.add_actions.call_args
    actions = args[0]
    apply_callback = None
    for action_name, callback in actions:
        if action_name == "gtk-apply":
            apply_callback = callback
            break

    assert apply_callback is not None, "Could not find gtk-apply callback"

    # Simulate clicking apply
    apply_callback()

    # Verify that slist.brightness_contrast was called
    mock_slist.brightness_contrast.assert_called_once()
    call_kwargs = mock_slist.brightness_contrast.call_args[1]
    assert call_kwargs["brightness"] == 20
    assert call_kwargs["contrast"] == 30
    assert call_kwargs["page"] == "uuid"

    mock_window.destroy()


def test_negate_dialog(mocker):
    "Test the negate dialog"

    mock_dialog_cls = mocker.patch("tools_menu_mixins.Dialog")
    mock_dialog_instance = mock_dialog_cls.return_value
    # mock get_content_area
    mock_vbox = mocker.Mock()
    mock_dialog_instance.get_content_area.return_value = mock_vbox

    # The 'negate' method needs a 'self' that is a Gtk.Window
    mock_app = mocker.Mock()

    class MockWindow(Gtk.Window, ToolsMenuMixins):
        "Test class to hold mixin"

        slist = None
        settings = {"Page range": "selected"}
        _error_callback = None
        post_process_progress = None
        _display_callback = None

        def get_application(self, *args, **kwargs):  # pylint: disable=arguments-differ
            "mock"
            return mock_app

    mock_window = MockWindow()
    mock_slist = mocker.patch.object(mock_window, "slist")
    mock_slist.get_page_index.return_value = [0]
    mock_slist.data = [[0, 0, "uuid"]]
    mocker.patch.object(mock_window, "post_process_progress")
    mocker.patch.object(mock_window, "_display_callback")

    # Call the method from the mixin on our container instance
    mock_window.negate(None, None)

    # We expect Dialog to be instantiated
    mock_dialog_cls.assert_called()

    # We expect add_actions to be called. We need to retrieve the apply callback
    # passed to add_actions to simulate clicking 'OK'.
    args, _kwargs = mock_dialog_instance.add_actions.call_args
    actions = args[0]
    apply_callback = None
    for action_name, callback in actions:
        if action_name == "gtk-apply":
            apply_callback = callback
            break

    assert apply_callback is not None, "Could not find gtk-apply callback"

    # Simulate clicking apply
    apply_callback()

    # Verify that slist.negate was called
    mock_slist.negate.assert_called_once()
    call_kwargs = mock_slist.negate.call_args[1]
    assert call_kwargs["page"] == "uuid"

    mock_window.destroy()
