"""Tests for the main-window UI definition (app.ui)."""

from __future__ import annotations

import pathlib
from typing import cast

import gi
import pytest

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, Gtk  # noqa: E402

APP_UI = pathlib.Path(__file__).parent.parent / "app.ui"


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
