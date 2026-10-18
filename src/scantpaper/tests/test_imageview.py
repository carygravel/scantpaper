"""Basic tests for imageview."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock, patch

import cairo
import gi
import pytest

from scantpaper.const import STYLE_CLASS_RUBBERBAND
from scantpaper.imageview import Dragger, ImageView, Selector, SelectorDragger, Tool

if TYPE_CHECKING:
    from collections.abc import Callable

    from scantpaper.loop_helpers import _MainLoopWrapper

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import (  # noqa: E402
    Gdk,
    GdkPixbuf,
    GLib,
    Gtk,
)


@dataclass
class MockEvent:
    """mock enough of the event class to test it."""

    button: int
    x: float
    y: float


def _gesture(button: int) -> MagicMock:
    """Fake Gtk.GestureClick carrying the button being pressed/released."""
    gesture = MagicMock()
    gesture.get_current_button.return_value = button
    return gesture


def _mock_allocation(view: ImageView, width: int, height: int) -> None:
    """Give an unrealized view a fixed size for deterministic fit math.

    An unrealized GTK4 widget reports a 0x0 allocation, which makes
    zoom_to_fit() a no-op. The offset setter mutates the rectangle it reads,
    so return a fresh copy on every call, as the real getter does.
    """

    def allocation() -> Gdk.Rectangle:
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = 0, 0, width, height
        return rect

    view.get_allocation = MagicMock(side_effect=allocation)


@pytest.fixture
def mock_view() -> ImageView:
    """Fixture for ImageView with a mocked cursor setter."""
    view = ImageView()
    view.set_cursor = MagicMock()
    return view


def test_basics(rose_png: str) -> None:
    """Basic tests for imageview."""
    view = ImageView()
    assert isinstance(view, ImageView)
    assert isinstance(view.get_tool(), SelectorDragger), (
        "get_tool() defaults to SelectorDragger"
    )

    # An unrealized GTK4 widget reports a 0x0 allocation (GTK3 used 1x1), so
    # zoom_to_fit() leaves the zoom alone until the widget is allocated.
    unrealized = view.get_allocation()
    assert isinstance(unrealized, Gdk.Rectangle)
    assert (unrealized.x, unrealized.y) == (0, 0)
    assert (unrealized.width, unrealized.height) == (0, 0)

    # Fill in the old GTK3 default so the fit math below is exercised.
    _mock_allocation(view, 1, 1)

    def on_offset_changed(
        _widget: Gtk.Widget, offset_x: float, offset_y: float
    ) -> None:
        view.disconnect(signal)
        if view.get_scale_factor() <= 1:
            assert offset_x == 0, "emitted offset-changed signal x"
            assert offset_y == 12, "emitted offset-changed signal y"

    signal = view.connect("offset-changed", on_offset_changed)
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png), zoom_to_fit=True)

    if view.get_scale_factor() <= 1:
        viewport = view.get_viewport()
        assert viewport.x == 0, "get_viewport x"
        assert viewport.y == pytest.approx(-12, 0.001), "get_viewport y"
        assert viewport.width == pytest.approx(70, 0.001), "get_viewport width"
        assert viewport.height == pytest.approx(70, 0.001), "get_viewport height"

    assert isinstance(view.get_pixbuf(), GdkPixbuf.Pixbuf), "get_pixbuf()"
    size = view.get_pixbuf_size()
    assert size.width == 70, "get_pixbuf_size width"
    assert size.height == 46, "get_pixbuf_size height"
    allocation = view.get_allocation()
    assert allocation.x == 0, "get_allocation x"
    assert allocation.y == 0, "get_allocation y"
    assert allocation.width == 1, "get_allocation width"
    assert allocation.height == 1, "get_allocation height"

    assert view.get_zoom() == pytest.approx(0.01428 * view.get_scale_factor(), 0.001), (
        "get_zoom()"
    )

    def on_zoom_changed(_widget: Gtk.Widget, zoom: float) -> None:
        view.disconnect(signal)
        assert zoom == 1, "emitted zoom-changed signal"

    signal = view.connect("zoom-changed", on_zoom_changed)
    view.set_zoom(1)


def test_selection(rose_png: str) -> None:
    """Basic tests for imageview."""
    view = ImageView()
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png), zoom_to_fit=True)

    def on_selection_changed(_widget: Gtk.Widget, selection: Gdk.Rectangle) -> None:
        view.disconnect(signal)
        assert selection.x == 10, "emitted selection-changed signal x"
        assert selection.y == 10, "emitted selection-changed signal y"
        assert selection.width == 10, "emitted selection-changed signal width"
        assert selection.height == 10, "emitted selection-changed signal heigth"

    signal = view.connect("selection-changed", on_selection_changed)
    selection = Gdk.Rectangle()
    selection.x, selection.y, selection.width, selection.height = 10, 10, 10, 10
    view.set_selection(selection)
    selection = cast("Any", view.get_selection())
    assert selection.x == 10, "get_selection x"
    assert selection.y == 10, "get_selection y"
    assert selection.width == 10, "get_selection width"
    assert selection.height == 10, "get_selection heigth"

    def on_tool_changed(_widget: Gtk.Widget, tool: Tool) -> None:
        view.disconnect(signal)
        assert isinstance(tool, Selector), "emitted tool-changed signal"

    signal = view.connect("tool-changed", on_tool_changed)
    view.set_tool(Selector(view))

    selection.x, selection.y, selection.width, selection.height = -10, -10, 20, 20
    view.set_selection(selection)
    selection = cast("Any", view.get_selection())
    assert selection.x == 0, "selection cannot overlap top left border x"
    assert selection.y == 0, "selection cannot overlap top left border y"
    assert selection.width == 10, "selection cannot overlap top left border width"
    assert selection.height == 10, "selection cannot overlap top left border heigth"

    selection.x, selection.y, selection.width, selection.height = 10, 10, 80, 50
    view.set_selection(selection)
    assert selection.x == 10, "selection cannot overlap bottom right border x"
    assert selection.y == 10, "selection cannot overlap bottom right border y"
    assert selection.width == 60, "selection cannot overlap bottom right border width"
    assert selection.height == 36, "selection cannot overlap bottom right border heigth"


def test_selection_clamp_never_negative(rose_png: str) -> None:
    """A selection fully outside the image clamps to zero area, never negative."""
    view = ImageView()
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png), zoom_to_fit=True)
    # rose.png is 70x46.
    selection = Gdk.Rectangle()
    selection.x, selection.y, selection.width, selection.height = -50, -50, 30, 30
    view.set_selection(selection)
    assert selection.width >= 0, "negative-x clamp must not yield negative width"
    assert selection.height >= 0, "negative-y clamp must not yield negative height"

    selection.x, selection.y, selection.width, selection.height = 60, 40, 80, 50
    view.set_selection(selection)
    assert selection.width >= 0, "right-overflow clamp must not yield negative width"
    assert selection.height >= 0, "bottom-overflow clamp must not yield negative height"
    assert selection.x <= 70, "clamped x stays within image"
    assert selection.y <= 46, "clamped y stays within image"


def test_selection_clamp_keeps_stored_selection_valid(rose_png: str) -> None:
    """The stored shared selection is never left with a negative rectangle."""
    view = ImageView()
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png), zoom_to_fit=True)
    stored = Gdk.Rectangle()
    stored.x, stored.y, stored.width, stored.height = -50, -50, 30, 30
    # set_selection clamps the passed object in place, as the shared
    # settings["selection"] would be; it must not become negative.
    view.set_selection(stored)
    assert stored.width >= 0
    assert stored.height >= 0


def test_viewport(rose_png: str) -> None:
    """Basic tests for imageview."""
    view = ImageView()
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png), zoom_to_fit=True)
    view.set_resolution_ratio(2)
    assert view.get_resolution_ratio() == 2, "get/set_resolution_ratio()"

    # A TypeError is raised when set_pixbuf() is called with something that is not a pixbuf.
    with pytest.raises(TypeError):
        view.set_pixbuf("Hi mom!", zoom_to_fit=True)

    view.set_pixbuf(None, zoom_to_fit=True)
    assert view.get_pixbuf() is None, "correctly cleared pixbuf"
    viewport = view.get_viewport()
    assert viewport.x == 0, "correctly cleared viewport x"
    assert viewport.y == 0, "correctly cleared viewport y"
    assert viewport.width == 0, "correctly cleared viewport width"
    assert viewport.height == 0, "correctly cleared viewport height"

    view.set_pixbuf(None, zoom_to_fit=False)
    assert view.get_pixbuf() is None, "correctly cleared pixbuf #2"


def test_transparency(datadir: str) -> None:
    """Test transparency."""
    css_provider_alpha = Gtk.CssProvider()
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(), css_provider_alpha, 0
    )
    css_provider_alpha.load_from_data(
        f"""
    .imageview.transparent {{
        background-color: #ff0000;
        background-image: none;
    }}
    .imageview {{
        background-image: url('file://{datadir}transp-blue.svg');
    }}
