"""Tests for the main-window UI definition (app.ui)."""

from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING, cast

import gi
import pytest

from scantpaper.app_window import ApplicationWindow
from scantpaper.imageview import ImageView

if TYPE_CHECKING:
    from collections.abc import Callable

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gio, GLib, Gtk  # noqa: E402

APP_UI = pathlib.Path(__file__).parent.parent / "app.ui"


def _pump_gtk(iterations: int = 80) -> None:
    """Iterate the main context until GTK settles."""
    context = GLib.MainContext.default()
    for _ in range(iterations):
        context.iteration(may_block=False)


def _pump_until(predicate: Callable[[], bool], iterations: int = 600) -> bool:
    """Iterate the main context until predicate() holds (or the cap is hit).

    A fixed iteration budget is unreliable in a long test session, where
    the display can be busy or a window needs many extra passes to become
    properly mapped before its popup surface can appear. Pumps on every
    pass so each iteration always lets GTK make progress.
    """
    context = GLib.MainContext.default()
    result = False
    for _ in range(iterations):
        context.iteration(may_block=False)
        if predicate():
            result = True
            break
    return result


@pytest.fixture
def ui_builder() -> Gtk.Builder:
    """Return a Gtk.Builder loaded from the real app.ui."""
    builder = Gtk.Builder()
    builder.add_from_file(str(APP_UI))
    return builder


def _top_level_labels(model: Gio.MenuModel) -> list[str]:
    labels: list[str] = []
    for i in range(model.get_n_items()):
        value = model.get_item_attribute_value(i, Gio.MENU_ATTRIBUTE_LABEL, None)
        labels.append(cast("str", value.get_string()) if value is not None else "")
    return labels


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


def test_menubar_is_an_in_window_popover_menu_bar(ui_builder: Gtk.Builder) -> None:
    """The window presents the menus itself as a Gtk.PopoverMenuBar."""
    bar = ui_builder.get_object("menubar")
    assert isinstance(bar, Gtk.PopoverMenuBar), (
        "menus must be in-window, not exported for the desktop shell"
    )

    main_vbox = ui_builder.get_object("main_vbox")
    assert main_vbox.get_first_child() is bar, "menubar sits above the toolbar"
    assert bar.get_next_sibling() is ui_builder.get_object("toolbar")


def test_menubar_exposes_the_top_level_menus(ui_builder: Gtk.Builder) -> None:
    """The menu model keeps every top-level menu and its actions."""
    bar = cast("Gtk.PopoverMenuBar", ui_builder.get_object("menubar"))
    model = bar.get_menu_model()

    assert _top_level_labels(model) == [
        "_File",
        "_Edit",
        "_View",
        "_Tools",
        "_Help",
    ]

    # A representative item keeps its action: File -> New is win.new.
    file_menu = model.get_item_link(0, Gio.MENU_LINK_SUBMENU)
    assert file_menu is not None
    section = file_menu.get_item_link(0, Gio.MENU_LINK_SECTION)
    assert section is not None
    action = section.get_item_attribute_value(0, Gio.MENU_ATTRIBUTE_ACTION, None)
    assert action is not None
    assert action.get_string() == "win.new"


def test_file_menu_exposes_import_hocr(ui_builder: Gtk.Builder) -> None:
    """The File menu links the hOCR import action."""
    bar = cast("Gtk.PopoverMenuBar", ui_builder.get_object("menubar"))
    file_menu = bar.get_menu_model().get_item_link(0, Gio.MENU_LINK_SUBMENU)
    assert file_menu is not None
    section = file_menu.get_item_link(0, Gio.MENU_LINK_SECTION)
    assert section is not None

    actions = []
    for i in range(section.get_n_items()):
        value = section.get_item_attribute_value(i, Gio.MENU_ATTRIBUTE_ACTION, None)
        if value is not None:
            actions.append(value.get_string())

    assert "win.import-hocr" in actions


def test_view_menu_exposes_clear_image_selection(ui_builder: Gtk.Builder) -> None:
    """The View menu links the image-selection clear action."""
    bar = cast("Gtk.PopoverMenuBar", ui_builder.get_object("menubar"))
    view_menu = bar.get_menu_model().get_item_link(2, Gio.MENU_LINK_SUBMENU)
    assert view_menu is not None

    assert "win.clear-image-selection" in _menu_action_names(view_menu)


def test_toolbar_exposes_clear_image_selection(ui_builder: Gtk.Builder) -> None:
    """The clear action sits next to the selection tools on the toolbar."""
    button = cast("Gtk.Button", ui_builder.get_object("toolbutton_clear_selection"))
    assert isinstance(button, Gtk.Button)
    assert button.get_action_name() == "win.clear-image-selection"
    assert button.get_icon_name() == "edit-clear"
    assert button.get_tooltip_text() == "Clear image selection"

    selectordragger = ui_builder.get_object("toolbutton_selectordragger")
    assert button.get_prev_sibling() is selectordragger


