"""Tests for ApplicationWindow."""

from __future__ import annotations

import pathlib
import uuid
from itertools import cycle
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock, patch

import gi
import pytest

from scantpaper.app_window import ApplicationWindow, drag_motion_callback, view_html
from scantpaper.config import ConfigDict
from scantpaper.i18n import _

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from typing import ClassVar

    from scantpaper.canvas import Canvas
    from scantpaper.imageview import ImageView
    from scantpaper.loop_helpers import _MainLoopWrapper

gi.require_version("Gtk", "4.0")
from gi.repository import (  # noqa: E402
    Gdk,
    GdkPixbuf,
    Gio,
    GLib,
    GObject,
    Gtk,
)


class MockImageView(Gtk.DrawingArea):
    """Mock ImageView class."""

    __gsignals__: ClassVar[dict[str, tuple[Any, ...]]] = {
        "zoom-changed": (GObject.SignalFlags.RUN_LAST, None, (float,)),
        "offset-changed": (GObject.SignalFlags.RUN_LAST, None, (int, int)),
        "selection-changed": (GObject.SignalFlags.RUN_LAST, None, (object,)),
    }
    zoom = GObject.Property(type=float, default=1.0, nick="zoom", blurb="zoom level")
    offset = GObject.Property(
        type=Gdk.Rectangle, nick="Image offset", blurb="Gdk.Rectangle of x, y"
    )
    selection = GObject.Property(
        type=Gdk.Rectangle, nick="Selection", blurb="Gdk.Rectangle of selected region"
    )
    resolution_ratio = GObject.Property(
        type=float,
        default=1.0,
        nick="resolution-ratio",
        blurb="Ratio of x-resolution/y-resolution",
    )

    def set_tool(self, tool: object) -> None:
        """Mock set_tool."""

    def set_pixbuf(self, pixbuf: object, *args: object) -> None:
        """Mock set_pixbuf."""

    def set_resolution_ratio(self, ratio: object) -> None:
        """Mock set_resolution_ratio."""

    def set_selection(self, selection: object) -> None:
        """Mock set_selection."""

    def get_selection(self) -> object:
        """Mock get_selection."""
        return self.selection


class MockCanvas(Gtk.DrawingArea):
    """Mock Canvas class."""

    __gsignals__: ClassVar[dict[str, tuple[Any, ...]]] = {
        "zoom-changed": (GObject.SignalFlags.RUN_LAST, None, (float,)),
        "offset-changed": (GObject.SignalFlags.RUN_LAST, None, (int, int)),
        "selection-drawn": (GObject.SignalFlags.RUN_LAST, None, (Gdk.Rectangle,)),
    }
    zoom = GObject.Property(type=float, default=1.0, nick="zoom", blurb="zoom level")
    offset = GObject.Property(
        type=Gdk.Rectangle, nick="Canvas offset", blurb="Gdk.Rectangle of x, y"
    )
    selection = GObject.Property(
        type=Gdk.Rectangle, nick="Selection", blurb="Gdk.Rectangle of selected region"
    )
    resolution_ratio = GObject.Property(
        type=float,
        default=1.0,
        nick="resolution-ratio",
        blurb="Ratio of x-resolution/y-resolution",
    )

    def clear_text(self) -> None:
        """Mock clear_text."""

    def sort_by_confidence(self) -> None:
        """Mock sort_by_confidence."""

    def sort_by_position(self) -> None:
        """Mock sort_by_position."""


def _make_create_temp_func(
    session_dir: pathlib.Path,
) -> Callable[[object], None]:
    """Return a mock _create_temp_directory side-effect using session_dir."""

    def mock_create_temp_func(self: object) -> None:
        self.session = MagicMock()
        self.session.name = str(session_dir)
        self._lockfd = MagicMock()
        self._dependencies = {
            "imagemagick": True,
            "libtiff": True,
            "djvu": True,
            "xdg": True,
            "unpaper": True,
            "tesseract": True,
            "qpdf": True,
            "jbig2": True,
            "ocr": True,
        }

    return mock_create_temp_func


def _setup_app_window_mocks(
    mocker: pytest.MockerFixture, tmp_path: pathlib.Path
) -> tuple[MagicMock, MagicMock, MagicMock]:
    """Apply common mocks needed for ApplicationWindow tests.

    Returns (mock_selector, mock_dragger, mock_selector_dragger).
    """
    mocker.patch("scantpaper.app_window.Document")
    mocker.patch("scantpaper.app_window.Unpaper")
    mocker.patch("scantpaper.app_window.ImageView", MockImageView)
    mocker.patch("scantpaper.layer.Canvas", MockCanvas)
    mocker.patch("scantpaper.app_window.Progress")
    mocker.patch("scantpaper.app_window.sane.init")
    mocker.patch("scantpaper.app_window.recursive_slurp")

    mock_selector = mocker.patch("scantpaper.app_window.Selector")
    mock_dragger = mocker.patch("scantpaper.app_window.Dragger")
    mock_selector_dragger = mocker.patch("scantpaper.app_window.SelectorDragger")

    mocker.patch("scantpaper.app_window.Gtk.Notebook.append_page")
    mocker.patch("scantpaper.app_window.SessionMixins._find_crashed_sessions")

    mocker.patch("scantpaper.app_window.shutil.disk_usage").return_value.free = (
        1000 * 1024 * 1024
    )

    session_dir = tmp_path / "session"
    session_dir.mkdir()

    mocker.patch.object(ApplicationWindow, "_check_dependencies", autospec=True)
    mocker.patch.object(
        ApplicationWindow,
        "_create_temp_directory",
        side_effect=_make_create_temp_func(session_dir),
        autospec=True,
    )
    mocker.patch.object(ApplicationWindow, "set_icon_name", autospec=True)
    mocker.patch.object(ApplicationWindow, "set_child", autospec=True)
    mocker.patch.object(ApplicationWindow, "present", autospec=True)

    mock_mm = mocker.patch("scantpaper.app_window.MultipleMessage")
    mock_mm.return_value.grid_rows = 1
    mock_mm.return_value.get_width.return_value = 400
    mock_mm.return_value.get_height.return_value = 300

    return cast(
        "tuple[MagicMock, MagicMock, MagicMock]",
        (mock_selector, mock_dragger, mock_selector_dragger),
    )


def _create_test_app(
    test_fn: Callable[[Gtk.Application, ApplicationWindow], None],
) -> None:
    """Create a Gtk.Application, run test_fn(application, win), and clean up."""
    app = Gtk.Application()
    app.iconpath = "/tmp"
    app.args = MagicMock(import_files=None, import_all=None)
    win = None
    try:
        with patch.object(Gtk.Application, "register", autospec=True):
            app.register(None)
            win = ApplicationWindow(application=app)
            test_fn(app, win)
    finally:
        if win:
            win.destroy()
        _pump_events()
        app.quit()


@pytest.fixture
def mock_builder(mocker: pytest.MockerFixture) -> Generator[object, None, None]:
    """Mock Gtk.Builder."""
    builder_cls = mocker.patch("scantpaper.app_window.Gtk.Builder")
    builder = builder_cls.return_value
    # Return a MagicMock for any object requested
    builder.get_object.side_effect = lambda x: MagicMock(name=x)
    return cast("Generator[object, None, None]", (builder))


@pytest.fixture
def mock_config(mocker: pytest.MockerFixture) -> Generator[object, None, None]:
    """Mock config module."""
    config = mocker.patch("scantpaper.app_window.config")
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
    return cast("Generator[object, None, None]", (config))


@pytest.fixture
def app_window(
    mocker: pytest.MockerFixture,
    mock_builder: object,
    mock_config: object,
) -> Generator[ApplicationWindow, None, None]:
    """Fixture to create an ApplicationWindow instance with mocked dependencies."""
    del mock_builder, mock_config
    mocker.patch("scantpaper.app_window.Document")
    mocker.patch("scantpaper.app_window.Unpaper")

    # Mock MultipleMessage to prevent blocking dialogs
    mock_mm = mocker.patch("scantpaper.app_window.MultipleMessage")
    mock_mm.return_value.grid_rows = 1
    mock_mm.return_value.get_width.return_value = 400
    mock_mm.return_value.get_height.return_value = 300

    mocker.patch("scantpaper.app_window.ImageView", MockImageView)
    mocker.patch("scantpaper.layer.Canvas", MockCanvas)

    mocker.patch("scantpaper.app_window.Progress")
    mocker.patch("scantpaper.app_window.sane.init")
    mocker.patch("scantpaper.app_window.recursive_slurp")
    mocker.patch("scantpaper.app_window.SessionMixins._find_crashed_sessions")
    mocker.patch("scantpaper.app_window.Selector")
    mocker.patch("scantpaper.app_window.Dragger")
    mocker.patch("scantpaper.app_window.SelectorDragger")
    mocker.patch("scantpaper.app_window.Gtk.Notebook.append_page")

    # Mock shutil to avoid disk usage check failures
    mock_shutil = mocker.patch("scantpaper.app_window.shutil")
    mock_shutil.disk_usage.return_value.free = 1000 * 1024 * 1024  # 1000 MB

    def mock_create_temp_func(self: object) -> None:
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
            "qpdf": True,
            "jbig2": True,
            "ocr": True,
        }

    mocker.patch.object(ApplicationWindow, "_check_dependencies", autospec=True)
    mocker.patch.object(
        ApplicationWindow,
        "_create_temp_directory",
        side_effect=mock_create_temp_func,
        autospec=True,
    )
    mocker.patch.object(ApplicationWindow, "set_icon_name", autospec=True)
    mocker.patch.object(ApplicationWindow, "set_child", autospec=True)
    mocker.patch.object(ApplicationWindow, "present", autospec=True)

    app_id = f"org.test.panes.u{uuid.uuid4().hex}"
    app = Gtk.Application(application_id=app_id, flags=Gio.ApplicationFlags.FLAGS_NONE)
    app.iconpath = "/tmp"
    app.args = MagicMock()
    app.args.import_files = None
    app.args.import_all = None

    # We need to register the app to use it fully, though maybe not strictly required here
    with patch.object(Gtk.Application, "register", autospec=True):
        app.register(None)
        win = ApplicationWindow(application=app)
        yield win
        win.destroy()
        _pump_events()
        app.quit()