""".encode()
    )
    view = ImageView()
    _mock_allocation(view, 300, 200)
    view.set_pixbuf(
        GdkPixbuf.Pixbuf.new_from_file(f"{datadir}transp-green.svg"),
        zoom_to_fit=True,
    )

    # GTK4 has no window grab; render the draw function into an offscreen
    # surface instead and read the pixels back.
    pxb = _render_view(view, 300, 200)

    p_x = int(pxb.get_width() / 2)
    p_y = int(pxb.get_height() / 2)
    middle = get_pixel(pxb, p_x, p_y)
    assert middle == [0, 255, 0], "middle pixel should be green"

    found = False
    while p_x > 0:
        pixel = get_pixel(pxb, p_x, p_y)
        if pixel == [255, 0, 0]:
            found = True
            break
        p_x -= 1
    assert found, "there is red background"

    found = False
    while p_x > 0:
        pixel = get_pixel(pxb, p_x, p_y)

        # the blue chessboard can become blurred with hidpi :(
        # Check for bluish color (blue channel dominant and > 200)
        if pixel[2] > 200 and pixel[2] > pixel[0] and pixel[2] > pixel[1]:
            found = True
            break
        p_x -= 1
    assert found, "there is blue outside"


def test_zoom(datadir: str) -> None:
    """Test zoom."""
    view = ImageView()
    _mock_allocation(view, 300, 200)
    view.set_pixbuf(
        GdkPixbuf.Pixbuf.new_from_file(f"{datadir}bigpic.svg"), zoom_to_fit=True
    )
    scale = view.get_scale_factor()
    assert view.get_zoom() == pytest.approx(0.2 * scale, 0.0001), "shrunk"
    view.set_zoom(1)

    # the transp-green picture is 100x100 which is less than 200.
    view.set_pixbuf(
        GdkPixbuf.Pixbuf.new_from_file(f"{datadir}transp-green.svg"),
        zoom_to_fit=False,
    )
    assert view.get_zoom() == 1, "picture fully visible"
    view.set_pixbuf(
        GdkPixbuf.Pixbuf.new_from_file(f"{datadir}transp-green.svg"),
        zoom_to_fit=True,
    )
    assert view.get_zoom() == 2 * scale, "zoomed"


def test_selector_tool(datadir: str) -> None:
    """Test selector tool."""
    window = Gtk.Window()
    window.set_default_size(300, 200)
    view = ImageView()
    window.set_child(view)
    view.set_tool(Selector(view))
    _mock_allocation(view, 300, 200)
    view.set_pixbuf(
        GdkPixbuf.Pixbuf.new_from_file(f"{datadir}transp-green.svg"),
        zoom_to_fit=True,
    )
    window.present()
    window.hide()

    view.set_zoom(8)
    event = MockEvent(button=1, x=7, y=5)
    view.get_tool().button_pressed(event.button, event.x, event.y)
    event.x = 93
    event.y = 67
    view.get_tool().motion(event.x, event.y)
    view.get_tool().button_released(event.button, event.x, event.y)

    if view.get_scale_factor() <= 1:
        selection = view.get_selection()
        assert selection.x == 32, "get_selection x"
        assert selection.y == 38, "get_selection y"
        assert selection.width == 11, "get_selection width"
        assert selection.height >= 7, "get_selection height"


def get_pixel(pxb: object, p_x: int, p_y: int) -> list[int]:
    """Return the RGB values of the pixel at (p_x, p_y)."""
    pixels = pxb.get_pixels()
    offset = p_y * pxb.get_rowstride() + p_x * pxb.get_n_channels()
    return list(pixels[offset : offset + 3])


def _find_pixel(
    pxb: object,
    p_x: int,
    p_y: int,
    step: int,
    continue_cond: Callable[[int], bool],
    predicate: Callable[[list[int]], bool],
) -> tuple[bool, int, list[int] | None]:
    """Scan pixels on row p_y from p_x by step while continue_cond(p_x) holds.

    Returns (found, end_x, last_pixel).
    """
    last = None
    while continue_cond(p_x):
        last = get_pixel(pxb, p_x, p_y)
        if predicate(last):
            return True, p_x, last
        p_x += step
    return False, p_x, last


class _SurfaceReader:
    """Expose a cairo surface through the GdkPixbuf pixel accessors.

    GTK4 has no window grab, so tests render the view's draw function into an
    offscreen surface instead. get_pixel() and _find_pixel() only need the
    pixbuf pixel accessors, which this adapter provides with the ARGB32 byte
    order swapped to RGB.
    """

    def __init__(self, surface: cairo.ImageSurface) -> None:
        surface.flush()
        raw = bytes(surface.get_data())
        stride = surface.get_stride()
        self._width = surface.get_width()
        self._height = surface.get_height()
        rgb = bytearray(self._width * self._height * 3)
        for y in range(self._height):
            for x in range(self._width):
                offset = y * stride + x * 4
                blue, green, red = raw[offset : offset + 3]
                target = (y * self._width + x) * 3
                rgb[target : target + 3] = bytes((red, green, blue))
        self._rgb = bytes(rgb)
        self._stride = self._width * 3

    def get_pixels(self) -> bytes:
        """Return the RGB bytes of the whole image."""
        return self._rgb

    def get_rowstride(self) -> int:
        """Return the number of bytes per row."""
        return self._stride

    def get_n_channels(self) -> int:
        """Return the number of channels per pixel."""
        return 3

    def get_width(self) -> int:
        """Return the image width."""
        return self._width

    def get_height(self) -> int:
        """Return the image height."""
        return self._height


def _render_view(view: ImageView, width: int, height: int) -> _SurfaceReader:
    """Render the view's GTK4 draw function into an offscreen surface."""
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    context = cairo.Context(surface)
    view._draw_func(view, context, width, height)
    surface.flush()
    return _SurfaceReader(surface)


