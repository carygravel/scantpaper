"Tests for ApplicationWindow"

import uuid
from unittest.mock import MagicMock, patch
import pytest
from app_window import ApplicationWindow, drag_motion_callback, view_html
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import (  # pylint: disable=wrong-import-position
    Gtk,
    Gdk,
    Gio,
    GLib,
    GObject,
)


class MockImageView(Gtk.DrawingArea):
    "Mock ImageView class"

    __gsignals__ = {
        "zoom-changed": (GObject.SignalFlags.RUN_LAST, None, (float,)),
        "offset-changed": (GObject.SignalFlags.RUN_LAST, None, (int, int)),
        "selection-changed": (GObject.SignalFlags.RUN_LAST, None, (object,)),
    }

    def set_tool(self, tool):
        "mock set_tool"

    def set_pixbuf(self, pixbuf, *args):
        "mock set_pixbuf"

    def set_resolution_ratio(self, ratio):
        "mock set_resolution_ratio"

    def set_selection(self, selection):
        "mock set_selection"

    def get_selection(self):
        "mock get_selection"
        return None

    def copy(self):
        "mock copy"
        return MagicMock()


class MockCanvas(Gtk.DrawingArea):
    "Mock Canvas class"

    __gsignals__ = {
        "zoom-changed": (GObject.SignalFlags.RUN_LAST, None, (float,)),
        "offset-changed": (GObject.SignalFlags.RUN_LAST, None, (int, int)),
    }

    def clear_text(self):
        "mock clear_text"

    def sort_by_confidence(self):
        "mock sort_by_confidence"

    def sort_by_position(self):
        "mock sort_by_position"


@pytest.fixture
def mock_builder(mocker):
    "Mock Gtk.Builder"
    builder_cls = mocker.patch("app_window.Gtk.Builder")
    builder = builder_cls.return_value
    # Return a MagicMock for any object requested
    builder.get_object.side_effect = lambda x: MagicMock(name=x)
    return builder


@pytest.fixture
def mock_config(mocker):
    "Mock config module"
    config = mocker.patch("app_window.config")
    config.read_config.return_value = {
        "restore window": False,
        "window_width": 100,
        "window_height": 100,
        "window_x": 0,
        "window_y": 0,
        "window_maximize": False,
        "cwd": "/tmp",
        "image_control_tool": "selector",
        "auto-open-scan-dialog": False,
        "unpaper options": {},
        "Paper": {},
        "thumb panel": 100,
        "viewer_tools": "tabbed",
        "available-tmp-warning": 100,
        "message_window_width": 200,
        "message_window_height": 200,
        "message": {},
        "cache-device-list": False,
        "selection": None,
    }
    return config