class _MenuAnchorStub:
    """Bare handler object exposing the real right-click methods under test.

    The function attributes bind the production method bodies to this
    object so the popover anchoring can be exercised without constructing
    a full application window.
    """

    _handle_clicks = ApplicationWindow._handle_clicks
    _show_popover_at_pointer = ApplicationWindow._show_popover_at_pointer

    def __init__(self) -> None:
        """Initialise with plain containers instead of production state."""
        self.settings: dict[str, object] = {}
        self.detail_popup: Gtk.Popover | None = None
        self._thumb_popup: Gtk.Popover | None = None


def _popover_offset(popover: Gtk.Widget) -> tuple[float, float] | None:
    """Return the popover's position from the window's surface origin.

    A GtkPopover lives on its own popup surface. The X11 surface exposes
    get_position_x/y (the Gdk.Popup interface), which gives the popover's
    top-left relative to the parent surface (the window), so the anchoring
    can be asserted without drawing on non-project X tooling. Returns None
    while the popover is not mapped (e.g. not yet shown).
    """
    surface = popover.get_surface()
    if surface is None or not surface.get_mapped():
        return None
    # float() turns the unknown GDK return into a real float for the
    # checker; the concrete values are already floats at runtime.
    return float(surface.get_position_x()), float(surface.get_position_y())


def test_context_menu_anchors_at_the_pointer(ui_builder: Gtk.Builder) -> None:
    """The right-click popover opens at the pointer, not the window corner.

    GTK3's popup_at_pointer() anchored the menu at the cursor; the GTK4
    port showed a popover parented to the whole window with a bare
    popup(), which pinned it to the window's top-left corner. Driving the
    real handler with a real popover from app.ui, two right-clicks must
    land the menu at two different pointer positions, moving toward the
    clicks, instead of staying put at the corner.
    """
    if Gdk.Display.get_default() is None:
        # No stubs for the current pytest; the installed one resolves skip
        # with no arguments.
        pytest.skip("requires a display")  # ty: ignore[too-many-positional-arguments]

    view = ImageView()
    view.set_size_request(700, 500)
    window = Gtk.Window(title="context-menu-anchor")
    window.set_child(view)
    stub = _MenuAnchorStub()
    stub.detail_popup = ui_builder.get_object("detail_popup")
    stub._thumb_popup = ui_builder.get_object("thumb_popup")
    # Production parents the popovers to the window once at startup
    # (_connect_popover_signals) before any right-click can show them.
    stub.detail_popup.set_parent(window)
    stub._thumb_popup.set_parent(window)
    # Before any right-click the popover is unmapped; this exercises the
    # not-yet-shown branch of the offset helper.
    detail = stub.detail_popup
    assert detail is not None
    assert _popover_offset(detail) is None
    # The stub is deliberately not an ApplicationWindow (it only needs the
    # two bound methods), so the receiver type does not match.
    ApplicationWindow._add_secondary_click_controller(
        stub,  # ty: ignore[invalid-argument-type]
        view,
    )
    window.present()
    # Give the window a chance to map before right-clicking; a popover can
    # only appear on a realized, mapped parent window.
    assert _pump_until(
        lambda: window.get_surface() is not None and window.get_surface().get_mapped(),
        iterations=600,
    ), "window is mapped before the first right-click"

    gesture = next(
        controller
        for controller in view.observe_controllers()
        if isinstance(controller, Gtk.GestureClick)
        and controller.props.button == Gdk.BUTTON_SECONDARY
    )

    def offset_after_click(x: int, y: int) -> tuple[float, float]:
        gesture.emit("pressed", 1, float(x), float(y))
        assert stub.detail_popup is not None
        assert _pump_until(lambda: _popover_offset(stub.detail_popup) is not None), (
            "detail popover is shown and mapped"
        )
        offset = _popover_offset(stub.detail_popup)
        assert offset is not None
        stub.detail_popup.popdown()
        _pump_gtk()
        return offset

    first = offset_after_click(200, 150)
    second = offset_after_click(420, 280)

    # The menu follows a right-click toward the lower-right instead of
    # staying pinned to the window's top-left corner.
    assert second[0] > first[0] + 50, "menu moves right with the pointer"
    assert second[1] > first[1] + 50, "menu moves down with the pointer"

    # Hiding (rather than destroying) the window avoids a GTK crash that a
    # later window construction in the same process hits when the parent is
    # destroyed after a popover was mapped: the orphaned popup surface's
    # teardown corrupts the CSS/render state. The hidden window is unmapped;
    # no test enumerates toplevels, so it cannot interfere.
    window.hide()
    _pump_gtk()