def test_find_pixel_reaches_boundary() -> None:
    """Test that _find_pixel returns not-found at the scan boundary."""
    pb = MagicMock()
    pb.get_pixels.return_value = b"\x01\x02\x03\x04\x05\x06"
    pb.get_rowstride.return_value = 3
    pb.get_n_channels.return_value = 3

    found, end_x, last = _find_pixel(pb, 0, 0, 1, lambda x: x < 2, lambda p: p == [])

    assert found is False
    assert end_x == 2
    assert last == [4, 5, 6]


def test_filter(datadir: str) -> None:
    """Test interpolation (filters)."""
    view = ImageView()
    _mock_allocation(view, 300, 200)
    view.set_pixbuf(
        GdkPixbuf.Pixbuf.new_from_file(f"{datadir}2color.svg"), zoom_to_fit=True
    )
    view.set_zoom(15)
    view.set_interpolation(cairo.FILTER_BILINEAR)

    # GTK4 has no window grab; render the draw function into an offscreen
    # surface instead and read the pixels back.
    pxb = _render_view(view, 300, 200)

    p_x = int(pxb.get_width() / 2)
    p_y = int(pxb.get_height() / 2)
    assert get_pixel(pxb, p_x, p_y) == [255, 0, 0], "middle pixel should be red"

    found, blurred_x, _ = _find_pixel(
        pxb, p_x, p_y, -1, lambda x: x > 0, lambda p: p != [255, 0, 0]
    )
    assert found, "there is non-red outside"

    found, fullblue_x, _ = _find_pixel(
        pxb, blurred_x, p_y, -1, lambda x: x > 0, lambda p: p == [0, 0, 255]
    )
    assert found, "there is blue outside"
    assert fullblue_x < blurred_x, "blue outside red"

    view.set_interpolation(cairo.FILTER_NEAREST)
    pxb = _render_view(view, 300, 200)

    assert get_pixel(pxb, fullblue_x, p_y) == [
        0,
        0,
        255,
    ], "blue pixel should still be blue"

    found, p_x, pixel = _find_pixel(
        pxb,
        fullblue_x,
        p_y,
        1,
        lambda x: x <= blurred_x,
        lambda p: p != [0, 0, 255],
    )

    assert found, "there is non-blue inside"
    assert pixel == [255, 0, 0], "red pixel should be immediatelly near blue one"

    assert fullblue_x < p_x, "sharp edge should be within blurred edge (1)"
    assert p_x < blurred_x, "sharp edge should be within blurred edge (2)"


def test_drag_no_pixbuf() -> None:
    """Test dragging without a pixbuf."""
    view = ImageView()
    view.set_tool(Dragger(view))
    tool = view.get_tool()
    event = MockEvent(button=1, x=10, y=10)
    tool.button_pressed(event.button, event.x, event.y)
    event.x = 20
    event.y = 20
    tool.motion(event.x, event.y)
    assert tool.drag_start == {"x": 10, "y": 10}


def test_tool_base_methods() -> None:
    """Test Tool base class methods."""
    view = ImageView()
    tool = Tool(view)
    assert tool.view() == view
    assert tool.button_pressed(1, 0.0, 0.0) is False
    assert tool.button_released(1, 0.0, 0.0) is None
    assert tool.motion(0.0, 0.0) is None
    assert tool.cursor_type_at_point(0, 0) is None
    assert tool.cursor_at_point(0, 0) is None

    # test connect/disconnect
    handler_id = tool.connect("zoom-changed", lambda *_args: None)
    tool.disconnect(handler_id)


