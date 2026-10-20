"""Paint-level test for the thumbnail display size."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import gi
import pytest

from scantpaper.app_window import _attach_thumbnail_css
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


def test_attach_thumbnail_css_tolerates_no_display(
    mocker: pytest.MockerFixture,
) -> None:
    """Attaching the stylesheet is a no-op before GTK opens a display.

    Whether any window test happens to run before the display opens
    depends on the environment, so cover the guard explicitly.
    """
    mocker.patch("gi.repository.Gdk.Display.get_default", return_value=None)
    _attach_thumbnail_css()