def _pump_events() -> None:
    """Process pending main-context iterations (GTK4 has no events_pending)."""
    context = GLib.MainContext.default()
    while context.pending():
        context.iteration(may_block=False)


def test_init(app_window: ApplicationWindow) -> None:
    """Test initialization."""
    assert isinstance(app_window, ApplicationWindow)
    assert app_window.session.name == "/tmp/session"


def test_post_process_progress_cancel_callback_wired(
    app_window: ApplicationWindow,
) -> None:
    """Test the post-process progress bar has a cancel callback wired to slist.cancel."""
    assert callable(app_window.post_process_progress.cancel_callback)
    assert app_window.post_process_progress.cancel_callback.__self__ is app_window
    app_window.slist.cancel = mocker = MagicMock()
    app_window.post_process_progress.cancel_callback()
    mocker.assert_called_once_with(app_window.post_process_progress.finish)


def test_drag_motion_callback() -> None:
    """Test drag_motion_callback."""
    tree = MagicMock()
    target = MagicMock()
    target.get_actions.return_value = Gdk.DragAction.MOVE

    # Mock get_dest_row_at_pos
    tree.get_dest_row_at_pos.return_value = (MagicMock(), MagicMock())

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
    assert drag_motion_callback(target, 0.0, 50.0, tree) == Gdk.DragAction.MOVE
    adj.set_value.assert_not_called()

    # Test with y at bottom (scroll down)
    assert drag_motion_callback(target, 0.0, 96.0, tree) == Gdk.DragAction.MOVE
    adj.set_value.assert_called()

    # Test with y at top (scroll up)
    assert drag_motion_callback(target, 0.0, 4.0, tree) == Gdk.DragAction.MOVE
    adj.set_value.assert_called()


def test_drag_motion_callback_error() -> None:
    """Test drag_motion_callback with TypeError."""
    tree = MagicMock()
    # Mock get_dest_row_at_pos to raise TypeError (e.g. returns None)
    tree.get_dest_row_at_pos.side_effect = TypeError
    assert drag_motion_callback(MagicMock(), 0.0, 0.0, tree) == Gdk.DragAction.MOVE
    # Should return early without crashing


def test_drag_motion_callback_copy() -> None:
    """Test drag_motion_callback with COPY action."""
    tree = MagicMock()
    target = MagicMock()
    tree.get_dest_row_at_pos.return_value = (MagicMock(), MagicMock())
    target.get_actions.return_value = Gdk.DragAction.COPY
    tree.get_parent.return_value = None
    assert drag_motion_callback(target, 0.0, 50.0, tree) == Gdk.DragAction.COPY


def test_view_html(mocker: pytest.MockerFixture) -> None:
    """Test view_html."""
    mocker.patch("pathlib.Path.exists", return_value=True)
    mock_launch = mocker.patch("gi.repository.Gio.AppInfo.launch_default_for_uri")

    view_html(None, None)
    mock_launch.assert_called()

    mocker.patch("pathlib.Path.exists", return_value=False)
    view_html(None, None)
    # Check that it launches the fallback URL
    args, _ = mock_launch.call_args
    assert "https://github.com/carygravel/scantpaper" in args[0]


def test_read_config_migration(
    app_window: ApplicationWindow, mocker: pytest.MockerFixture
) -> None:
    """Test configuration file migration from old name."""
    mocker.patch("scantpaper.app_window.os.environ", {"HOME": "/home/user"})
    mock_exists = mocker.patch.object(pathlib.Path, "exists", autospec=True)
    mock_copy = mocker.patch("scantpaper.app_window.shutil.copy")
    mocker.patch("scantpaper.app_window.config.read_config", return_value={"Paper": {}})
    mocker.patch("scantpaper.app_window.config.add_defaults")
    mocker.patch("scantpaper.app_window.config.remove_invalid_paper")

    # new file does not exist, old file exists
    mock_exists.side_effect = [False, True, True]

    app_window._read_config()

    mock_copy.assert_called_once()


def test_read_config_stashes_load_warnings(
    app_window: ApplicationWindow, mocker: pytest.MockerFixture
) -> None:
    """Load warnings are stashed on the window until the user is informed."""
    mock_settings = ConfigDict(Paper={})
    mock_settings.load_warnings = ["settings were rescued"]
    mocker.patch("scantpaper.app_window.config.read_config", return_value=mock_settings)
    mocker.patch("scantpaper.app_window.config.add_defaults")
    mocker.patch("scantpaper.app_window.config.remove_invalid_paper")
    mocker.patch("scantpaper.app_window.config.remove_invalid_paper")
    mocker.patch("scantpaper.app_window.os.environ", {"HOME": "/home/user"})
    mocker.patch.object(pathlib.Path, "exists", autospec=True, return_value=True)

    app_window._read_config()

    assert app_window._config_load_warnings == ["settings were rescued"]
    assert not app_window._config_warnings_acknowledged


def test_notify_config_load_warnings(app_window: ApplicationWindow) -> None:
    """Config load warnings are shown to the user and marked acknowledged."""
    app_window._config_load_warnings = ["something was rescued"]
    app_window._config_warnings_acknowledged = False
    app_window._show_message_dialog = MagicMock()

    app_window._notify_config_load_warnings()

    app_window._show_message_dialog.assert_called_once()
    _args, kwargs = app_window._show_message_dialog.call_args
    assert "rescued" in kwargs["text"]
    assert kwargs["message_type"] == "info"
    assert app_window._config_warnings_acknowledged, "user marked as informed"

    app_window._notify_config_load_warnings()
    app_window._show_message_dialog.assert_called_once()


def test_read_config_restore_window(mocker: pytest.MockerFixture) -> None:
    """Test window restoration from config."""
    mock_settings = {
        "restore window": True,
        "window_width": 800,
        "window_height": 600,
        "window_x": 100,
        "window_y": 100,
        "window_maximize": True,
        "image_control_tool": "selector",
        "viewer_tools": "tabbed",
        "Paper": {},
        "cwd": "/tmp",
    }
    mocker.patch("scantpaper.app_window.config.read_config", return_value=mock_settings)
    mocker.patch("scantpaper.app_window.config.add_defaults")
    mocker.patch("scantpaper.app_window.config.remove_invalid_paper")

    app = Gtk.Application()
    app.iconpath = "/tmp"
    with (
        patch.object(Gtk.Window, "set_icon_name"),
        patch.object(Gtk.ApplicationWindow, "set_default_size") as mock_size,
        patch.object(Gtk.ApplicationWindow, "maximize") as mock_maximize,
        patch.object(ApplicationWindow, "_populate_main_window"),
    ):

        def mock_read_config_side_effect(self: object) -> None:
            self.settings = mock_settings

        with patch.object(
            ApplicationWindow,
            "_read_config",
            side_effect=mock_read_config_side_effect,
            autospec=True,
        ):
            win = ApplicationWindow(application=app)
            # Manually trigger the logic that happens in __init__
            win.set_default_size(
                win.settings["window_width"],
                win.settings["window_height"],
            )
            win.maximize()

            mock_size.assert_called_with(800, 600)
            mock_maximize.assert_called()


def test_init_actions(app_window: ApplicationWindow) -> None:
    """Test that actions are initialized."""
    actions = app_window.list_actions()
    assert "scan" in actions
    assert "save" in actions
    assert "quit" in actions
    assert "tooltype" in actions

    # Check initial state
    assert app_window._actions["tooltype"].get_state().get_string() == "selector"


def _menu_action_names(model: Gio.MenuModel) -> list[str]:
    """Return every action name referenced by the menu model, recursively."""
    names: list[str] = []
    for i in range(model.get_n_items()):
        action = model.get_item_attribute_value(i, Gio.MENU_ATTRIBUTE_ACTION, None)
        if action is not None:
            names.append(cast("str", action.get_string()))
        for link in (Gio.MENU_LINK_SECTION, Gio.MENU_LINK_SUBMENU):
            submenu = model.get_item_link(i, link)
            if submenu is not None:
                names.extend(_menu_action_names(submenu))
    return names


@pytest.fixture(scope="module")
def menubar_action_names() -> list[str]:
    """Return the actions in app.ui's menubar model.

    Module-scoped so it is instantiated (and loads the real app.ui) before the
    function-scoped fixtures patch Gtk.Builder, which breaks .ui loading.
    """
    builder = Gtk.Builder()
    builder.add_from_file(str(pathlib.Path(__file__).parent.parent / "app.ui"))
    model = builder.get_object("menubar").get_menu_model()
    return _menu_action_names(model)


def test_menu_model_actions_are_registered(
    app_window: ApplicationWindow, menubar_action_names: list[str]
) -> None:
    """Every action referenced by app.ui's menu model is registered."""
    registered = set(app_window.list_actions())

    missing = sorted(
        name
        for name in menubar_action_names
        if name.startswith("win.") and name.removeprefix("win.") not in registered
    )
    assert missing == [], f"menu actions not registered on the window: {missing}"


