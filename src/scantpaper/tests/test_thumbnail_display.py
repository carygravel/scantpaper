"""Paint-level test for the thumbnail display size."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import gi

from scantpaper.app_window import _attach_thumbnail_css
from scantpaper.document import Document

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    import pytest

gi.require_version("Gtk", "4.0")
gi.require_version("Gsk", "4.0")
from gi.repository import (  # noqa: E402
    GLib,
    Gsk,
    Gtk,
)


def _texture_nodes(node: Gsk.RenderNode) -> Iterator[Gsk.TextureNode]:
    """Yield the texture nodes in a render node tree."""
    if isinstance(node, Gsk.TextureNode):
        yield node
    for child in node.get_children() or ():
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
    snapshot = Gtk.Snapshot()
    win.snapshot_child(slist, snapshot)
    node = snapshot.to_node()
    win.destroy()
    assert node is not None, "expected a render tree from the thumbnail list"
    return node


def test_thumbnail_paints_at_generated_size(
    rose_png: str,
    temp_db: object,
    import_in_mainloop: Callable[[object, list[str]], None],
) -> None:
    """The thumbnail list paints a thumbnail at its generated size.

    GTK4's CellRendererPixbuf clamps its paint to the stylesheet's
    -gtk-icon-size; without the application's CSS override a 100x65
    thumbnail is painted at 16px high even though the cell is allocated
    100x65, so only a render-node assertion can catch the regression.
    """
    _attach_thumbnail_css()
    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [rose_png])
    pixbuf = slist.data[0][1]
    assert pixbuf.get_width() == 100, "generated thumbnail width"
    assert pixbuf.get_height() == 65, "generated thumbnail height"

    node = _snapshot_render_tree(slist)
    bounds = [n.get_bounds() for n in _texture_nodes(node)]
    assert bounds, "expected a texture node in the thumbnail list render tree"
    painted = [(b.size.width, b.size.height) for b in bounds]
    assert any(
        abs(width - pixbuf.get_width()) <= 1 and abs(height - pixbuf.get_height()) <= 1
        for width, height in painted
    ), f"no thumbnail painted at {pixbuf.get_width()}x{pixbuf.get_height()}: {painted}"


def test_attach_thumbnail_css_tolerates_no_display(
    mocker: pytest.MockerFixture,
) -> None:
    """Attaching the stylesheet is a no-op before GTK opens a display.

    Whether any window test happens to run before the display opens
    depends on the environment, so cover the guard explicitly.
    """
    mocker.patch("gi.repository.Gdk.Display.get_default", return_value=None)
    _attach_thumbnail_css()