def test_dragger_edge_cases(rose_png: str, mock_view: ImageView) -> None:
    """Test Dragger tool edge cases."""
    view = mock_view
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png), zoom_to_fit=False)
    dragger = Dragger(view)
    view.set_tool(dragger)

    # button 3 should not block context menu
    event = MockEvent(button=3, x=10, y=10)
    assert dragger.button_pressed(event.button, event.x, event.y) is False

    # dragging and motion
    event = MockEvent(button=1, x=10, y=10)
    dragger.button_pressed(event.button, event.x, event.y)
    assert dragger.dragging is True

    event.x, event.y = 15, 15
    dragger.motion(event.x, event.y)
    assert dragger.drag_start == {"x": 15, "y": 15}

    dragger.button_released(event.button, event.x, event.y)
    assert dragger.dragging is False

    # cursor types
    assert dragger.cursor_type_at_point(10, 10) == "grab"
    dragger.dragging = True
    assert dragger.cursor_type_at_point(10, 10) == "grabbing"
    dragger.dragging = False
    assert dragger.cursor_type_at_point(-10, -10) is None


def test_selector_edge_cases(rose_png: str, mock_view: ImageView) -> None:
    """Test Selector tool edge cases."""
    view = mock_view
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png), zoom_to_fit=False)
    selector = Selector(view)
    view.set_tool(selector)

    # button 3
    event = MockEvent(button=3, x=10, y=10)
    assert selector.button_pressed(event.button, event.x, event.y) is False

    # selector without selection
    assert selector.cursor_type_at_point(10, 10) == "crosshair"

    # motion without dragging
    selector.motion(10, 10)

    # set/get selection convenience methods
    selection = Gdk.Rectangle()
    selection.x, selection.y, selection.width, selection.height = 5, 5, 5, 5
    selector.set_selection(selection)
    assert selector.get_selection().x == 5


def test_selector_dragger_tool(rose_png: str, mock_view: ImageView) -> None:
    """Test SelectorDragger tool."""
    view = mock_view
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png), zoom_to_fit=False)
    tool = SelectorDragger(view)
    view.set_tool(tool)

    # LMB -> Selector
    event = MockEvent(button=1, x=10, y=10)
    tool.button_pressed(event.button, event.x, event.y)
    assert isinstance(tool._tool, Selector)

    # MMB -> Dragger
    event = MockEvent(button=2, x=10, y=10)
    tool.button_pressed(event.button, event.x, event.y)
    assert isinstance(tool._tool, Dragger)

    # RMB -> False
    event = MockEvent(button=3, x=10, y=10)
    assert tool.button_pressed(event.button, event.x, event.y) is False

    # motion and released
    tool.motion(event.x, event.y)
    tool.button_released(event.button, event.x, event.y)
    assert isinstance(tool._tool, Selector)

    # cursor
    assert tool.cursor_type_at_point(10, 10) == "se-resize"


def test_imageview_more_basics(rose_png: str) -> None:
    """Test more ImageView methods."""
    view = ImageView()
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png), zoom_to_fit=False)

    # zoom methods
    view.set_zoom(2.0)
    assert view.get_zoom() == 2.0
    assert view.getzoom_is_fit() is False

    view.zoom_in()
    assert view.get_zoom() > 2.0

    view.zoom_out()
    assert view.get_zoom() == pytest.approx(2.0)

    view.zoom_to_fit()
    assert view.getzoom_is_fit() is True

    view.set_fitting(value=False)
    assert view.getzoom_is_fit() is False

    # interpolation
    view.set_interpolation(cairo.FILTER_BEST)
    assert view.get_interpolation() == cairo.FILTER_BEST

    # resolution ratio
    view.set_resolution_ratio(1.5)
    assert view.get_resolution_ratio() == 1.5


def test_imageview_events(rose_png: str, mock_view: ImageView) -> None:
    """Test ImageView event handlers."""
    view = mock_view
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png), zoom_to_fit=False)

    # button events (mostly covered via tools, but call direct)
    event = MockEvent(button=1, x=10, y=10)
    view._button_pressed(_gesture(event.button), 1, event.x, event.y)
    view._motion(None, event.x, event.y)
    view._button_released(_gesture(event.button), 1, event.x, event.y)

    # scroll event: _scroll zooms around the last pointer position from _motion
    event = MockEvent(button=0, x=10, y=10)
    view._motion(None, event.x, event.y)
    view._scroll(None, 0.0, -1.0)
    assert view.get_zoom() > 1.0

    view._scroll(None, 0.0, 1.0)

    # configure event: the size-allocate vfunc re-fits when zoom_is_fit
    view.setzoom_is_fit(zoom_to_fit=True)
    view.do_size_allocate(400, 300, -1)


def test_imageview_draw(rose_png: str) -> None:
    """Test the ImageView draw function."""
    view = ImageView()
    # Use a pixbuf with alpha to hit line 518
    pixbuf = GdkPixbuf.Pixbuf.new_from_file(rose_png)
    # Ensure it has alpha
    # GdkPixbuf.Pixbuf.add_alpha() takes position-only args; PyGObject rejects keywords
    pixbuf_alpha = pixbuf.add_alpha(True, 0, 0, 0)  # noqa: FBT003
    view.set_pixbuf(pixbuf_alpha, zoom_to_fit=False)

    # draw with selection
    selection = Gdk.Rectangle()
    selection.x, selection.y, selection.width, selection.height = 5, 5, 5, 5
    view.set_selection(selection)

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 100, 100)
    context = cairo.Context(surface)
    view._draw_func(view, context, 1, 1)

    # draw without pixbuf
    view.set_pixbuf(None)
    view._draw_func(view, context, 1, 1)


def test_imageview_coordinate_conversions(rose_png: str) -> None:
    """Test ImageView coordinate conversion methods."""
    view = ImageView()
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png), zoom_to_fit=False)
    view.set_zoom(1.0)
    view.set_offset(0, 0)

    # These might depend on scale factor and allocation
    wx, wy = view.to_widget_coords(10, 10)
    ix, iy = view.to_image_coords(wx, wy)
    assert ix == pytest.approx(10)
    assert iy == pytest.approx(10)

    dw, dh = view.to_image_distance(10, 10)
    assert dw > 0
    assert dh > 0