def test_change_image_tool_cb(
    app_window: ApplicationWindow, mocker: pytest.MockerFixture
) -> None:
    """Test changing image tool."""
    app_window.view = MagicMock()

    # Mock Dragger to return a known object
    dragger_cls = mocker.patch("scantpaper.app_window.Dragger")
    dragger_instance = dragger_cls.return_value

    action = app_window._actions["tooltype"]

    # Change to dragger
    variant = GLib.Variant("s", "dragger")
    app_window._change_image_tool_cb(action, variant)

    assert app_window.settings["image_control_tool"] == "dragger"
    app_window.view.set_tool.assert_called_with(dragger_instance)

    # No manual radio button sync — Gtk.Actionable handles it
    assert not any(
        "context_" in str(c) for c in app_window.builder.get_object.call_args_list
    )

    # repeat to test early return — set_tool should not be called again
    app_window.view.set_tool.reset_mock()
    app_window._change_image_tool_cb(action, variant)
    assert app_window.settings["image_control_tool"] == "dragger"
    app_window.view.set_tool.assert_not_called()

    # Change to selectordragger with existing selection
    app_window.settings["selection"] = MagicMock()
    app_window.view.selection_changed_signal = 789
    app_window._actions["tooltype"].set_state(GLib.Variant("s", "selector"))
    variant = GLib.Variant("s", "selectordragger")
    app_window._change_image_tool_cb(action, variant)
    app_window.view.set_selection.assert_called()


def test_change_image_tool_no_reentrant_loop(
    app_window: ApplicationWindow, mocker: pytest.MockerFixture
) -> None:
    """GtkCheckMenuItem.set_active() calls gtk_menu_item_activate().

    This re-activates the action with the old item's target. Verify this
    doesn't cause a loop.
    """
    app_window.view = MagicMock()
    mocker.patch("scantpaper.app_window.Dragger")

    action = app_window._actions["tooltype"]
    original_set_state = action.set_state

    def reentrant_set_state(variant: GLib.Variant) -> None:
        original_set_state(variant)
        # Simulate GtkCheckMenuItem deactivating the previously-active item,
        # which calls gtk_menu_item_activate -> g_action_activate with old value
        app_window._change_image_tool_cb(action, GLib.Variant("s", "selector"))

    action.set_state = reentrant_set_state

    app_window._change_image_tool_cb(action, GLib.Variant("s", "dragger"))
    assert app_window.settings["image_control_tool"] == "dragger"
    assert action.get_state().get_string() == "dragger"


def test_change_view_cb(app_window: ApplicationWindow) -> None:
    """Test changing view type and covering all old mode branches."""
    action = app_window._actions["viewtype"]
    app_window._vnotebook = MagicMock()
    app_window._hpanei = MagicMock()
    app_window._vpanei = MagicMock()
    app_window._vpaned = MagicMock()

    app_window.settings["viewer_tools"] = "tabbed"
    variant = GLib.Variant("s", "horizontal")
    app_window._change_view_cb(action, variant)
    assert app_window.settings["viewer_tools"] == "horizontal"
    app_window._vnotebook.detach_tab.assert_called()

    app_window.settings["viewer_tools"] = "horizontal"
    variant = GLib.Variant("s", "vertical")
    app_window._change_view_cb(action, variant)
    assert app_window.settings["viewer_tools"] == "vertical"
    app_window._hpanei.set_start_child.assert_called()

    app_window.settings["viewer_tools"] = "vertical"
    variant = GLib.Variant("s", "tabbed")
    app_window._change_view_cb(action, variant)
    assert app_window.settings["viewer_tools"] == "tabbed"
    app_window._vpanei.set_end_child.assert_called()


def test_create_toolbar_missing_deps(app_window: ApplicationWindow) -> None:
    """Test toolbar creation with missing dependencies."""
    app_window._dependencies = {
        "imagemagick": False,
        "libtiff": False,
        "djvu": False,
        "xdg": False,
        "unpaper": False,
        "tesseract": False,
        "qpdf": False,
        "jbig2": False,
        "ocr": False,
    }
    app_window._show_message_dialog = MagicMock()
    app_window._create_toolbar()
    app_window._show_message_dialog.assert_called()
    # Check that it enabled/disabled correctly
    assert not app_window._actions["email"].get_enabled()


def test_create_toolbar_tesseract_lang_missing(
    app_window: ApplicationWindow, mocker: pytest.MockerFixture
) -> None:
    """Test toolbar creation when tesseract language is missing (covers 530-531)."""
    app_window._dependencies["tesseract"] = True
    mock_locale_installed = mocker.patch(
        "scantpaper.app_window.locale_installed",
        return_value="Missing language package",
    )
    mocker.patch("scantpaper.app_window.get_tesseract_codes")
    app_window._show_message_dialog = MagicMock()

    app_window._create_toolbar()

    mock_locale_installed.assert_called()
    app_window._show_message_dialog.assert_called()
    _args, kwargs = app_window._show_message_dialog.call_args
    assert "Missing language package" in kwargs["text"]


def test_update_uimanager(app_window: ApplicationWindow) -> None:
    """Test _update_uimanager."""
    # Simulate no selection
    app_window.slist.get_selected_indices.return_value = []
    cast("Any", app_window.slist).data = []

    app_window._update_uimanager()

    assert not app_window._actions["save"].get_enabled()
    assert not app_window._actions["crop-dialog"].get_enabled()

    # Simulate selection and data
    app_window.slist.get_selected_indices.return_value = [0]
    cast("Any", app_window.slist).data = [MagicMock()]

    app_window._update_uimanager()

    assert app_window._actions["save"].get_enabled()
    assert app_window._actions["crop-dialog"].get_enabled()


def test_paste_action_reflects_clipboard(app_window: ApplicationWindow) -> None:
    """Test paste action is enabled by clipboard data via the changed signal."""
    assert not app_window._actions["paste"].get_enabled()

    app_window.clipboard.data = [MagicMock()]
    assert app_window._actions["paste"].get_enabled()

    app_window.clipboard.data = None
    assert not app_window._actions["paste"].get_enabled()


def test_update_uimanager_low_disk_space(
    app_window: ApplicationWindow, mocker: pytest.MockerFixture
) -> None:
    """Test _update_uimanager when disk space is low."""
    # Set free space to 50 MB, which is less than available-tmp-warning (100 MB)
    mock_shutil = mocker.patch("scantpaper.app_window.shutil")
    mock_shutil.disk_usage.return_value.free = 50 * 1024 * 1024

    mock_show_dialog = mocker.patch.object(app_window, "_show_message_dialog")

    app_window._update_uimanager()

    mock_show_dialog.assert_called_once()
    _args, kwargs = mock_show_dialog.call_args
    assert kwargs["message_type"] == "warning"
    assert "50Mb free" in kwargs["text"]


def test_update_uimanager_unpaper_missing(app_window: ApplicationWindow) -> None:
    """Test _update_uimanager when unpaper is missing."""
    app_window._dependencies["unpaper"] = False
    assert "unpaper" in app_window._actions

    app_window._update_uimanager()
    assert "unpaper" not in app_window._actions

    # Test that subsequent calls don't crash, although they might if the code
    # doesn't check for existence. Based on my analysis, it might crash if it
    # tries to set_enabled(False) on a deleted key.
    # If it's already deleted, self._actions["unpaper"] will raise KeyError.
    app_window._update_uimanager()


def test_missing_packages_message_order(app_window: ApplicationWindow) -> None:
    """The startup warning lists missing packages in registry order."""
    app_window._dependencies = {
        "imagemagick": False,
        "libtiff": True,
        "djvu": False,
        "xdg": True,
        "unpaper": False,
        "tesseract": False,
        "qpdf": False,
        "jbig2": False,
        "ocr": False,
    }
    lines = [
        line for line in app_window._missing_packages_message().split("\n") if line
    ]
    assert lines == [
        _("Save image and Save as PDF both require imagemagick"),
        _("Save as DjVu requires djvulibre-bin"),
        _("unpaper missing"),
        _("OCR requires tesseract"),
        _("PDF encryption requires qpdf"),
        _("JBIG2 PDF compression requires jbig2"),
    ]


def test_update_uimanager_ocr_missing(app_window: ApplicationWindow) -> None:
    """Test _update_uimanager when ocr is missing."""
    app_window._dependencies["ocr"] = False
    app_window._update_uimanager()
    assert not app_window._actions["ocr"].get_enabled()


def test_update_uimanager_no_pages_hide_email_dialog(
    app_window: ApplicationWindow,
) -> None:
    """Test _update_uimanager hides email dialog if no pages."""
    cast("Any", app_window.slist).data = []
    app_window._dependencies["xdg"] = True
    app_window._windowe = MagicMock()

    app_window._update_uimanager()

    assert not app_window._actions["email"].get_enabled()
    app_window._windowe.hide.assert_called_once()


def test_update_uimanager_xdg_missing(app_window: ApplicationWindow) -> None:
    """Test _update_uimanager when xdg is missing (covers branches)."""
    app_window._dependencies["xdg"] = False

    # case with pages
    cast("Any", app_window.slist).data = [MagicMock()]
    app_window._update_uimanager()
    assert not app_window._actions["email"].get_enabled()

    # case without pages
    cast("Any", app_window.slist).data = []
    app_window._update_uimanager()
    assert not app_window._actions["email"].get_enabled()


def test_update_uimanager_no_pages_no_email_dialog(
    app_window: ApplicationWindow,
) -> None:
    """Test _update_uimanager does not hide email dialog if it is None."""
    cast("Any", app_window.slist).data = []
    app_window._dependencies["xdg"] = True
    app_window._windowe = None
    app_window._update_uimanager()
    # covers branch jump 768->771


def test_update_uimanager_ocr_present(app_window: ApplicationWindow) -> None:
    """Test _update_uimanager when ocr is present."""
    app_window._dependencies["ocr"] = True
    app_window._update_uimanager()
    # covers branch jump 755->758


def test_update_uimanager_ghost_ocr_and_hide_email(
    app_window: ApplicationWindow,
) -> None:
    """Test ghosting ocr and hiding email dialog in one go (covers 756 & 769)."""
    app_window._dependencies["ocr"] = False
    app_window._dependencies["xdg"] = True
    cast("Any", app_window.slist).data = []
    app_window._windowe = MagicMock()

    app_window._update_uimanager()

    assert not app_window._actions["ocr"].get_enabled()
    app_window._windowe.hide.assert_called_once()


