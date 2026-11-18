"""Paint-level test for the thumbnail display size."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import gi
import pytest

from scantpaper.app_window import _attach_thumbnail_css, drag_motion_callback
from scantpaper.const import THUMBNAIL
from scantpaper.document import Document

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

gi.require_version("Gtk", "4.0")
gi.require_version("Gsk", "4.0")
from gi.repository import (  # noqa: E402
    GLib,
    Gsk,
    Gtk,
)

SAFE_SNAPSHOT = tuple(map(int, gi.__version__.split(".")[:2])) >= (3, 46)


def _texture_nodes(node: Gsk.RenderNode) -> Iterator[Gsk.TextureNode]:
    """Yield the texture nodes in a render node tree."""
    if isinstance(node, Gsk.TextureNode):
        yield node
    if isinstance(node, Gsk.ContainerNode):
        for index in range(node.get_n_children()):
            child = node.get_child(index)
            if child is not None:
                yield from _texture_nodes(child)


def _wait_for(condition: Callable[[], bool], timeout_ms: int = 5000) -> None:
    """Run the mainloop until the condition holds or the timeout expires."""
    loop = GLib.MainLoop()
    GLib.timeout_add(timeout_ms, loop.quit)

    def check() -> bool:
        if condition():
            loop.quit()
            return cast("bool", GLib.SOURCE_REMOVE)
        return cast("bool", GLib.SOURCE_CONTINUE)

    GLib.idle_add(check)
    loop.run()


def _snapshot_render_tree(slist: Gtk.TreeView) -> Gsk.RenderNode:
    """Realize the thumbnail list in a mapped, allocated window and snapshot it."""
    win = Gtk.Window()
    win.set_child(slist)
    win.set_default_size(300, 400)
    win.present()
    _wait_for(
        lambda: win.get_mapped() and slist.get_allocated_width() > 1,
    )
    # let the frame clock run one paint cycle now that the widget is allocated
    _wait_for(lambda: False, timeout_ms=100)
    snapshot = Gtk.Snapshot.new()
    win.snapshot_child(slist, snapshot)
    node = snapshot.to_node()
    win.destroy()
    assert node is not None, "expected a render tree from the thumbnail list"
    return node


@pytest.fixture
def thumbnail_list(
    rose_png: str,
    temp_db: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> Document:
    """Return a document containing one generated thumbnail."""
    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [rose_png])
    return slist


def test_thumbnail_generates_at_expected_size(thumbnail_list: Document) -> None:
    """The stylesheet and generated pixbuf agree on the thumbnail size."""
    provider = _attach_thumbnail_css()
    assert provider is not None, "expected a CSS provider"
    assert f"-gtk-icon-size: {THUMBNAIL}px" in provider.to_string()
    pixbuf = thumbnail_list.data[0][1]
    assert pixbuf.get_width() == 100, "generated thumbnail width"
    assert pixbuf.get_height() == 65, "generated thumbnail height"


@pytest.mark.skipif(
    not SAFE_SNAPSHOT,
    reason="PyGObject 3.42 cannot marshal Gtk.Snapshot through snapshot_child",
)
def test_thumbnail_paints_at_generated_size(thumbnail_list: Document) -> None:
    """The thumbnail list paints a thumbnail at its generated size.

    GTK4's CellRendererPixbuf clamps its paint to the stylesheet's
    -gtk-icon-size; without the application's CSS override a 100x65
    thumbnail is painted at 16px high even though the cell is allocated
    100x65. The installed rule is asserted on every supported PyGObject;
    newer versions additionally inspect the render tree.
    """
    pixbuf = thumbnail_list.data[0][1]
    node = _snapshot_render_tree(thumbnail_list)
    bounds = [n.get_bounds() for n in _texture_nodes(node)]
    assert bounds, "expected a texture node in the thumbnail list render tree"
    painted = [(b.size.width, b.size.height) for b in bounds]
    assert any(
        abs(width - pixbuf.get_width()) <= 1 and abs(height - pixbuf.get_height()) <= 1
        for width, height in painted
    ), f"no thumbnail painted at {pixbuf.get_width()}x{pixbuf.get_height()}: {painted}"


def test_texture_nodes_walks_containers(mocker: pytest.MockerFixture) -> None:
    """Container traversal yields texture children and ignores empty slots."""
    texture = mocker.MagicMock(spec=Gsk.TextureNode)
    container = mocker.MagicMock(spec=Gsk.ContainerNode)
    container.get_n_children.return_value = 2
    container.get_child.side_effect = [texture, None]
    assert list(_texture_nodes(container)) == [texture]


def test_wait_for_stops_when_condition_holds() -> None:
    """The idle callback ends the loop as soon as the condition holds."""
    calls = 0

    def condition() -> bool:
        nonlocal calls
        calls += 1
        return calls == 3

    _wait_for(condition, timeout_ms=100)
    assert calls == 3


def test_wait_for_stops_on_timeout() -> None:
    """The timeout source ends the loop even when the condition never holds."""
    _wait_for(lambda: False, timeout_ms=1)


def _realize_and_paint(slist: Gtk.TreeView) -> Gsk.RenderNode:
    """Map ``slist`` in the app's nesting and paint it.

    Like _snapshot_render_tree, but puts the list inside a Gtk.ScrolledWindow
    (the app's layout, app_window.py _build_thumbnail_display) so
    drag_motion_callback's auto-scroll code can run, then forces the repaint
    of the realized tree — the exact frame that crashed the pre-fix build.
    """
    scroll = Gtk.ScrolledWindow()
    scroll.set_child(slist)
    win = Gtk.Window()
    win.set_child(scroll)
    win.set_default_size(300, 400)
    win.present()
    _wait_for(
        lambda: win.get_mapped() and slist.get_allocated_width() > 1,
    )
    # let the frame clock run one paint cycle now that the widget is allocated
    _wait_for(lambda: False, timeout_ms=100)
    snapshot = Gtk.Snapshot.new()
    scroll.snapshot_child(slist, snapshot)
    node = snapshot.to_node()
    win.destroy()
    assert node is not None, "expected a render tree from the thumbnail list"
    return node


@pytest.mark.skipif(
    not SAFE_SNAPSHOT,
    reason="PyGObject 3.42 cannot marshal Gtk.Snapshot through snapshot_child",
)
def test_drag_motion_does_not_arm_highlight_on_realized_tree(
    thumbnail_list: Document,
) -> None:
    """Display-backed regression: drag motion never arms the crashing highlight.

    The pre-fix build segfaulted natively when a custom-DnD tree armed
    GtkTreeView.set_drag_dest_row() and the next repaint drew the drop
    highlight through a NULL TreeViewDragInfo/cssnode (gtk_tree_view_bin_snapshot,
    gtktreeview.c:4849). Wire the app's motion path the way app_window does
    (slist.rows_drop_target "motion" -> drag_motion_callback), drive a motion
    over a realized tree, then force the repaint that used to crash: the
    process must survive and the armed drag-dest row must stay unset, because
    the drop index is computed by _on_drop_rows at drop time.

    Like the other display-backed tests in this module, it runs only under
    the suite's xvfb display (pytest-xvfb / CI) and realizes the widget
    through the Gtk.Snapshot machinery guarded by SAFE_SNAPSHOT.
    """
    slist = thumbnail_list
    slist.rows_drop_target.connect("motion", drag_motion_callback, slist)
    _realize_and_paint(slist)
    slist.rows_drop_target.emit("motion", 20, 30)
    _realize_and_paint(slist)  # repaint after motion: the former crash site
    path, _pos = slist.get_drag_dest_row()
    assert path is None, (
        "drag motion must not arm the native drop highlight (crash path)"
    )


@pytest.mark.skipif(
    not SAFE_SNAPSHOT,
    reason="PyGObject 3.42 cannot marshal Gtk.Snapshot through snapshot_child",
)
def test_drag_reorder_cycle_crash_free_and_single_undo(
    thumbnail_list: Document,
    import_in_mainloop: Callable[[object, list[str]], None],
    rose_png: str,
) -> None:
    """End-to-end: a drag reorder completes crash-free and undoes in one step.

    The manual-QA repro of task 3.3 as an automated gate: drive the app's real
    GTK DnD controllers in the order GTK fires them (DragSource prepare ->
    DropTarget accept/motion/drop) on a realized thumbnail tree, let the
    worker reorder land, and undo with a single call. On pre-fix code the same
    motion + repaint path segfaults, so surviving this sequence is itself the
    native-crash regression. Runs under the suite's xvfb display like the
    other display-backed tests in this module.
    """
    slist = thumbnail_list
    # Import two more pages through the worker so its page list matches the
    # realized tree (three pages, as the manual-QA repro describes).
    import_in_mainloop(slist, [rose_png])
    import_in_mainloop(slist, [rose_png])
    slist.get_selection().unselect_all()  # select() is additive, so clear first
    slist.select([0])
    start_ids = [row[2] for row in slist.data]
    assert len(start_ids) == 3, "expected three pages to reorder"
    moved = start_ids[0]
    assert slist.get_selected_indices() == [0], "exactly the first page selected"

    drag_source = next(
        c for c in slist.observe_controllers() if isinstance(c, Gtk.DragSource)
    )
    slist.rows_drop_target.connect("motion", drag_motion_callback, slist)
    _realize_and_paint(slist)

    # The exact signal sequence a real drag produces.
    drag_source.emit("prepare", 0.0, 0.0)
    slist.rows_drop_target.emit("accept", None)
    slist.rows_drop_target.emit("motion", 20, 30)
    _realize_and_paint(slist)  # repaint while dragging: the former crash frame
    slist.rows_drop_target.emit("drop", "scantpaper-rows", 20, 500)

    # Wait for the worker reorder to land: the moved page goes last.
    def reordered() -> bool:
        ids = [row[2] for row in slist.data]
        return ids[-1] == moved and ids != start_ids

    _wait_for(reordered)
    assert slist.thread.can_undo(), "reorder must be undoable"
    assert slist.get_selected_indices() == [2], "moved page stays selected"

    # One undo restores the original order.
    def after_undo() -> None:
        nonlocal restored
        restored = [row[2] for row in slist.data] == start_ids

    restored = False
    slist.undo(finished_callback=after_undo)
    _wait_for(lambda: restored)
    assert [row[2] for row in slist.data] == start_ids, (
        "one undo restores the previous order"
    )
    assert slist.get_selected_indices() == [0], "undo restores the pre-drag selection"


def test_attach_thumbnail_css_tolerates_no_display(
    mocker: pytest.MockerFixture,
) -> None:
    """Attaching the stylesheet is a no-op before GTK opens a display.

    Whether any window test happens to run before the display opens
    depends on the environment, so cover the guard explicitly.
    """
    mocker.patch("gi.repository.Gdk.Display.get_default", return_value=None)
    _attach_thumbnail_css()
