"""test dialog."""

import gi

from scantpaper.const import DIALOG_ROW_SPACING
from scantpaper.dialog.crop import Crop
from scantpaper.loop_helpers import safe_mainloop

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import (  # noqa: E402
    Gdk,
    Gtk,
)


def test_1() -> None:
    """Test dialog."""
    dialog = Crop(transient_for=Gtk.Window(), page_width=100, page_height=100)
    assert isinstance(dialog, Crop), "Created dialog"
    assert dialog.page_width == 100, "default page-width"
    assert dialog.page_height == 100, "default page-height"

    flag = False
    mlp = safe_mainloop(2000)

    def on_changed_selection(*_: object) -> None:
        nonlocal flag
        flag = True
        mlp.quit()

    dialog.connect("changed-selection", on_changed_selection)
    selection = Gdk.Rectangle()
    selection.x, selection.y, selection.width, selection.height = 10, 10, 10, 10
    dialog.selection = selection
    mlp.run()
    assert flag, "updating selection emits signal"
    assert dialog._sb_x.get_value() == 10, "updating selection changes spinbutton"

    content = dialog.get_content_area()
    grid = next(
        child
        for child in list(content.observe_children())
        if isinstance(child, Gtk.Grid)
    )
    row = grid.get_child_at(1, 0)
    assert row.get_spacing() == DIALOG_ROW_SPACING, "crop row widgets are spaced"


def test_coverage() -> None:
    """Test coverage for edge cases."""
    dialog = Crop(transient_for=Gtk.Window(), page_width=100, page_height=100)

    # Line 72: page_width.setter early return
    dialog.page_width = 100
    dialog.page_width = 100

    # Line 92: page_height.setter early return
    dialog.page_height = 100
    dialog.page_height = 100

    # Line 50: selection.setter early return
    rect = Gdk.Rectangle()
    rect.x, rect.y, rect.width, rect.height = 1, 1, 1, 1
    dialog.selection = rect
    dialog.selection = rect

    # Line 142: on_sb_selector_value_changed if self.selection is None
    dialog._selection = None
    # This should trigger on_sb_selector_value_changed which sets self.selection
    # We call it directly to hit line 142
    dialog.on_sb_selector_value_changed(dialog._sb_x, "x")
    assert dialog.selection is not None


def test_crop_selection_can_be_cleared() -> None:
    """Assigning None clears the dialog without dereferencing the rectangle."""
    dialog = Crop(transient_for=Gtk.Window(), page_width=100, page_height=100)
    rect = Gdk.Rectangle()
    rect.x, rect.y, rect.width, rect.height = 10, 20, 30, 40
    dialog.selection = rect

    changed = []
    dialog.connect("changed-selection", lambda _d, sel: changed.append(sel))
    dialog.selection = None

    assert dialog.selection is None
    assert changed == [None]
    assert [
        dialog._sb_x.get_value(),
        dialog._sb_y.get_value(),
        dialog._sb_width.get_value(),
        dialog._sb_height.get_value(),
    ] == [0, 0, 0, 0]

    # A page resize updates the spin ranges without a selection.
    dialog.page_width = 200
    dialog.page_height = 200


def test_crop_selector_with_existing_selection() -> None:
    """Test on_sb_selector_value_changed when selection already exists."""
    dialog = Crop(transient_for=Gtk.Window(), page_width=100, page_height=100)

    # Set an initial selection
    rect = Gdk.Rectangle()
    rect.x, rect.y, rect.width, rect.height = 10, 20, 30, 40
    dialog.selection = rect

    # Now change a spinbutton value — should copy existing selection attributes
    dialog._sb_x.set_value(50)
    dialog.on_sb_selector_value_changed(dialog._sb_x, "x")
    assert dialog.selection.x == 50
    assert dialog.selection.y == 20
    assert dialog.selection.width == 30
    assert dialog.selection.height == 40