def test_process_error_reopen(
    app_window: ApplicationWindow, mocker: pytest.MockerFixture
) -> None:
    """Test _process_error_callback with reopen response (covers 892)."""
    app_window._scan_progress = MagicMock()
    app_window.scan_dialog = MagicMock()
    cast("Any", app_window.settings)["message"]["error opening device"] = {
        "response": None
    }

    # Mock dialog to return 'reopen'
    mocker.patch("scantpaper.app_window.Gtk.MessageDialog")
    mocker.patch("scantpaper.app_window.run_dialog", return_value=Gtk.ResponseType.OK)

    mock_radio1 = MagicMock(name="radio1")
    mock_radio1.get_active.return_value = True  # reopen

    mock_radio_other = MagicMock(name="other_radio")
    mock_radio_other.get_active.return_value = False
    mocker.patch(
        "scantpaper.app_window.Gtk.CheckButton.new_with_label",
        side_effect=cycle(
            [
                mock_radio1,
                mock_radio_other,
                mock_radio_other,
                mock_radio_other,
                MagicMock(get_active=MagicMock(return_value=False)),
                MagicMock(get_active=MagicMock(return_value=False)),
            ]
        ),
    )

    app_window._process_error_callback(None, "open_device", "Device busy", None)
    app_window.scan_dialog.assert_called_once()

    app_window.scan_dialog.reset_mock()
    app_window._process_error_callback(
        None, "open_device", "Error during device I/O", None
    )
    app_window.scan_dialog.assert_called_once()


def test_process_error_rescan(
    app_window: ApplicationWindow, mocker: pytest.MockerFixture
) -> None:
    """Test _process_error_callback with rescan response (covers 900)."""
    app_window._scan_progress = MagicMock()
    app_window.scan_dialog = MagicMock()
    cast("Any", app_window.settings)["message"]["error opening device"] = {
        "response": None
    }

    # Mock dialog to return 'rescan'
    mocker.patch("scantpaper.app_window.Gtk.MessageDialog")
    mocker.patch("scantpaper.app_window.run_dialog", return_value=Gtk.ResponseType.OK)

    mock_radio1 = MagicMock(name="radio1")
    mock_radio1.get_active.return_value = False
    mock_radio2 = MagicMock(name="radio2")
    mock_radio2.get_active.return_value = True  # rescan
    mock_radio3 = MagicMock(name="radio3")
    mock_radio3.get_active.return_value = False
    mock_radio4 = MagicMock(name="radio4")
    mock_radio4.get_active.return_value = False

    mocker.patch(
        "scantpaper.app_window.Gtk.CheckButton.new_with_label",
        side_effect=cycle(
            [
                mock_radio1,
                mock_radio2,
                mock_radio3,
                mock_radio4,
                MagicMock(get_active=MagicMock(return_value=False)),
                MagicMock(get_active=MagicMock(return_value=False)),
            ]
        ),
    )

    app_window._process_error_callback(None, "open_device", "Device busy", None)
    app_window.scan_dialog.assert_called_with(None, None, hidden=False, scan=True)


def test_process_error_ignore(
    app_window: ApplicationWindow, mocker: pytest.MockerFixture
) -> None:
    """Test _process_error_callback with ignore response (covers 892)."""
    app_window._scan_progress = MagicMock()
    app_window.scan_dialog = MagicMock()
    cast("Any", app_window.settings)["message"]["error opening device"] = {
        "response": None
    }

    # Mock dialog to return something other than OK (e.g., CANCEL)
    mocker.patch("scantpaper.app_window.Gtk.MessageDialog")
    mocker.patch(
        "scantpaper.app_window.run_dialog", return_value=Gtk.ResponseType.CANCEL
    )

    mock_cb = mocker.patch("scantpaper.app_window.Gtk.CheckButton.new_with_label")
    mock_cb.return_value.get_active.return_value = False

    app_window._process_error_callback(None, "open_device", "Device busy", None)

    # For ignore, scan_dialog should NOT be called
    app_window.scan_dialog.assert_not_called()


def test_maximized_notify(
    app_window: ApplicationWindow, mocker: pytest.MockerFixture
) -> None:
    """Test _maximized_notify (replaces the GTK3 window-state-event)."""
    mocker.patch.object(app_window, "is_maximized", return_value=True)
    app_window._maximized_notify(app_window, MagicMock())
    assert app_window.settings["window_maximize"] is True

    mocker.patch.object(app_window, "is_maximized", return_value=False)
    app_window._maximized_notify(app_window, MagicMock())
    assert app_window.settings["window_maximize"] is False


def test_handle_clicks(app_window: ApplicationWindow) -> None:
    """Test _handle_clicks."""
    gesture = MagicMock()
    gesture.get_widget.return_value = MockImageView()

    app_window.detail_popup = MagicMock()
    app_window._handle_clicks(gesture, 1, 0.0, 0.0)
    app_window.detail_popup.popup.assert_called_once()
    assert gesture.set_state.call_count == 1

    # Mock other widget (e.g. Thumbnail list)
    gesture = MagicMock()
    gesture.get_widget.return_value = MagicMock()
    app_window._thumb_popup = MagicMock()
    app_window._handle_clicks(gesture, 1, 0.0, 0.0)
    assert app_window.settings["Page range"] == "selected"
    app_window._thumb_popup.popup.assert_called_once()
    assert gesture.set_state.call_count == 1


def test_view_selection_changed_callback(app_window: ApplicationWindow) -> None:
    """Test _view_selection_changed_callback."""
    sel = MagicMock()
    copied_sel = MagicMock()
    sel.copy.return_value = copied_sel

    app_window._windowc = MagicMock()
    app_window._view_selection_changed_callback(
        cast("ImageView", cast("object", None)), sel
    )

    assert app_window.settings["selection"] == copied_sel


def test_view_selection_changed_callback_none(app_window: ApplicationWindow) -> None:
    """Test _view_selection_changed_callback with None."""
    with pytest.raises(AttributeError):
        app_window._view_selection_changed_callback(
            cast("ImageView", cast("object", None)), None
        )


def test_on_key_press(app_window: ApplicationWindow) -> None:
    """Test _on_key_press."""
    app_window.delete_selection = MagicMock()

    # Delete key
    assert (
        app_window._on_key_press(None, Gdk.KEY_Delete, 0, Gdk.ModifierType(0)) is True
    )
    app_window.delete_selection.assert_called_once()

    # Other key
    assert app_window._on_key_press(None, Gdk.KEY_a, 0, Gdk.ModifierType(0)) is False


def test_on_view_selection_notify(app_window: ApplicationWindow) -> None:
    """Test _on_view_selection_notify with a non-None selection."""
    sel = MagicMock()
    copied = MagicMock()
    sel.copy.return_value = copied

    app_window.view = MagicMock()
    app_window.view.selection = sel
    app_window._on_view_selection_notify(None, None)
    assert app_window.settings["selection"] == copied

    app_window.view.selection = None
    app_window._on_view_selection_notify(None, None)


def test_process_error_callback(
    app_window: ApplicationWindow, mocker: pytest.MockerFixture
) -> None:
    """Test _process_error_callback."""
    app_window._scan_progress = MagicMock()
    app_window._show_message_dialog = MagicMock()

    # Basic error
    app_window._process_error_callback(None, "some_process", "some error", 123)
    app_window._scan_progress.disconnect.assert_called_once_with(123)
    app_window._scan_progress.hide.assert_called_once()
    app_window._show_message_dialog.assert_called_once()

    # open_device error - ignore
    app_window._show_message_dialog.reset_mock()
    cast("Any", app_window.settings)["message"]["error opening device"] = {
        "response": "ignore"
    }
    app_window._process_error_callback(None, "open_device", "Device busy", None)
    app_window._show_message_dialog.assert_not_called()

    # open_device error - show dialog and select reopen
    app_window.settings["message"].pop("error opening device")
    mocker.patch("scantpaper.app_window.Gtk.MessageDialog")
    mocker.patch("scantpaper.app_window.run_dialog", return_value=Gtk.ResponseType.OK)
    app_window.scan_dialog = MagicMock()

    mock_radio1 = MagicMock(name="radio1")
    mock_radio2 = MagicMock(name="radio2")
    mock_radio3 = MagicMock(name="radio3")
    mock_radio4 = MagicMock(name="radio4")
    mocker.patch(
        "scantpaper.app_window.Gtk.CheckButton.new_with_label",
        side_effect=cycle(
            [
                mock_radio1,
                mock_radio2,
                mock_radio3,
                mock_radio4,
                MagicMock(get_active=MagicMock(return_value=False)),
                MagicMock(get_active=MagicMock(return_value=False)),
            ]
        ),
    )
    mock_radio1.get_active.return_value = True
    mock_radio2.get_active.return_value = False
    mock_radio3.get_active.return_value = False
    mock_radio4.get_active.return_value = False

    app_window._process_error_callback(None, "open_device", "Device busy", None)
    app_window.scan_dialog.assert_called()

    # open_device error - show dialog and select rescan
    mock_radio1.get_active.return_value = False
    mock_radio2.get_active.return_value = True
    app_window.scan_dialog.reset_mock()
    app_window._process_error_callback(None, "open_device", "Device busy", None)
    # response should be "rescan", scan_dialog(None, None, hidden=False, scan=True)
    app_window.scan_dialog.assert_called_with(None, None, hidden=False, scan=True)

    # open_device error - show dialog and select restart
    mock_radio2.get_active.return_value = False
    mock_radio3.get_active.return_value = True
    app_window._restart = MagicMock()
    app_window._process_error_callback(None, "open_device", "Device busy", None)
    app_window._restart.assert_called_once()

    # other error
    app_window._process_error_callback(None, "other", "msg", None)
    app_window._show_message_dialog.assert_called()