def test_to_widget_coords_without_offset() -> None:
    """to_widget_coords treats a missing offset as an unshifted origin.

    A pixbuf set before the first real allocation leaves the offset unset;
    the conversion must not crash (it used to dereference None).
    """
    view = ImageView()
    assert view.get_offset() is None, "precondition: no offset"

    wx, wy = view.to_widget_coords(30, 40)
    assert wx == pytest.approx(30 / view.get_scale_factor()), "x unshifted"
    assert wy == pytest.approx(40 / view.get_scale_factor()), "y unshifted"

    # Round-trips through to_image_coords, which yields (None, None) without
    # an offset rather than inventing one.
    assert view.to_image_coords(wx, wy) == (None, None)


def test_imageview_zoom_to_selection(rose_png: str) -> None:
    """Test zoom_to_selection."""
    view = ImageView()
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png), zoom_to_fit=False)
    selection = Gdk.Rectangle()
    selection.x, selection.y, selection.width, selection.height = 5, 5, 5, 5
    view.set_selection(selection)
    view.zoom_to_selection(1.1)


def test_selector_drag_edges(rose_png: str, mock_view: ImageView) -> None:
    """Test Selector edge dragging logic."""
    view = mock_view
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png), zoom_to_fit=False)
    view.set_zoom(1.0)
    view.set_offset(0, 0)
    selector = Selector(view)
    view.set_tool(selector)

    # Set a selection
    sel = Gdk.Rectangle()
    sel.x, sel.y, sel.width, sel.height = 20, 20, 20, 20
    view.set_selection(sel)

    # Test cursor at edges
    # Left edge (using y=30 which is inside [20, 40])
    assert selector.cursor_type_at_point(*view.to_widget_coords(20, 30)) == "w-resize"
    assert selector.h_edge == "lower"
    assert selector.v_edge == "mid"

    # Right edge
    assert selector.cursor_type_at_point(*view.to_widget_coords(40, 30)) == "e-resize"
    assert selector.h_edge == "upper"
    assert selector.v_edge == "mid"

    # Top edge
    assert selector.cursor_type_at_point(*view.to_widget_coords(30, 20)) == "n-resize"
    assert selector.h_edge == "mid"
    assert selector.v_edge == "lower"

    # Bottom edge
    assert selector.cursor_type_at_point(*view.to_widget_coords(30, 40)) == "s-resize"
    assert selector.h_edge == "mid"
    assert selector.v_edge == "upper"

    # Corner (Top-Left) - Using values inside the CURSOR_PIXELS range but hitting the edges
    assert selector.cursor_type_at_point(*view.to_widget_coords(21, 21)) == "nw-resize"
    assert selector.h_edge == "lower"
    assert selector.v_edge == "lower"

    # Dragging an edge
    x, y = view.to_widget_coords(20, 30)
    event = MockEvent(button=1, x=x, y=y)
    selector.button_pressed(event.button, event.x, event.y)
    x, y = view.to_widget_coords(10, 30)
    event.x = x
    selector.motion(event.x, event.y)
    new_sel = view.get_selection()
    assert new_sel.x == 10
    assert new_sel.width == 30
    selector.button_released(event.button, event.x, event.y)


def test_dragger_dnd_start(rose_png: str, mock_view: ImageView) -> None:
    """Test Dragger DND start logic."""
    view = mock_view
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png), zoom_to_fit=False)
    # A usable allocation: the pan clamps at the edge of a 100x100 widget.
    alloc = Gdk.Rectangle()
    alloc.x, alloc.y, alloc.width, alloc.height = 0, 0, 100, 100
    view.get_allocation = MagicMock(return_value=alloc)
    view.get_scale_factor = MagicMock(return_value=1)
    dragger = Dragger(view)
    view.set_tool(dragger)

    # Mock drag_check_threshold to return True
    view.drag_check_threshold = MagicMock(return_value=True)
    # Mock emit to return True for dnd-start
    view.emit = MagicMock(return_value=True)

    event = MockEvent(button=1, x=10, y=10)
    dragger.button_pressed(event.button, event.x, event.y)

    # Move enough to trigger DND (clamped offset shouldn't move if already at edge)
    event.x = 100
    dragger.motion(event.x, event.y)

    assert dragger.dragging is False
    view.emit.assert_any_call("dnd-start", 100, 10, 1)


def test_imageview_clamping(rose_png: str) -> None:
    """Test ImageView offset clamping."""
    view = ImageView()
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png), zoom_to_fit=False)
    # Mock get_allocation
    alloc = Gdk.Rectangle()
    alloc.x, alloc.y, alloc.width, alloc.height = 0, 0, 100, 100
    view.get_allocation = MagicMock(return_value=alloc)
    # Use real to_image_distance but ensure scale factor is 1
    view.get_scale_factor = MagicMock(return_value=1.0)

    # Center if smaller than widget (rose is 70x46)
    view.set_offset(0, 0)
    offset = view.get_offset()
    assert offset.x == (100 - 70) / 2
    assert offset.y == (100 - 46) / 2

    # If larger than widget (zoom in)
    view.set_zoom(2.0)  # image distance for 100x100 is 50x50
    view.set_offset(10, 10)  # should clamp to 0
    offset = view.get_offset()
    assert offset.x == 0


def test_zoom_clamping() -> None:
    """Test zoom clamping."""
    view = ImageView()
    view._set_zoom(1000)
    assert view.get_zoom() == 100
    view._set_zoom(0.00001)
    assert view.get_zoom() == 0.001


def test_selector_flip_edges(rose_png: str, mock_view: ImageView) -> None:
    """Test Selector edge flipping when dragging."""
    view = mock_view
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png), zoom_to_fit=False)
    selector = Selector(view)
    view.set_tool(selector)

    # Start dragging a new selection from (50, 50) to (60, 60)
    x, y = view.to_widget_coords(50, 50)
    event = MockEvent(button=1, x=x, y=y)
    selector.button_pressed(event.button, event.x, event.y)

    event.x, event.y = view.to_widget_coords(60, 60)
    selector.motion(event.x, event.y)
    sel = view.get_selection()
    assert sel.x == 50
    assert sel.width == 10

    # Drag past the start point to flip edge
    x, y = view.to_widget_coords(40, 50)
    event.x = x
    selector.motion(event.x, event.y)
    sel = view.get_selection()
    assert sel.x == 40
    assert sel.width == 10