@pytest.fixture
def app_window(mocker, mock_builder, mock_config):
    "Fixture to create an ApplicationWindow instance with mocked dependencies"
    mocker.patch("app_window.Document")
    mocker.patch("app_window.Unpaper")

    mocker.patch("app_window.ImageView", MockImageView)
    mocker.patch("app_window.Canvas", MockCanvas)

    mocker.patch("app_window.Progress")
    mocker.patch("app_window.sane.init")
    mocker.patch("app_window.recursive_slurp")
    mocker.patch("app_window.Selector")
    mocker.patch("app_window.Dragger")
    mocker.patch("app_window.SelectorDragger")
    mocker.patch("app_window.Gtk.HPaned.pack1")
    mocker.patch("app_window.Gtk.HPaned.pack2")
    mocker.patch("app_window.Gtk.VPaned.pack1")
    mocker.patch("app_window.Gtk.VPaned.pack2")
    mocker.patch("app_window.Gtk.Notebook.append_page")
    mocker.patch("app_window.Gtk.Container.remove")

    # Mock shutil to avoid disk usage check failures
    mock_shutil = mocker.patch("app_window.shutil")
    mock_shutil.disk_usage.return_value.free = 1000 * 1024 * 1024  # 1000 MB

    mocker.patch.object(ApplicationWindow, "_show_message_dialog")

    def mock_create_temp_func(self):
        self.session = MagicMock()
        self.session.name = "/tmp/session"
        self._lockfd = MagicMock()
        self._dependencies = {
            "imagemagick": True,
            "libtiff": True,
            "djvu": True,
            "xdg": True,
            "unpaper": True,
            "tesseract": True,
            "pdftk": True,
            "ocr": True,
        }

    mocker.patch.object(ApplicationWindow, "_check_dependencies", autospec=True)
    mocker.patch.object(
        ApplicationWindow,
        "_create_temp_directory",
        side_effect=mock_create_temp_func,
        autospec=True,
    )
    mocker.patch.object(ApplicationWindow, "set_icon_from_file", autospec=True)
    mocker.patch.object(ApplicationWindow, "add", autospec=True)
    mocker.patch.object(ApplicationWindow, "show_all", autospec=True)

    app_id = f"org.test.panes.u{uuid.uuid4().hex}"
    app = Gtk.Application(application_id=app_id, flags=Gio.ApplicationFlags.FLAGS_NONE)
    app.iconpath = "/tmp"
    app.set_menubar = MagicMock()
    app.args = MagicMock()
    app.args.import_files = None
    app.args.import_all = None

    # We need to register the app to use it fully, though maybe not strictly required here
    with patch.object(Gtk.Application, "register", autospec=True):
        try:
            app.register(None)
        except GLib.Error:
            pass

        win = ApplicationWindow(application=app)
        yield win
        win.destroy()
        while Gtk.events_pending():
            Gtk.main_iteration()
        app.quit()


def test_init(app_window):
    "Test initialization"
    assert isinstance(app_window, ApplicationWindow)
    assert app_window.session.name == "/tmp/session"


def test_drag_motion_callback(mocker):
    "Test drag_motion_callback"
    mocker.patch("app_window.Gdk.drag_status")
    tree = MagicMock()
    context = MagicMock()

    # Mock get_dest_row_at_pos
    tree.get_dest_row_at_pos.return_value = (MagicMock(), MagicMock())

    # Mock context actions
    context.get_actions.return_value = Gdk.DragAction.MOVE

    # Mock scroll adjustment
    scroll = MagicMock()
    adj = MagicMock()
    scroll.get_vadjustment.return_value = adj
    adj.get_page_size.return_value = 100
    adj.get_step_increment.return_value = 10
    adj.get_value.return_value = 50
    adj.get_upper.return_value = 200
    adj.get_lower.return_value = 0
    tree.get_parent.return_value = scroll

    # Test with y in middle (no scroll)
    drag_motion_callback(tree, context, 0, 50, 0)
    adj.set_value.assert_not_called()

    # Test with y at bottom (scroll down)
    drag_motion_callback(tree, context, 0, 96, 0)
    adj.set_value.assert_called()

    # Test with y at top (scroll up)
    drag_motion_callback(tree, context, 0, 4, 0)
    adj.set_value.assert_called()


def test_view_html(mocker):
    "Test view_html"
    mocker.patch("pathlib.Path.exists", return_value=True)
    mock_launch = mocker.patch("gi.repository.Gio.AppInfo.launch_default_for_uri")

    view_html(None, None)
    mock_launch.assert_called()

    mocker.patch("pathlib.Path.exists", return_value=False)
    view_html(None, None)
    # Check that it launches the fallback URL
    args, _ = mock_launch.call_args
    assert "gscan2pdf.sf.net" in args[0]


def test_init_actions(app_window):
    "Test that actions are initialized"
    actions = app_window.list_actions()
    assert "scan" in actions
    assert "save" in actions
    assert "quit" in actions
    assert "tooltype" in actions

    # Check initial state
    assert app_window._actions["tooltype"].get_state().get_string() == "selector"


def test_change_image_tool_cb(app_window, mocker):
    "Test changing image tool"
    # Mock the view and builder object
    app_window.view = MagicMock()
    button = MagicMock()
    app_window.builder.get_object.return_value = button

    # Mock Dragger to return a known object
    dragger_cls = mocker.patch("app_window.Dragger")
    dragger_instance = dragger_cls.return_value

    action = app_window._actions["tooltype"]

    # Change to dragger
    variant = GLib.Variant("s", "dragger")
    app_window._change_image_tool_cb(action, variant)

    assert app_window.settings["image_control_tool"] == "dragger"
    app_window.view.set_tool.assert_called_with(dragger_instance)