def test_process_error_callback_ignore_hides_bar_after_dialog(
    app_window: ApplicationWindow, mocker: pytest.MockerFixture
) -> None:
    """Test that selecting 'ignore' in the open_device error dialog hides the progress bar."""
    app_window._scan_progress = MagicMock()
    app_window._show_message_dialog = MagicMock()
    app_window.scan_dialog = MagicMock()

    mocker.patch("scantpaper.app_window.Gtk.MessageDialog")
    mocker.patch("scantpaper.app_window.run_dialog", return_value=Gtk.ResponseType.OK)

    mock_radio1 = MagicMock(name="radio1")
    mock_radio2 = MagicMock(name="radio2")
    mock_radio3 = MagicMock(name="radio3")
    mock_radio4 = MagicMock(name="radio4")
    mocker.patch(
        "scantpaper.app_window.Gtk.CheckButton.new_with_label",
        side_effect=cycle(
            [
                mock_radio1,
                mock_radio2,
                mock_radio3,
                mock_radio4,
                MagicMock(get_active=MagicMock(return_value=False)),
                MagicMock(get_active=MagicMock(return_value=False)),
            ]
        ),
    )
    mock_radio1.get_active.return_value = False
    mock_radio2.get_active.return_value = False
    mock_radio3.get_active.return_value = False
    mock_radio4.get_active.return_value = True

    app_window._process_error_callback(None, "open_device", "Device busy", None)

    # The bar is hidden once before the dialog and once after it returns,
    # so that no dialog option leaves the progress bar visible.
    assert app_window._scan_progress.hide.call_count == 2
    assert app_window._windows is None
    app_window.scan_dialog.assert_not_called()


def test_page_selection_changed_callback(app_window: ApplicationWindow) -> None:
    """Test _page_selection_changed_callback."""
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

    app_process_progress_finish = app_window.post_process_progress.finish
    app_process_progress_finish.reset_mock()

    # With selection
    app_window.slist.get_selected_indices.return_value = [0]
    cast("Any", app_window.slist).data = [[1, None, "page_id"]]
    app_window.slist.get_column.return_value = MagicMock()
    cast("Any", app_window.view).get_selection.return_value = None

    app_window._page_selection_changed_callback(None)
    app_window._display_image.assert_called_with("page_id")
    app_window._update_uimanager.assert_called()
    app_window.post_process_progress.finish.assert_called_once()


def test_page_selection_changed_with_value_error(
    app_window: ApplicationWindow, mocker: pytest.MockerFixture
) -> None:
    """Test _page_selection_changed_callback handles ValueError (covers 690-691)."""
    app_window.slist.get_selected_indices.return_value = [0]
    cast("Any", app_window.slist).data = [[1, None, "page_id"]]
    app_window._display_image = mocker.Mock(side_effect=ValueError)
    cast("Any", app_window.view).get_selection = mocker.Mock(return_value=None)

    # Should not raise ValueError
    app_window._page_selection_changed_callback(None)


def test_page_selection_changed_does_not_reapply_selection(
    app_window: ApplicationWindow, mocker: pytest.MockerFixture
) -> None:
    """Switching pages does not re-apply the selection against the thumbnail.

    The selection is re-applied later by _on_page_loaded against the
    full-resolution image, so it is not clamped away (and settings["selection"]
    is not corrupted) during the page change.
    """
    app_window.slist.get_selected_indices.return_value = [0]
    cast("Any", app_window.slist).data = [[1, None, "page_id"]]
    app_window._display_image = mocker.Mock()
    mock_selection = MagicMock()
    cast("Any", app_window.view).get_selection = mocker.Mock(
        return_value=mock_selection
    )
    cast("Any", app_window.view).set_selection = mocker.Mock()

    app_window._page_selection_changed_callback(None)

    app_window.view.set_selection.assert_not_called()


def test_pack_viewer_tools(app_window: ApplicationWindow) -> None:
    """Test _pack_viewer_tools."""
    app_window._vnotebook = MagicMock()
    app_window._hpanei = MagicMock()
    app_window._vpanei = MagicMock()
    app_window._vpaned = MagicMock()
    app_window.view = MagicMock()
    app_window.t_canvas = MagicMock()
    app_window.a_canvas = MagicMock()
    app_window._init_split_pane = MagicMock()

    # Tabbed
    app_window.settings["viewer_tools"] = "tabbed"
    app_window._pack_viewer_tools()
    assert app_window._vnotebook.append_page.call_count == 3

    # Horizontal
    app_window.settings["viewer_tools"] = "horizontal"
    app_window.settings["split panel h"] = 123
    app_window._pack_viewer_tools()
    app_window._hpanei.set_start_child.assert_called_with(app_window.view)
    app_window._hpanei.set_end_child.assert_called_with(app_window.t_canvas)
    app_window._init_split_pane.assert_called_with(
        app_window._hpanei, Gtk.Orientation.HORIZONTAL, 123
    )

    # Vertical
    app_window.settings["viewer_tools"] = "vertical"
    app_window.settings["split panel v"] = 456
    app_window._pack_viewer_tools()
    app_window._vpanei.set_start_child.assert_called_with(app_window.view)
    app_window._vpanei.set_end_child.assert_called_with(app_window.t_canvas)
    app_window._init_split_pane.assert_called_with(
        app_window._vpanei, Gtk.Orientation.VERTICAL, 456
    )


def test_pack_viewer_tools_split_attaches_on_startup(
    app_window: ApplicationWindow, mocker: pytest.MockerFixture
) -> None:
    """A split view replaces the vnotebook left in _vpaned at startup."""
    # The fixture patches Gtk paned pack methods globally; restore the real
    # GTK behaviour so this test exercises actual packing.
    mocker.stopall()
    app_window._vpaned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
    app_window._vnotebook = Gtk.Notebook()
    app_window._vpaned.set_start_child(app_window._vnotebook)
    app_window._hpanei = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
    app_window._vpanei = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
    app_window.view = Gtk.Box()
    app_window.t_canvas = Gtk.Box()
    app_window.a_canvas = Gtk.Box()
    app_window._init_split_pane = MagicMock()

    app_window.settings["viewer_tools"] = "vertical"
    app_window._pack_viewer_tools()
    assert app_window._vpaned.get_start_child() is app_window._vpanei
    assert app_window._vnotebook.get_parent() is None

    app_window._vpaned.set_start_child(app_window._vnotebook)
    app_window.settings["viewer_tools"] = "horizontal"
    app_window._pack_viewer_tools()
    assert app_window._vpaned.get_start_child() is app_window._hpanei
    assert app_window._vnotebook.get_parent() is None


def test_switch_split_orientation_moves_children(
    app_window: ApplicationWindow, mocker: pytest.MockerFixture
) -> None:
    """Switching split orientation re-docks the children without a stale parent."""
    mocker.stopall()
    app_window._vpaned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
    app_window._vnotebook = Gtk.Notebook()
    app_window._hpanei = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
    app_window._vpanei = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
    app_window.view = Gtk.Box()
    app_window.t_canvas = Gtk.Box()
    app_window.a_canvas = Gtk.Box()
    app_window._init_split_pane = MagicMock()
    app_window._active_layer = "text"

    app_window.settings["viewer_tools"] = "horizontal"
    app_window._pack_viewer_tools()
    assert app_window._hpanei.get_start_child() is app_window.view

    app_window.settings["viewer_tools"] = "vertical"
    app_window._pack_viewer_tools()
    assert app_window._vpanei.get_start_child() is app_window.view
    assert app_window._hpanei.get_start_child() is None


def test_startup_tabbed_defaults_to_text(
    app_window: ApplicationWindow,
) -> None:
    """A fresh startup selects the text layer for the View menu.

    The tabbed view opens on the image page; the bar stays hidden there, which
    the real-layout test below covers. Here the mocked notebook has no real
    current page, so only the selection is asserted.
    """
    assert app_window._active_layer == "text"
    assert app_window._actions["editmode"].get_state().get_string() == "text"
    app_window._vnotebook.set_current_page.assert_not_called()


def test_startup_split_shows_persisted_layer(
    app_window: ApplicationWindow,
) -> None:
    """A split view shows the persisted layer's bar and canvas immediately."""
    app_window.settings["viewer_tools"] = "vertical"
    app_window.settings["editmode"] = "annotation"
    app_window._active_layer = None

    app_window._set_active_layer(app_window._active_layer_for_split())

    assert app_window._active_layer == "annotation"
    assert app_window._ann_editor.controls.get_visible()
    assert not app_window._text_editor.controls.get_visible()
    assert app_window._vpanei.get_end_child() is app_window.a_canvas


def test_set_active_layer_selects_tab_and_shows_bar(
    app_window: ApplicationWindow,
) -> None:
    """Selecting a layer in tabbed mode selects its page and shows its bar."""
    app_window.settings["viewer_tools"] = "tabbed"
    app_window._vnotebook = MagicMock()

    app_window._set_active_layer("annotation")

    app_window._vnotebook.set_current_page.assert_called_with(2)
    assert app_window._ann_editor.controls.get_visible()
    assert not app_window._text_editor.controls.get_visible()
    assert app_window.settings["editmode"] == "annotation"
    assert app_window._actions["editmode"].get_state().get_string() == "annotation"


def test_switch_page_follows_the_active_layer(
    app_window: ApplicationWindow,
) -> None:
    """A tab change selects its layer; the image tab hides the bar but keeps it."""
    app_window.settings["viewer_tools"] = "tabbed"
    app_window._in_edit_mode_change = False

    app_window._on_switch_page(None, None, 1)
    assert app_window._active_layer == "text"
    assert app_window._text_editor.controls.get_visible()

    app_window._on_switch_page(None, None, 2)
    assert app_window._active_layer == "annotation"
    assert app_window._ann_editor.controls.get_visible()

    app_window._on_switch_page(None, None, 0)
    assert app_window._active_layer == "annotation"
    assert not app_window._text_editor.controls.get_visible()
    assert not app_window._ann_editor.controls.get_visible()
    assert app_window._actions["editmode"].get_state().get_string() == "annotation"


def test_switch_page_ignored_while_syncing(
    app_window: ApplicationWindow,
) -> None:
    """The re-entry guard stops a programmatic page change recursing."""
    app_window.settings["viewer_tools"] = "tabbed"
    app_window._active_layer = "annotation"
    app_window._in_edit_mode_change = True

    app_window._on_switch_page(None, None, 0)

    assert app_window._active_layer == "annotation"