def test_imageview_no_pixbuf_offset() -> None:
    """Test set_offset when pixbuf is None."""
    view = ImageView()
    view.set_offset(10, 10)
    assert view.get_offset() is None


def test_update_cursor_none(mock_view: ImageView, rose_png: str) -> None:
    """Test update_cursor when cursor_at_point returns None."""
    view = mock_view
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png), zoom_to_fit=False)
    view.get_tool().cursor_at_point = MagicMock(return_value=None)
    view.update_cursor(10, 10)
    # Should not crash and not change the cursor
    view.set_cursor.assert_not_called()


def test_selector_update_selection_direct(rose_png: str) -> None:
    """Test Selector._update_selection directly to hit mid/mid branch."""
    view = ImageView()
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png), zoom_to_fit=False)
    # Ensure it has an allocation for coordinate conversion if needed,
    # though here we use scale factor 1.
    selector = Selector(view)

    # Manually set dragging and drag_start
    selector.dragging = True
    x, y = view.to_widget_coords(10, 10)
    selector.drag_start = {"x": x, "y": y}

    # h_edge and v_edge are None, will be set to "mid" in _update_selection
    x, y = view.to_widget_coords(20, 20)
    event = MockEvent(button=1, x=x, y=y)
    selector._update_selection(event.x, event.y)

    sel = view.get_selection()
    assert sel.x == 10
    assert sel.y == 10
    assert sel.width == 10
    assert sel.height == 10


def test_selector_update_selection_edge_branches(rose_png: str) -> None:
    """Test Selector._update_selection edge branches."""
    view = ImageView()
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png), zoom_to_fit=False)

    # Set an initial selection
    initial_sel = Gdk.Rectangle()
    initial_sel.x, initial_sel.y, initial_sel.width, initial_sel.height = 20, 20, 20, 20
    view.set_selection(initial_sel)

    selector = Selector(view)
    selector.dragging = True

    # Test dragging only horizontal edge (v_edge is mid)
    selector.h_edge = "lower"
    selector.v_edge = "mid"
    x, y = view.to_widget_coords(40, 30)
    selector.drag_start = {"x": x, "y": None}

    x, y = view.to_widget_coords(10, 30)
    event = MockEvent(button=1, x=x, y=y)
    selector._update_selection(event.x, event.y)

    sel = view.get_selection()
    assert sel.x == 10
    assert sel.width == 30
    assert sel.y == 20
    assert sel.height == 20

    # Test dragging only vertical edge (h_edge is mid)
    # rose_png height is 46. y=20 + height=20 = 40.
    selector.h_edge = "mid"
    selector.v_edge = "upper"
    x, y = view.to_widget_coords(40, 20)
    selector.drag_start = {"x": None, "y": y}

    x, y = view.to_widget_coords(30, 40)
    event = MockEvent(button=1, x=x, y=y)
    selector._update_selection(event.x, event.y)

    sel = view.get_selection()
    assert sel.x == 10  # from previous selection
    assert sel.width == 30
    assert sel.y == 20
    assert sel.height == 20


def test_selector_cursor_dragging_branches(rose_png: str, mock_view: ImageView) -> None:
    """Test Selector.cursor_type_at_point dragging branches."""
    view = mock_view
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png), zoom_to_fit=False)
    selector = Selector(view)
    view.set_tool(selector)

    # Set a selection
    sel = Gdk.Rectangle()
    sel.x, sel.y, sel.width, sel.height = 20, 20, 20, 20
    view.set_selection(sel)

    # 1. Hit h_edge=="mid" and v_edge=="mid" branch (new selection start)
    selector.dragging = True
    selector.h_edge = "mid"
    selector.v_edge = "mid"
    selector.drag_start = {}
    x, y = view.to_widget_coords(30, 30)
    assert selector.cursor_type_at_point(x, y) == "se-resize"
    assert selector.h_edge == "upper"
    assert selector.v_edge == "upper"
    assert selector.drag_start == {"x": x, "y": y}

    # 2. Hit h_edge=="mid" and v_edge!="mid" branch
    selector.h_edge = "mid"
    selector.v_edge = "lower"
    selector.drag_start = {}
    assert selector.cursor_type_at_point(*view.to_widget_coords(30, 20)) == "n-resize"
    x, y = view.to_widget_coords(40, 40)
    assert selector.drag_start["x"] == x

    # test case where "x" is already in drag_start
    selector.drag_start = {"x": 50}
    assert selector.cursor_type_at_point(*view.to_widget_coords(30, 20)) == "n-resize"

    # 3. Hit h_edge!="mid" and v_edge=="mid" branch
    selector.h_edge = "lower"
    selector.v_edge = "mid"
    selector.drag_start = {}
    assert selector.cursor_type_at_point(*view.to_widget_coords(20, 30)) == "w-resize"
    assert selector.drag_start["y"] == y

    # test case where "y" is already in drag_start
    selector.drag_start = {"y": 50}
    assert selector.cursor_type_at_point(*view.to_widget_coords(20, 30)) == "w-resize"


def test_dragger_coverage(rose_png: str, mock_view: ImageView) -> None:
    """Cover specific lines in Dragger.motion."""
    view = mock_view
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png), zoom_to_fit=False)
    dragger = Dragger(view)
    view.set_tool(dragger)

    # Cover line 91: motion when not dragging
    event = MockEvent(button=1, x=10, y=10)
    dragger.dragging = False
    dragger.motion(event.x, event.y)  # Should return early (line 91)

    # Cover line 104: motion when dragging but not dnd_eligible
    dragger.dragging = True
    dragger.drag_start = {"x": 10, "y": 10}
    dragger.dnd_eligible = False

    # Mock view methods to verify behavior
    # We need offset to be returned by view.get_offset(). set_pixbuf sets it.

    # We want to verify that we return at line 104.
    # Line 115 calls view.drag_check_threshold.
    view.drag_check_threshold = MagicMock()

    event.x, event.y = 20, 20
    dragger.motion(event.x, event.y)

    # Should have called set_offset (lines 98-101) - implicitly verified by the fact that code runs
    # But should NOT have called drag_check_threshold (line 115) because of return at line 104
    view.drag_check_threshold.assert_not_called()