def test_change_view_cb(app_window):
    "Test changing view type"
    action = app_window._actions["viewtype"]

    # Initial state
    assert app_window.settings["viewer_tools"] == "tabbed"

    # Change to horizontal
    variant = GLib.Variant("s", "horizontal")
    app_window._change_view_cb(action, variant)

    assert app_window.settings["viewer_tools"] == "horizontal"

    # Change to vertical
    variant = GLib.Variant("s", "vertical")
    app_window._change_view_cb(action, variant)

    assert app_window.settings["viewer_tools"] == "vertical"


def test_update_uimanager(app_window):
    "Test _update_uimanager"
    # Simulate no selection
    app_window.slist.get_selected_indices.return_value = []
    app_window.slist.data = []

    app_window._update_uimanager()

    assert not app_window._actions["save"].get_enabled()
    assert not app_window._actions["crop-dialog"].get_enabled()

    # Simulate selection and data
    app_window.slist.get_selected_indices.return_value = [0]
    app_window.slist.data = [MagicMock()]

    app_window._update_uimanager()

    assert app_window._actions["save"].get_enabled()
    assert app_window._actions["crop-dialog"].get_enabled()


def test_window_state_event_callback(app_window):
    "Test _window_state_event_callback"
    event = MagicMock()
    event.new_window_state = Gdk.WindowState.MAXIMIZED
    app_window._window_state_event_callback(None, event)
    assert app_window.settings["window_maximize"] is True

    event.new_window_state = Gdk.WindowState.FOCUSED
    app_window._window_state_event_callback(None, event)
    assert app_window.settings["window_maximize"] is False


def test_changed_text_sort_method(app_window):
    "Test _changed_text_sort_method"
    app_window.t_canvas = MagicMock()

    app_window._changed_text_sort_method(None, "confidence")
    app_window.t_canvas.sort_by_confidence.assert_called_once()

    app_window._changed_text_sort_method(None, "position")
    app_window.t_canvas.sort_by_position.assert_called_once()


def test_handle_clicks(app_window, mocker):
    "Test _handle_clicks"
    event = MagicMock()
    event.button = 3  # Right click

    # Use instance of MockImageView
    view_widget = MockImageView()
    app_window.detail_popup = MagicMock()
    assert app_window._handle_clicks(view_widget, event) is True
    app_window.detail_popup.show_all.assert_called_once()
    app_window.detail_popup.popup_at_pointer.assert_called_once_with(event)

    # Mock other widget (e.g. Thumbnail list)
    other_widget = MagicMock()
    app_window._thumb_popup = MagicMock()
    assert app_window._handle_clicks(other_widget, event) is True
    assert app_window.settings["Page range"] == "selected"
    app_window._thumb_popup.show_all.assert_called_once()
    app_window._thumb_popup.popup_at_pointer.assert_called_once_with(event)

    # Left click
    event.button = 1
    assert app_window._handle_clicks(view_widget, event) is False


def test_view_zoom_changed_callback(app_window):
    "Test _view_zoom_changed_callback"
    app_window.t_canvas = MagicMock()
    app_window.t_canvas.zoom_changed_signal = 123
    app_window._view_zoom_changed_callback(None, 2.0)
    app_window.t_canvas.handler_block.assert_called_once_with(123)
    app_window.t_canvas.set_scale.assert_called_once_with(2.0)
    app_window.t_canvas.handler_unblock.assert_called_once_with(123)


def test_view_offset_changed_callback(app_window):
    "Test _view_offset_changed_callback"
    app_window.t_canvas = MagicMock()
    app_window.t_canvas.offset_changed_signal = 456
    app_window._view_offset_changed_callback(None, 10, 20)
    app_window.t_canvas.handler_block.assert_called_once_with(456)
    app_window.t_canvas.set_offset.assert_called_once_with(10, 20)
    app_window.t_canvas.handler_unblock.assert_called_once_with(456)