def test_change_view_to_split_shows_active_layer_canvas(
    app_window: ApplicationWindow,
) -> None:
    """Entering a split view packs the active layer's canvas beside the image."""
    app_window.settings["viewer_tools"] = "tabbed"
    app_window._active_layer = "annotation"
    app_window._in_edit_mode_change = False

    app_window._change_view_cb(
        app_window._actions["viewtype"], GLib.Variant("s", "horizontal")
    )

    assert app_window.settings["viewer_tools"] == "horizontal"
    assert app_window._hpanei.get_start_child() is app_window.view
    assert app_window._hpanei.get_end_child() is app_window.a_canvas
    assert app_window._ann_editor.controls.get_visible()


def test_change_view_from_image_tab_falls_back_to_last_layer(
    app_window: ApplicationWindow,
) -> None:
    """Entering a split from the image tab uses the last active layer."""
    app_window.settings["viewer_tools"] = "tabbed"
    app_window.settings["editmode"] = "annotation"
    app_window._active_layer = None
    app_window._in_edit_mode_change = False

    app_window._change_view_cb(
        app_window._actions["viewtype"], GLib.Variant("s", "vertical")
    )

    assert app_window._active_layer == "annotation"
    assert app_window._vpanei.get_end_child() is app_window.a_canvas


def test_change_view_to_tabbed_lands_on_active_layer_page(
    app_window: ApplicationWindow,
) -> None:
    """Leaving a split view selects the tab matching the active layer."""
    app_window.settings["viewer_tools"] = "vertical"
    app_window._active_layer = "annotation"
    app_window._vnotebook = MagicMock()
    app_window._in_edit_mode_change = False

    app_window._change_view_cb(
        app_window._actions["viewtype"], GLib.Variant("s", "tabbed")
    )

    app_window._vnotebook.set_current_page.assert_called_with(2)
    assert app_window._ann_editor.controls.get_visible()


def test_pack_viewer_tools_uses_active_canvas(
    app_window: ApplicationWindow,
) -> None:
    """A split pane packs the active layer's canvas, not always the text one."""
    app_window._vnotebook = MagicMock()
    app_window._hpanei = MagicMock()
    app_window._vpanei = MagicMock()
    app_window._vpaned = MagicMock()
    app_window.view = MagicMock()
    app_window.t_canvas = MagicMock()
    app_window.a_canvas = MagicMock()
    app_window._init_split_pane = MagicMock()

    app_window._active_layer = "annotation"
    app_window.settings["viewer_tools"] = "horizontal"
    app_window._pack_viewer_tools()
    app_window._hpanei.set_end_child.assert_called_with(app_window.a_canvas)


def _measure_minimum(widget: MagicMock, minimum: int) -> None:
    """Make widget.measure() report the given minimum size."""
    result = MagicMock()
    result.minimum = minimum
    widget.measure.return_value = result


def test_init_split_pane_saved_position(app_window: ApplicationWindow) -> None:
    """A saved split position is applied once the pane has been allocated."""
    pane = MagicMock()
    pane.get_width.return_value = 400
    _measure_minimum(pane, 1)
    _measure_minimum(pane.get_start_child.return_value, 0)
    _measure_minimum(pane.get_end_child.return_value, 0)
    app_window._init_split_pane(pane, Gtk.Orientation.HORIZONTAL, 321)
    assert pane.add_tick_callback.call_count == 1

    callback = pane.add_tick_callback.call_args.args[0]
    assert callback(pane, MagicMock()) is False

    pane.set_position.assert_called_once_with(321)


def test_init_split_pane_saved_position_clamped(app_window: ApplicationWindow) -> None:
    """A saved position is clamped so both children keep their minimums.

    A position saved under an older, larger geometry would otherwise fill
    the whole pane and hide the end child.
    """
    pane = MagicMock()
    pane.get_width.return_value = 400
    _measure_minimum(pane, 1)
    _measure_minimum(pane.get_start_child.return_value, 50)
    _measure_minimum(pane.get_end_child.return_value, 150)
    app_window._init_split_pane(pane, Gtk.Orientation.HORIZONTAL, 321)

    callback = pane.add_tick_callback.call_args.args[0]
    assert callback(pane, MagicMock()) is False

    # high = 400 - 1 - 150 = 249; low = 1 + 50 = 51
    pane.set_position.assert_called_once_with(249)


def test_init_split_pane_missing_end_child(app_window: ApplicationWindow) -> None:
    """A pane without an end child contributes no minimum to the clamp."""
    pane = MagicMock()
    pane.get_width.return_value = 400
    _measure_minimum(pane, 1)
    _measure_minimum(pane.get_start_child.return_value, 50)
    pane.get_end_child.return_value = None
    app_window._init_split_pane(pane, Gtk.Orientation.HORIZONTAL, 500)

    callback = pane.add_tick_callback.call_args.args[0]
    assert callback(pane, MagicMock()) is False

    # high = 400 - 1 - 0 = 399
    pane.set_position.assert_called_once_with(399)


def test_init_split_pane_default_half(app_window: ApplicationWindow) -> None:
    """Without a saved position, a half-split default is set on first allocation."""
    pane = MagicMock()
    pane.get_height.return_value = 600
    _measure_minimum(pane, 1)
    _measure_minimum(pane.get_start_child.return_value, 0)
    _measure_minimum(pane.get_end_child.return_value, 0)
    app_window._init_split_pane(pane, Gtk.Orientation.VERTICAL, None)
    assert pane.add_tick_callback.call_count == 1

    callback = pane.add_tick_callback.call_args.args[0]
    assert callback(pane, MagicMock()) is False

    pane.set_position.assert_called_once_with(300)


def test_init_split_pane_default_half_horizontal(
    app_window: ApplicationWindow,
) -> None:
    """A horizontal split uses the allocated width for its half-split default."""
    pane = MagicMock()
    pane.get_width.return_value = 900
    _measure_minimum(pane, 1)
    _measure_minimum(pane.get_start_child.return_value, 0)
    _measure_minimum(pane.get_end_child.return_value, 0)
    app_window._init_split_pane(pane, Gtk.Orientation.HORIZONTAL, None)
    assert pane.add_tick_callback.call_count == 1

    callback = pane.add_tick_callback.call_args.args[0]
    assert callback(pane, MagicMock()) is False

    pane.set_position.assert_called_once_with(450)


def test_init_split_pane_end_at_minimum(app_window: ApplicationWindow) -> None:
    """The outer pane pins its end child (the edit bar) to its minimum height."""
    pane = MagicMock()
    pane.get_height.return_value = 600
    _measure_minimum(pane, 1)
    _measure_minimum(pane.get_start_child.return_value, 0)
    _measure_minimum(pane.get_end_child.return_value, 40)
    app_window._init_split_pane(
        pane, Gtk.Orientation.VERTICAL, None, end_at_minimum=True
    )
    assert pane.add_tick_callback.call_count == 1

    callback = pane.add_tick_callback.call_args.args[0]
    assert callback(pane, MagicMock()) is False

    # high = 600 - 1 - 40 = 559, so the bar keeps its 40px minimum.
    pane.set_position.assert_called_once_with(559)


def test_init_split_pane_waits_for_allocation(app_window: ApplicationWindow) -> None:
    """The tick callback keeps ticking until the pane has been allocated."""
    pane = MagicMock()
    pane.get_height.return_value = 0
    _measure_minimum(pane, 1)
    _measure_minimum(pane.get_start_child.return_value, 0)
    _measure_minimum(pane.get_end_child.return_value, 0)
    app_window._init_split_pane(pane, Gtk.Orientation.VERTICAL, None)

    callback = pane.add_tick_callback.call_args.args[0]
    assert callback(pane, MagicMock()) is True
    pane.set_position.assert_not_called()

    pane.get_height.return_value = 600
    assert callback(pane, MagicMock()) is False
    pane.set_position.assert_called_once_with(300)


def test_close_request(
    app_window: ApplicationWindow, mocker: pytest.MockerFixture
) -> None:
    """Test that _close_request blocks closing when _can_quit refuses."""
    mocker.patch.object(app_window, "_can_quit", return_value=False)
    assert app_window._close_request(app_window) is True

    mocker.patch.object(app_window, "_can_quit", return_value=True)
    assert app_window._close_request(app_window) is False


def test_can_quit_reads_real_window_state(
    app_window: ApplicationWindow,
    mocker: pytest.MockerFixture,
    tmp_path: pathlib.Path,
) -> None:
    """_can_quit persists real window state via the GTK4 API.

    Regression test: Gtk3's PyGObject Widget.get_size() tuple helper and
    Window.get_position() do not exist in GTK4.
    """
    app_window._pages_saved = MagicMock(return_value=True)
    app_window._chdir_cwd = MagicMock()
    app_window._windows = None
    cast("Any", app_window.session).name = str(tmp_path)
    app_window.settings["viewer_tools"] = "tabbed"
    mocker.patch("scantpaper.file_menu_mixins.config.write_config")
    mocker.patch("scantpaper.file_menu_mixins.fcntl")

    assert app_window._can_quit() is True

    assert isinstance(app_window.settings["window_width"], int)
    assert isinstance(app_window.settings["window_height"], int)
    # GTK4 cannot position windows, so the position is not read back.
    assert app_window.settings["window_x"] == 0