def test_update_dragged_edge_coverage(rose_png: str, mock_view: ImageView) -> None:
    """Cover _update_dragged_edge branches."""
    view = mock_view
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png), zoom_to_fit=False)
    selector = Selector(view)

    # direction="x" -> h_edge, direction="y" -> v_edge

    # 1. edge == "lower", direction in drag_start, s > drag_start[direction]
    selector.h_edge = "lower"
    selector.drag_start = {"x": 10}
    selector._update_dragged_edge("x", 20, 5, 30)
    assert selector.h_edge == "upper"

    # 2. edge == "lower", direction in drag_start, s <= drag_start[direction]
    selector.h_edge = "lower"
    selector.drag_start = {"x": 30}
    selector._update_dragged_edge("x", 20, 5, 30)
    assert selector.h_edge == "lower"

    # 3. edge == "upper", direction in drag_start, s < drag_start[direction]
    selector.v_edge = "upper"
    selector.drag_start = {"y": 30}
    selector._update_dragged_edge("y", 20, 5, 30)
    assert selector.v_edge == "lower"

    # 4. edge == "upper", direction NOT in drag_start
    selector.h_edge = "upper"
    selector.drag_start = {}
    selector._update_dragged_edge("x", 20, 5, 30)
    assert selector.drag_start["x"] == 5  # line 312
    assert selector.h_edge == "upper"


def test_imageview_coverage_complex(rose_png: str, mock_view: ImageView) -> None:
    """Cover various specific lines in imageview.py."""
    view = ImageView()

    # 1. A degenerate selection must not render the rubberband.
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png), zoom_to_fit=False)
    # Selection with 0 width
    selection = Gdk.Rectangle()
    selection.x, selection.y, selection.width, selection.height = 10, 10, 0, 10
    view.set_selection(selection)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 100, 100)
    context = cairo.Context(surface)
    with patch("gi.repository.Gtk.render_frame") as render_frame:
        view._draw_func(view, context, 1, 1)
    render_frame.assert_not_called()

    # 2. _scroll returns early if image_x is None
    # image_x comes from to_image_coords, which returns None, None if offset is None
    view_no_offset = mock_view
    view_no_offset.set_pixbuf(None)  # No pixbuf -> no offset usually
    # Force offset property to be None if set_pixbuf(None) doesn't do it
    view_no_offset.set_property("offset", None)
    view_no_offset._motion(None, 10, 10)
    assert view_no_offset._scroll(None, 0.0, -1.0) is False

    # 3. Line 637: to_image_coords return None, None if offset is None
    view.set_property("offset", None)
    assert view.to_image_coords(10, 10) == (None, None)

    # 4. Line 668: setzoom_is_fit with limit
    view.setzoom_is_fit(zoom_to_fit=True, limit=5.0)
    assert view.zoom_to_fit_limit == 5.0

    # 5. Line 756: set_tool raise ValueError
    with pytest.raises(TypeError, match="invalid set_tool call"):
        view.set_tool(cast("Tool", cast("object", "Not a tool")))

    # 6. Line 770: set_selection return if pixbuf_size is None
    view.set_pixbuf(None)
    view.set_selection(selection)  # Should return early at 770

    # 7. Line 836: _clamp_direction offset < allocation - pixbuf_size
    # Use a fresh view to ensure clean state
    view7 = ImageView()
    view7.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png), zoom_to_fit=False)
    view7.set_zoom(1.0)

    # Mock allocation to be small (e.g., 10x10) so image is larger
    alloc = Gdk.Rectangle()
    alloc.x, alloc.y, alloc.width, alloc.height = 0, 0, 10, 10
    view7.get_allocation = MagicMock(return_value=alloc)
    view7.get_scale_factor = MagicMock(return_value=1.0)

    # Try to set offset to -100 (way past -36 which is 10 - 46)
    # Should clamp to allocation - pixbuf_size = 10 - 46 = -36 (y) or 10 - 70 = -60 (x)
    view7.set_offset(-100, -100)
    offset = view7.get_offset()
    assert offset.x == -60  # 10 - 70
    assert offset.y == -36  # 10 - 46


def test_imageview_set_selection_none() -> None:
    """Verify that ImageView.set_selection(None) does not raise AttributeError."""
    view = MagicMock(spec=ImageView)
    view.selection = MagicMock()  # existing selection

    # Mock get_pixbuf_size to return something so it doesn't return early
    view.get_pixbuf_size.return_value = MagicMock(width=100, height=100)

    # This should not raise AttributeError
    ImageView.set_selection(view, None)
    assert view.selection is None


def test_selection_drawing_coordinates() -> None:
    """Test selection rubberband is drawn at widget coordinates with zoom applied."""
    view = ImageView()

    pixbuf = GdkPixbuf.Pixbuf.new(
        GdkPixbuf.Colorspace.RGB,
        has_alpha=False,
        bits_per_sample=8,
        width=100,
        height=100,
    )
    view.set_pixbuf(pixbuf)

    # ratio=0.5 makes to_widget_coords non-identity without any clamping.
    # to_widget_coords(x,y) = (x * zoom / factor / ratio, y * zoom / factor)
    # With zoom=1, factor=1, ratio=0.5: x-coords are doubled, y unchanged.
    view.set_resolution_ratio(0.5)

    selection = Gdk.Rectangle()
    selection.x, selection.y, selection.width, selection.height = 10, 20, 30, 40
    view.set_selection(selection)

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 400, 400)
    context = cairo.Context(surface)

    rubberband_calls = []

    def capture_render_background(
        style_ctx: Gtk.StyleContext,
        cr: object,
        x: float,
        y: float,
        w: float,
        h: float,
    ) -> None:
        del cr
        if style_ctx.has_class(STYLE_CLASS_RUBBERBAND):
            rubberband_calls.append((x, y, w, h))

    with (
        patch(
            "gi.repository.Gtk.render_background", side_effect=capture_render_background
        ),
        patch("gi.repository.Gtk.render_frame"),
    ):
        view._draw_func(view, context, 1, 1)

    assert len(rubberband_calls) == 1, "Selection background was not rendered"
    x, y, w, h = rubberband_calls[0]

    # Calculate expected coordinates using to_widget_coords to account for scale factor
    # to_widget_coords applies: (x + offset.x) * zoom / factor / ratio
    x1, y1 = view.to_widget_coords(10, 20)
    x2, y2 = view.to_widget_coords(40, 60)
    expected_w = x2 - x1
    expected_h = y2 - y1

    assert (x, y, w, h) == pytest.approx((x1, y1, expected_w, expected_h)), (
        f"Selection drawn at wrong coordinates: got {(x, y, w, h)}, expected "
        f"{(x1, y1, expected_w, expected_h)}"
    )