def test_view_selection_changed_callback(app_window):
    "Test _view_selection_changed_callback"
    sel = MagicMock()
    copied_sel = MagicMock()
    sel.copy.return_value = copied_sel

    app_window._windowc = MagicMock()
    app_window._view_selection_changed_callback(None, sel)

    assert app_window.settings["selection"] == copied_sel
    assert app_window._windowc.selection == copied_sel


def test_on_key_press(app_window):
    "Test _on_key_press"
    app_window.delete_selection = MagicMock()

    # Delete key
    event = MagicMock()
    event.keyval = Gdk.KEY_Delete
    assert app_window._on_key_press(None, event) == Gdk.EVENT_STOP
    app_window.delete_selection.assert_called_once()

    # Other key
    event.keyval = Gdk.KEY_a
    assert app_window._on_key_press(None, event) == Gdk.EVENT_PROPAGATE


def test_process_error_callback(app_window, mocker):
    "Test _process_error_callback"
    app_window._scan_progress = MagicMock()
    app_window._show_message_dialog = MagicMock()

    # Basic error
    app_window._process_error_callback(None, "some_process", "some error", 123)
    app_window._scan_progress.disconnect.assert_called_once_with(123)
    app_window._scan_progress.hide.assert_called_once()
    app_window._show_message_dialog.assert_called_once()

    # open_device error - ignore
    app_window._show_message_dialog.reset_mock()
    app_window.settings["message"]["error opening device"] = {"response": "ignore"}
    app_window._process_error_callback(None, "open_device", "Device busy", None)
    app_window._show_message_dialog.assert_not_called()


def test_page_selection_changed_callback(app_window, mocker):
    "Test _page_selection_changed_callback"
    app_window.view = MagicMock()
    app_window.t_canvas = MagicMock()
    app_window.a_canvas = MagicMock()
    app_window.post_process_progress = MagicMock()
    app_window._display_image = MagicMock()
    app_window._update_uimanager = MagicMock()

    # No selection
    app_window.slist.get_selected_indices.return_value = []
    app_window._page_selection_changed_callback(None)
    app_window.view.set_pixbuf.assert_called_with(None)
    app_window.t_canvas.clear_text.assert_called_once()
    app_window.a_canvas.clear_text.assert_called_once()
    app_window.post_process_progress.finish.assert_called_once()

    app_window.post_process_progress.finish.reset_mock()

    # With selection
    app_window.slist.get_selected_indices.return_value = [0]
    app_window.slist.data = [[1, None, "page_id"]]
    app_window.slist.get_column.return_value = MagicMock()
    app_window.view.get_selection.return_value = None

    app_window._page_selection_changed_callback(None)
    app_window._display_image.assert_called_with("page_id")
    app_window._update_uimanager.assert_called()
    app_window.post_process_progress.finish.assert_called_once()


def test_pack_viewer_tools(app_window, mocker):
    "Test _pack_viewer_tools"
    app_window._vnotebook = MagicMock()
    app_window._hpanei = MagicMock()
    app_window._vpanei = MagicMock()
    app_window._vpaned = MagicMock()
    app_window.view = MagicMock()
    app_window.t_canvas = MagicMock()
    app_window.a_canvas = MagicMock()

    # Tabbed
    app_window.settings["viewer_tools"] = "tabbed"
    app_window._pack_viewer_tools()
    assert app_window._vnotebook.append_page.call_count == 3

    # Horizontal
    app_window.settings["viewer_tools"] = "horizontal"
    app_window._pack_viewer_tools()
    app_window._hpanei.pack1.assert_called_with(app_window.view, True, True)
    app_window._hpanei.pack2.assert_called_with(app_window.t_canvas, True, True)

    # Vertical
    app_window.settings["viewer_tools"] = "vertical"
    app_window._pack_viewer_tools()
    app_window._vpanei.pack1.assert_called_with(app_window.view, True, True)
    app_window._vpanei.pack2.assert_called_with(app_window.t_canvas, True, True)