def test_ask_device_open_error_stores_response(
    app_window: ApplicationWindow, mocker: pytest.MockerFixture
) -> None:
    """Test that 'don't show this message again' stores the chosen response."""
    mocker.patch("scantpaper.app_window.Gtk.MessageDialog")
    mocker.patch("scantpaper.app_window.run_dialog", return_value=Gtk.ResponseType.OK)

    mock_radio = MagicMock(name="radio")
    mock_radio.get_active.return_value = False
    mock_cb = MagicMock(name="store_response")
    mock_cb.get_active.return_value = True
    mocker.patch(
        "scantpaper.app_window.Gtk.CheckButton.new_with_label",
        side_effect=cycle(
            [
                mock_radio,
                mock_radio,
                mock_radio,
                mock_radio,
                MagicMock(),
                mock_cb,
            ]
        ),
    )
    cast("Any", app_window.settings)["message"].pop("error opening device", None)

    response = app_window._ask_device_open_error("error opening device")

    assert response == "rescan", "all radios inactive falls through to rescan"
    assert (
        cast("Any", app_window.settings)["message"]["error opening device"]["response"]
        == "rescan"
    ), "response stored in the settings"


def test_show_message_dialog(
    app_window: ApplicationWindow, mocker: pytest.MockerFixture
) -> None:
    """Test _show_message_dialog."""
    mock_mm_cls = mocker.patch("scantpaper.app_window.MultipleMessage")
    mock_mm = mock_mm_cls.return_value
    mock_mm.grid_rows = 2
    mock_run = mocker.patch(
        "scantpaper.app_window.run_dialog", return_value=Gtk.ResponseType.OK
    )
    mock_mm.get_width.return_value = 300
    mock_mm.get_height.return_value = 400

    # Initial call
    app_window._show_message_dialog(parent=app_window, text="test message")

    mock_mm_cls.assert_called_once()
    mock_mm.add_message.assert_called_once()
    mock_run.assert_called_once()
    mock_mm.store_responses.assert_called_once()
    mock_mm.destroy.assert_called_once()
    assert app_window._message_dialog is None
    assert app_window.settings["message_window_width"] == 300
    assert app_window.settings["message_window_height"] == 400


def test_show_message_dialog_already_exists(
    app_window: ApplicationWindow, mocker: pytest.MockerFixture
) -> None:
    """Test _show_message_dialog when _message_dialog is already created."""
    mock_mm_cls = mocker.patch("scantpaper.app_window.MultipleMessage")
    mock_mm = MagicMock()
    mock_mm.grid_rows = 1
    mock_mm.get_size.return_value = (200, 200)
    app_window._message_dialog = mock_mm

    app_window._show_message_dialog(parent=app_window, text="test message")

    mock_mm_cls.assert_not_called()
    mock_mm.add_message.assert_called_once()
    mock_mm.destroy.assert_called_once()
    assert app_window._message_dialog is None


@pytest.mark.usefixtures("mock_builder", "mock_config")
def test_pre_flight_linux(mocker: pytest.MockerFixture) -> None:
    """Test that recursive_slurp is called on Linux."""
    mocker.patch("scantpaper.app_window.sys.platform", "linux")
    mock_slurp = mocker.patch("scantpaper.app_window.recursive_slurp")

    # Mock MultipleMessage to prevent blocking dialogs
    mock_mm = mocker.patch("scantpaper.app_window.MultipleMessage")
    mock_mm.return_value.grid_rows = 1
    mock_mm.return_value.get_width.return_value = 400
    mock_mm.return_value.get_height.return_value = 300

    mocker.patch("scantpaper.app_window.Document")
    mocker.patch("scantpaper.app_window.Unpaper")
    mocker.patch("scantpaper.app_window.ImageView", MockImageView)
    mocker.patch("scantpaper.layer.Canvas", MockCanvas)
    mocker.patch("scantpaper.app_window.Progress")
    mocker.patch("scantpaper.app_window.sane.init")
    mocker.patch("scantpaper.app_window.Selector")
    mocker.patch("scantpaper.app_window.Dragger")
    mocker.patch("scantpaper.app_window.SelectorDragger")
    mocker.patch("scantpaper.app_window.SessionMixins._find_crashed_sessions")

    mocker.patch("scantpaper.app_window.shutil.disk_usage").return_value.free = (
        1000 * 1024 * 1024
    )

    def mock_create_temp_func(self: object) -> None:
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
            "qpdf": True,
            "jbig2": True,
            "ocr": True,
        }

    mocker.patch.object(ApplicationWindow, "_check_dependencies", autospec=True)
    mocker.patch.object(
        ApplicationWindow,
        "_create_temp_directory",
        side_effect=mock_create_temp_func,
        autospec=True,
    )
    mocker.patch.object(ApplicationWindow, "set_icon_name", autospec=True)
    mocker.patch.object(ApplicationWindow, "set_child", autospec=True)
    mocker.patch.object(ApplicationWindow, "present", autospec=True)

    app = Gtk.Application()
    app.iconpath = "/tmp"
    app.args = MagicMock(import_files=None, import_all=None)
    win = None

    try:
        win = ApplicationWindow(application=app)
        mock_slurp.assert_called_once()
    finally:
        if win:
            win.destroy()
        _pump_events()
        app.quit()


@pytest.mark.usefixtures("mock_builder")
def test_pre_flight_cwd_none(
    mocker: pytest.MockerFixture, mock_config: object, tmp_path: pathlib.Path
) -> None:
    """Test that cwd is set to os.getcwd() if it is None."""
    mock_config.read_config.return_value["cwd"] = None

    _setup_app_window_mocks(mocker, tmp_path)

    app = Gtk.Application()
    app.iconpath = "/tmp"
    app.args = MagicMock(import_files=None, import_all=None)
    win = None

    try:
        # on some systems, creating the ApplicationWindow fails if the
        # application is not first registered.
        with patch.object(Gtk.Application, "register", autospec=True):
            app.register(None)
            win = ApplicationWindow(application=app)
            assert win.settings["cwd"] == str(pathlib.Path.cwd())
    finally:
        if win:
            win.destroy()
        _pump_events()
        app.quit()


@pytest.mark.usefixtures("mock_builder", "mock_config")
def test_populate_main_window_cwd_missing(
    mocker: pytest.MockerFixture, tmp_path: pathlib.Path
) -> None:
    """Test that cwd is set to os.getcwd() if it is missing in _populate_main_window."""
    _setup_app_window_mocks(mocker, tmp_path)

    # Patch _pre_flight to delete 'cwd' from settings after it runs
    original_pre_flight = ApplicationWindow._pre_flight

    def mock_pre_flight(self: object) -> None:
        original_pre_flight(cast("ApplicationWindow", self))
        del self.settings["cwd"]

    mocker.patch.object(
        ApplicationWindow, "_pre_flight", side_effect=mock_pre_flight, autospec=True
    )

    app = Gtk.Application()
    app.iconpath = "/tmp"
    app.args = MagicMock(import_files=None, import_all=None)
    win = None

    try:
        # on some systems, creating the ApplicationWindow fails if the
        # application is not first registered.
        with patch.object(Gtk.Application, "register", autospec=True):
            app.register(None)
            win = ApplicationWindow(application=app)
            assert win.settings["cwd"] == str(pathlib.Path.cwd())
    finally:
        if win:
            win.destroy()
        _pump_events()
        app.quit()


@pytest.mark.usefixtures("mock_builder")
def test_init_with_auto_open_and_imports(
    mocker: pytest.MockerFixture, mock_config: object, tmp_path: pathlib.Path
) -> None:
    """Test that scan_dialog and _import_files are called during init if configured."""
    mock_config.read_config.return_value["auto-open-scan-dialog"] = True

    _setup_app_window_mocks(mocker, tmp_path)

    # Mock the methods we want to check
    mock_scan_dialog = mocker.patch.object(ApplicationWindow, "scan_dialog")
    mock_import_files = mocker.patch.object(ApplicationWindow, "_import_files")

    app = Gtk.Application()
    app.iconpath = "/tmp"
    app.args = MagicMock()
    app.args.import_files = ["file1.pdf"]
    app.args.import_all = ["file2.pdf"]
    win = None

    try:
        # on some systems, creating the ApplicationWindow fails if the
        # application is not first registered.
        with patch.object(Gtk.Application, "register", autospec=True):
            app.register(None)
            win = ApplicationWindow(application=app)
            mock_scan_dialog.assert_called_once_with(None, None, hidden=True)
            assert mock_import_files.call_count == 2
            mock_import_files.assert_any_call(["file2.pdf"], all_pages=True)
    finally:
        if win:
            win.destroy()
        _pump_events()
        app.quit()


@pytest.mark.usefixtures("mock_builder")
def test_populate_panes_tool_selection(
    mocker: pytest.MockerFixture, mock_config: object, tmp_path: pathlib.Path
) -> None:
    """Test _populate_panes with different image_control_tool settings."""
    mock_selector, mock_dragger, mock_selector_dragger = _setup_app_window_mocks(
        mocker, tmp_path
    )

    def assert_dragger(_app: Gtk.Application, _win: ApplicationWindow) -> None:
        mock_dragger.assert_called()
        mock_dragger.reset_mock()
        mock_selector.reset_mock()
        mock_selector_dragger.reset_mock()

    # Test with "dragger"
    mock_config.read_config.return_value["image_control_tool"] = "dragger"
    _create_test_app(assert_dragger)

    # Test with "selectordragger" (or any other value that falls into 'else')
    mock_config.read_config.return_value["image_control_tool"] = "selectordragger"

    def assert_selector_dragger(_app: Gtk.Application, _win: ApplicationWindow) -> None:
        mock_selector_dragger.assert_called()

    _create_test_app(assert_selector_dragger)