def test_adaptive_filter() -> None:
    """Test _get_adaptive_filter is interaction-driven, not zoom-driven."""
    view = ImageView()
    # static: configured interpolation regardless of zoom
    assert view._get_adaptive_filter() == cairo.FILTER_GOOD
    view.set_interpolation(cairo.FILTER_BEST)
    assert view._get_adaptive_filter() == cairo.FILTER_BEST
    # interacting: fast filtering overrides configured interpolation
    view.set_interacting(interacting=True)
    assert view._get_adaptive_filter() == cairo.FILTER_FAST
    view.set_interacting(interacting=False)
    assert view._get_adaptive_filter() == cairo.FILTER_BEST


def test_static_fit_zoom_high_quality() -> None:
    """Static full-page (fit) view renders with the configured filter, not point sampling."""
    view = ImageView()
    view._set_zoom(0.3)
    assert view._get_adaptive_filter() == cairo.FILTER_GOOD


def test_dragger_toggles_interacting() -> None:
    """Dragger pan toggles the view's interaction state."""
    view = ImageView()
    dragger = Dragger(view)
    event = MockEvent(button=1, x=5, y=5)
    dragger.button_pressed(event.button, event.x, event.y)
    assert view.get_interacting() is True
    dragger.button_released(event.button, event.x, event.y)
    assert view.get_interacting() is False


def test_selector_does_not_toggle_interacting(mocker: pytest.MockerFixture) -> None:
    """Selector rubber-band drag does not mark the view as interacting."""
    view = ImageView()
    selector = Selector(view)
    mocker.patch.object(selector, "_update_selection")
    selector.button_pressed(1, 5, 5)
    assert view.get_interacting() is False


def test_scroll_toggles_interacting_and_idle_returns(
    mocker: pytest.MockerFixture,
) -> None:
    """Scroll-zoom marks interacting; the idle callback restores quality."""
    view = ImageView()
    mocker.patch.object(view, "to_image_coords", return_value=(1.0, 1.0))
    view._motion(None, 10.0, 10.0)
    view._scroll(None, 0.0, -1.0)
    assert view.get_interacting() is True
    assert view._scroll_timeout is not None
    queue = mocker.patch.object(view, "queue_draw")
    view.do_dispose()  # dispose while a scroll timeout is armed removes it
    assert view._scroll_timeout is None
    assert view._scroll_idle() == GLib.SOURCE_REMOVE
    assert view.get_interacting() is False
    queue.assert_called_once()


def test_pixbuf_set_before_allocation_fits_on_allocate(
    rose_png: str,
    mainloop_with_timeout: Callable[[], _MainLoopWrapper],
) -> None:
    """A pixbuf set while unallocated is fitted at the first real allocation."""
    view = ImageView()
    win = Gtk.Window()
    win.set_default_size(400, 300)
    win.set_child(view)

    # The window is not presented yet, so the view has no usable allocation
    # and the fit is deferred.
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png), zoom_to_fit=True)
    assert view.get_offset() is None, "no offset while unallocated"
    assert view.getzoom_is_fit(), "zoom-to-fit still pending"

    loop = mainloop_with_timeout()

    def poll() -> bool:
        allocation = view.get_allocation()
        if allocation.width > 0 and allocation.height > 0:
            loop.quit()
            return cast("bool", GLib.SOURCE_REMOVE)
        return cast("bool", GLib.SOURCE_CONTINUE)

    # Before the window is presented the poll must keep polling rather than
    # end the loop.
    assert poll() == GLib.SOURCE_CONTINUE

    GLib.timeout_add(10, poll)
    GLib.timeout_add(2000, loop.quit)
    win.present()
    loop.run()
    allocation = Gdk.Rectangle()
    allocation.x, allocation.y = view.get_allocation().x, view.get_allocation().y
    allocation.width, allocation.height = (
        view.get_allocation().width,
        view.get_allocation().height,
    )
    win.destroy()

    assert allocation.width > 0, "allocated width"
    assert allocation.height > 0, "allocated height"
    assert view.get_offset() is not None, "offset computed on first allocation"
    expected = (
        min(allocation.width / 70, allocation.height / 46) * view.get_scale_factor()
    )
    assert view.get_zoom() == pytest.approx(expected, rel=0.01), "fit zoom"


def test_do_size_allocate_refits_when_fit(rose_png: str) -> None:
    """The size-allocate vfunc re-fits the page when zoom-to-fit is active."""
    view = ImageView()
    view.set_cursor = MagicMock()
    _mock_allocation(view, 400, 300)
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png), zoom_to_fit=True)
    assert view.get_zoom() == pytest.approx(400 / 70, rel=0.01), "initial fit"

    # Simulate a resize: the allocation now reports a wider widget.
    _mock_allocation(view, 800, 300)
    view.do_size_allocate(800, 300, -1)
    assert view.get_zoom() == pytest.approx(min(800 / 70, 300 / 46), rel=0.01), (
        "re-fit on allocate"
    )


def test_do_size_allocate_keeps_manual_zoom(rose_png: str) -> None:
    """The size-allocate vfunc leaves a manual zoom alone."""
    view = ImageView()
    view.set_cursor = MagicMock()
    _mock_allocation(view, 400, 300)
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png), zoom_to_fit=True)
    view.set_zoom(2.0)

    _mock_allocation(view, 800, 300)
    view.do_size_allocate(800, 300, -1)
    assert view.get_zoom() == 2.0, "manual zoom preserved"