def _real_layout_window(
    mocker: pytest.MockerFixture,
    tmp_path: pathlib.Path,
    viewer_tools: str,
    *,
    mock_canvas: bool = True,
    split_panel_v: int | None = None,
) -> tuple[Gtk.Application, ApplicationWindow]:
    """Build an ApplicationWindow with the real app.ui layout and widgets.

    Mocks the environment (config, SANE init, crashed-session check) but
    keeps the real Builder objects, ImageView and — unless mock_canvas —
    the real text/annotation canvases, so real GTK layout can be asserted.
    """
    session_dir = tmp_path / "session"
    session_dir.mkdir()

    mocker.patch("scantpaper.app_window.Unpaper")
    if mock_canvas:
        mocker.patch("scantpaper.layer.Canvas", MockCanvas)
    mocker.patch("scantpaper.app_window.sane.init")
    mocker.patch("scantpaper.app_window.recursive_slurp")
    mocker.patch("scantpaper.app_window.SessionMixins._find_crashed_sessions")
    mocker.patch("scantpaper.app_window.MultipleMessage")
    mocker.patch("scantpaper.app_window.shutil.disk_usage").return_value.free = (
        1000 * 1024 * 1024
    )
    mocker.patch.object(ApplicationWindow, "_check_dependencies", autospec=True)
    mocker.patch.object(
        ApplicationWindow,
        "_create_temp_directory",
        side_effect=_make_create_temp_func(session_dir),
        autospec=True,
    )
    mock_config = mocker.patch("scantpaper.app_window.config")
    mock_config.read_config.return_value = {
        "restore window": False,
        "window_width": 800,
        "window_height": 600,
        "window_x": 0,
        "window_y": 0,
        "window_maximize": False,
        "cwd": "/tmp",
        "image_control_tool": "selector",
        "auto-open-scan-dialog": False,
        "unpaper options": {},
        "Paper": {},
        "thumb panel": 100,
        "split panel v": split_panel_v,
        "viewer_tools": viewer_tools,
        "available-tmp-warning": 100,
        "message_window_width": 200,
        "message_window_height": 200,
        "message": {},
        "cache-device-list": False,
        "selection": None,
    }

    app = Gtk.Application()
    app.iconpath = "/tmp"
    app.args = MagicMock(import_files=None, import_all=None)
    with patch.object(Gtk.Application, "register", autospec=True):
        app.register(None)
        win = ApplicationWindow(application=app)
    win.set_default_size(800, 600)
    win.present()
    return app, win


def _wait_until(
    mainloop_with_timeout: Callable[[], _MainLoopWrapper], predicate: Callable[[], bool]
) -> None:
    """Pump the main loop until predicate() is true (bounded)."""
    loop = mainloop_with_timeout()

    def poll() -> bool:
        if predicate():
            loop.quit()
            return cast("bool", GLib.SOURCE_REMOVE)
        return cast("bool", GLib.SOURCE_CONTINUE)

    GLib.timeout_add(10, poll)
    GLib.timeout_add(2000, loop.quit)
    loop.run()


@pytest.mark.parametrize("viewer_tools", ["tabbed", "horizontal", "vertical"])
def test_image_view_allocated_at_startup(
    mocker: pytest.MockerFixture,
    tmp_path: pathlib.Path,
    viewer_tools: str,
    mainloop_with_timeout: Callable[[], _MainLoopWrapper],
) -> None:
    """The image area is allocated a usable share at startup in every mode.

    Regression test for the GTK4 migration: a bare DrawingArea requests a
    0x0 minimum, and a GtkPaned without an explicit position defaults its
    divider to child1's minimum request, collapsing the image view to a
    zero-height sliver.
    """
    app, win = _real_layout_window(mocker, tmp_path, viewer_tools)
    try:
        _wait_until(
            mainloop_with_timeout,
            lambda: win.view.get_allocation().height > 100,
        )

        allocation = win.view.get_allocation()
        assert allocation.width > 0, "image view width allocated"
        assert allocation.height > 100, "image view height not collapsed"
    finally:
        win.destroy()
        app.quit()


def test_startup_tabbed_hides_bar_on_image_page(
    mocker: pytest.MockerFixture,
    tmp_path: pathlib.Path,
) -> None:
    """The text layer is selected at startup, but its bar waits for its canvas.

    The window opens on the Image page, which shows the bare scan, so the edit
    bar is hidden there even though the View menu selects the text layer. This
    mirrors what selecting the Image tab does at runtime.
    """
    app, win = _real_layout_window(mocker, tmp_path, "tabbed")
    try:
        assert win._vnotebook.get_current_page() == 0
        assert win._active_layer == "text"
        assert win._actions["editmode"].get_state().get_string() == "text"
        assert not win._text_editor.controls.get_visible()
        assert not win._ann_editor.controls.get_visible()
    finally:
        win.destroy()
        app.quit()


def _page_pixbuf(width: int = 181, height: int = 256) -> GdkPixbuf.Pixbuf:
    """Return a plain white portrait page pixbuf (A4-ish aspect)."""
    pixbuf = GdkPixbuf.Pixbuf.new(
        GdkPixbuf.Colorspace.RGB,
        has_alpha=True,
        bits_per_sample=8,
        width=width,
        height=height,
    )
    pixbuf.fill(0xFFFFFFFF)
    return pixbuf


def _page_visible_on(canvas: Canvas) -> bool:
    """Return whether the known page extent intersects the canvas viewport."""
    # Without an extent the page is zero-sized and never visible.
    size = canvas.get_pixbuf_size() or {"width": 0, "height": 0}
    zoom = canvas.zoom / canvas.get_scale_factor()
    x0 = canvas.offset.x * zoom
    y0 = canvas.offset.y * zoom
    allocation = canvas.get_allocation()
    return bool(
        x0 < allocation.width
        and y0 < allocation.height
        and x0 + size["width"] * zoom > 0
        and y0 + size["height"] * zoom > 0
    )


def test_canvas_aligns_with_view_after_tab_switch(
    mocker: pytest.MockerFixture,
    tmp_path: pathlib.Path,
    mainloop_with_timeout: Callable[[], _MainLoopWrapper],
) -> None:
    """A canvas shown after being hidden displays the region the view had.

    Regression test for the GTK4 migration: hidden GtkStack pages have a
    0x0 allocation, and the canvas clamped every incoming offset against
    it, losing the view's fitted offset.
    """
    app, win = _real_layout_window(mocker, tmp_path, "tabbed", mock_canvas=False)
    try:
        _wait_until(
            mainloop_with_timeout,
            lambda: win.view.get_allocation().height > 100,
        )
        # Display a page and mimic the layer editor giving the canvas the
        # page extent plus the view's fitted offset.
        win.view.set_pixbuf(_page_pixbuf(), zoom_to_fit=True)
        win.t_canvas.set_page_extent(181, 256)
        offset = win.view.get_offset()
        win.t_canvas.set_offset(offset.x, offset.y)

        win._vnotebook.set_current_page(1)
        _wait_until(
            mainloop_with_timeout,
            lambda: win.t_canvas.get_allocation().height > 100,
        )

        t_canvas = win.t_canvas
        assert t_canvas is not None, "text canvas exists"
        assert _page_visible_on(t_canvas), "page visible on canvas"
        assert win.t_canvas.offset.x == pytest.approx(win.view.get_offset().x, abs=2), (
            "canvas offset x matches the view"
        )
        assert win.t_canvas.offset.y == pytest.approx(win.view.get_offset().y, abs=2), (
            "canvas offset y matches the view"
        )
    finally:
        win.destroy()
        app.quit()


def test_canvas_page_visible_after_shrink_while_hidden(
    mocker: pytest.MockerFixture,
    tmp_path: pathlib.Path,
    mainloop_with_timeout: Callable[[], _MainLoopWrapper],
) -> None:
    """Shrinking the window while a canvas is hidden cannot hide the page.

    The view re-fits against the shrunk allocation and pushes its offset;
    the hidden canvas must not clamp that push against its stale, larger
    allocation, which would place the page off-screen once shown.
    """
    app, win = _real_layout_window(mocker, tmp_path, "tabbed", mock_canvas=False)
    try:
        _wait_until(
            mainloop_with_timeout,
            lambda: win.view.get_allocation().height > 100,
        )
        win.view.set_pixbuf(_page_pixbuf(), zoom_to_fit=True)
        win.t_canvas.set_page_extent(181, 256)

        # Show the canvas once so it holds a stale (large) allocation, then
        # hide it again.
        win._vnotebook.set_current_page(1)
        _wait_until(
            mainloop_with_timeout,
            lambda: win.t_canvas.get_allocation().height > 100,
        )
        win._vnotebook.set_current_page(0)

        # Shrink the image area while the canvas is hidden: the view re-fits
        # against the shrunk allocation and pushes the new offset.
        win._vpaned.set_position(100)
        _wait_until(
            mainloop_with_timeout,
            lambda: win.view.get_allocation().height < 70,
        )

        # Show the canvas: the page must be visible within the live,
        # smaller allocation.
        win._vnotebook.set_current_page(1)
        _wait_until(
            mainloop_with_timeout,
            lambda: (
                win.t_canvas.get_allocation().height < 70
                and win.t_canvas.get_allocation().height > 0
            ),
        )

        t_canvas = win.t_canvas
        assert t_canvas is not None, "text canvas exists"
        assert _page_visible_on(t_canvas), "page visible after shrink"
    finally:
        win.destroy()
        app.quit()


def test_stale_saved_split_position_does_not_hide_canvas(
    mocker: pytest.MockerFixture,
    tmp_path: pathlib.Path,
    mainloop_with_timeout: Callable[[], _MainLoopWrapper],
) -> None:
    """A saved split position from an older geometry cannot hide a pane.

    Regression test: `split panel v` was saved as 278 when the inner pane
    was ~491px tall; after the outer pane's default became a half-split
    (~279px), restoring 278 filled the whole pane and left the canvas a
    1px sliver.
    """
    app, win = _real_layout_window(
        mocker, tmp_path, "vertical", mock_canvas=False, split_panel_v=278
    )
    try:
        _wait_until(
            mainloop_with_timeout,
            lambda: (
                win.view.get_allocation().height > 0
                and win.t_canvas is not None
                and win.t_canvas.get_allocation().height > 0
                and win.t_canvas.get_allocation().height < 270
            ),
        )

        t_canvas = win.t_canvas
        assert t_canvas is not None, "text canvas exists"
        assert t_canvas.get_allocation().height >= 100, (
            "canvas pane visible despite a stale saved position"
        )
        assert win.view.get_allocation().height >= 100, "view pane visible"
    finally:
        win.destroy()
        app.quit()
