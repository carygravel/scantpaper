"Basic tests for imageview"

from dataclasses import dataclass
from unittest.mock import MagicMock
import pytest
from imageview import ImageView, Dragger, Selector, Tool, SelectorDragger
import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import (  # pylint: disable=wrong-import-position
    GLib,
    Gdk,
    GdkPixbuf,
    Gtk,
)


@dataclass
class MockEvent:
    "mock enough of the event class to test it"

    button: int
    x: float  # pylint: disable=invalid-name
    y: float  # pylint: disable=invalid-name
    direction: Gdk.ScrollDirection = Gdk.ScrollDirection.UP


@pytest.fixture
def mock_view():
    "Fixture for ImageView with mocked get_window"
    view = ImageView()
    view.get_window = MagicMock()
    # Mock window.set_cursor
    view.get_window.return_value.set_cursor = MagicMock()
    return view


def test_basics(rose_png):
    "Basic tests for imageview"

    view = ImageView()
    assert isinstance(view, ImageView)
    assert isinstance(view.get_tool(), Dragger), "get_tool() defaults to dragger"

    def on_offset_changed(_widget, offset_x, offset_y):
        view.disconnect(signal)
        if view.get_scale_factor() <= 1:
            assert offset_x == 0, "emitted offset-changed signal x"
            assert offset_y == 12, "emitted offset-changed signal y"

    signal = view.connect("offset-changed", on_offset_changed)
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png.name), True)

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
    assert allocation.x == -1, "get_allocation x"
    assert allocation.y == -1, "get_allocation y"
    assert allocation.width == 1, "get_allocation width"
    assert allocation.height == 1, "get_allocation height"

    assert view.get_zoom() == pytest.approx(
        0.01428 * view.get_scale_factor(), 0.001
    ), "get_zoom()"

    def on_zoom_changed(_widget, zoom):
        view.disconnect(signal)
        assert zoom == 1, "emitted zoom-changed signal"

    signal = view.connect("zoom-changed", on_zoom_changed)
    view.set_zoom(1)


def test_selection(rose_png):
    "Basic tests for imageview"
    view = ImageView()
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png.name), True)

    def on_selection_changed(_widget, selection):
        view.disconnect(signal)
        assert selection.x == 10, "emitted selection-changed signal x"
        assert selection.y == 10, "emitted selection-changed signal y"
        assert selection.width == 10, "emitted selection-changed signal width"
        assert selection.height == 10, "emitted selection-changed signal heigth"

    signal = view.connect("selection-changed", on_selection_changed)
    selection = Gdk.Rectangle()
    selection.x, selection.y, selection.width, selection.height = 10, 10, 10, 10
    view.set_selection(selection)
    selection = view.get_selection()
    assert selection.x == 10, "get_selection x"
    assert selection.y == 10, "get_selection y"
    assert selection.width == 10, "get_selection width"
    assert selection.height == 10, "get_selection heigth"

    def on_tool_changed(_widget, tool):
        view.disconnect(signal)
        assert isinstance(tool, Selector), "emitted tool-changed signal"

    signal = view.connect("tool-changed", on_tool_changed)
    view.set_tool(Selector(view))

    selection.x, selection.y, selection.width, selection.height = -10, -10, 20, 20
    view.set_selection(selection)
    selection = view.get_selection()
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


def test_viewport(rose_png):
    "Basic tests for imageview"
    view = ImageView()
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png.name), True)
    view.set_resolution_ratio(2)
    assert view.get_resolution_ratio() == 2, "get/set_resolution_ratio()"

    # A TypeError is raised when set_pixbuf() is called with something that is not a pixbuf.
    with pytest.raises(TypeError):
        view.set_pixbuf("Hi mom!", True)

    view.set_pixbuf(None, True)
    assert view.get_pixbuf() is None, "correctly cleared pixbuf"
    viewport = view.get_viewport()
    assert viewport.x == 0, "correctly cleared viewport x"
    assert viewport.y == 0, "correctly cleared viewport y"
    assert viewport.width == 1, "correctly cleared viewport width"
    assert viewport.height == 1, "correctly cleared viewport height"

    view.set_pixbuf(None, False)
    assert view.get_pixbuf() is None, "correctly cleared pixbuf #2"


def test_transparency(datadir):
    "Test transparency"
    window = Gtk.Window()
    window.set_size_request(300, 200)
    css_provider_alpha = Gtk.CssProvider()
    Gtk.StyleContext.add_provider_for_screen(  # pylint: disable=no-member
        window.get_screen(), css_provider_alpha, 0  # pylint: disable=no-member
    )
    css_provider_alpha.load_from_data(
        f"""
    .imageview.transparent {{
        background-color: #ff0000;
        background-image: none;
    }}
    .imageview {{
        background-image: url('{datadir}transp-blue.svg');
    }}
""".encode(
            "UTF-8"
        )
    )
    view = ImageView()
    view.set_pixbuf(
        GdkPixbuf.Pixbuf.new_from_file(f"{datadir}transp-green.svg"),
        True,
    )
    window.add(view)  # pylint: disable=no-member
    window.show_all()  # pylint: disable=no-member
    gdkw = window.get_window()  # pylint: disable=no-member

    # can't use a simple scalar, because it won't be in scope in the timeout
    var = {"pb": None}

    def grab_window():
        var["pb"] = Gdk.pixbuf_get_from_window(gdkw, *gdkw.get_geometry())
        Gtk.main_quit()
        return False

    # Have to grab the window in a timeout, because it has to hit the main loop to be drawn
    GLib.timeout_add(1000, grab_window)
    Gtk.main()

    def get_pixel(pxb, p_x, p_y):
        pixels = pxb.get_pixels()
        offset = p_y * pxb.get_rowstride() + p_x * pxb.get_n_channels()
        return list(pixels[offset : offset + 3])

    p_x = int(var["pb"].get_width() / 2)
    p_y = int(var["pb"].get_height() / 2)
    middle = get_pixel(var["pb"], p_x, p_y)
    assert middle == [0, 255, 0], "middle pixel should be green"

    found = False
    while p_x > 0:
        pixel = get_pixel(var["pb"], p_x, p_y)
        if pixel == [255, 0, 0]:
            found = True
            break
        p_x -= 1
    assert found, "there is red background"

    found = False
    while p_x > 0:
        pixel = get_pixel(var["pb"], p_x, p_y)

        # the blue chessboard can become blurred with hidpi :(
        pixel_below = get_pixel(var["pb"], p_x, p_y)
        if pixel == [0, 0, 255] or pixel_below == [0, 0, 255]:
            found = True
            break
        p_x -= 1
    assert found, "there is blue outside"


def test_zoom(datadir):
    "Test zoom"
    window = Gtk.Window()
    window.set_size_request(300, 200)
    view = ImageView()
    scale = view.get_scale_factor()
    window.add(view)
    window.show_all()
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(f"{datadir}bigpic.svg"), True)
    assert view.get_zoom() == pytest.approx(0.2 * scale, 0.0001), "shrunk"
    view.set_zoom(1)

    # the transp-green picture is 100x100 which is less than 200.
    view.set_pixbuf(
        GdkPixbuf.Pixbuf.new_from_file(f"{datadir}transp-green.svg"),
        False,
    )
    assert view.get_zoom() == 1, "picture fully visible"
    view.set_pixbuf(
        GdkPixbuf.Pixbuf.new_from_file(f"{datadir}transp-green.svg"),
        True,
    )
    assert view.get_zoom() == 2 * scale, "zoomed"


def test_selector_tool(datadir):
    "Test selector tool"
    window = Gtk.Window()
    window.set_size_request(300, 200)
    view = ImageView()
    window.add(view)
    view.set_tool(Selector(view))
    view.set_pixbuf(
        GdkPixbuf.Pixbuf.new_from_file(f"{datadir}transp-green.svg"),
        True,
    )
    window.show_all()
    window.hide()

    view.set_zoom(8)
    event = MockEvent(button=1, x=7, y=5)
    view.get_tool().button_pressed(event)
    event.x = 93
    event.y = 67
    view.get_tool().motion(event)
    view.get_tool().button_released(event)

    if view.get_scale_factor() <= 1:
        selection = view.get_selection()
        assert selection.x == 32, "get_selection x"
        assert selection.y == 38, "get_selection y"
        assert selection.width == 11, "get_selection width"
        assert selection.height >= 7, "get_selection height"


def test_filter(datadir):
    "Test interpolation (filters)"
    window = Gtk.Window()
    window.set_size_request(300, 200)
    view = ImageView()
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(f"{datadir}2color.svg"), True)
    window.add(view)
    window.show_all()
    view.set_zoom(15)
    view.set_interpolation(cairo.FILTER_BILINEAR)  # pylint: disable=no-member
    gdkw = window.get_window()  # pylint: disable=no-member

    # can't use a simple scalar, because it won't be in scope in the timeout
    var = {"pb": None}

    def grab_window():
        var["pb"] = Gdk.pixbuf_get_from_window(gdkw, *gdkw.get_geometry())
        Gtk.main_quit()
        return False

    # Have to grab the window in a timeout, because it has to hit the main loop to be drawn
    GLib.timeout_add(1000, grab_window)
    Gtk.main()

    def get_pixel(pxb, p_x, p_y):
        pixels = pxb.get_pixels()
        offset = p_y * pxb.get_rowstride() + p_x * pxb.get_n_channels()
        return list(pixels[offset : offset + 3])

    p_x = int(var["pb"].get_width() / 2)
    p_y = int(var["pb"].get_height() / 2)
    assert get_pixel(var["pb"], p_x, p_y) == [255, 0, 0], "middle pixel should be red"

    found = False
    while p_x > 0:
        if get_pixel(var["pb"], p_x, p_y) != [255, 0, 0]:
            found = True
            break
        p_x -= 1
    assert found, "there is non-red outside"

    blurred_x = p_x
    found = False
    while p_x > 0:
        if get_pixel(var["pb"], p_x, p_y) == [0, 0, 255]:
            found = True
            break
        p_x -= 1
    assert found, "there is blue outside"
    fullblue_x = p_x
    assert fullblue_x < blurred_x, "blue outside red"

    view.set_interpolation(cairo.FILTER_NEAREST)  # pylint: disable=no-member
    GLib.timeout_add(1000, grab_window)
    Gtk.main()

    assert get_pixel(var["pb"], fullblue_x, p_y) == [
        0,
        0,
        255,
    ], "blue pixel should still be blue"

    found = False
    while p_x <= blurred_x:
        pixel = get_pixel(var["pb"], p_x, p_y)
        if pixel != [0, 0, 255]:
            found = True
            break
        p_x += 1

    assert found, "there is non-blue inside"
    assert pixel == [255, 0, 0], "red pixel should be immediatelly near blue one"

    assert fullblue_x < p_x, "sharp edge should be within blurred edge (1)"
    assert p_x < blurred_x, "sharp edge should be within blurred edge (2)"


def test_drag_no_pixbuf():
    "Test dragging without a pixbuf"
    view = ImageView()
    tool = view.get_tool()
    event = MockEvent(button=1, x=10, y=10)
    tool.button_pressed(event)
    event.x = 20
    event.y = 20
    try:
        tool.motion(event)
    except AttributeError:
        pytest.fail("Dragging without a pixbuf should not raise an AttributeError")


def test_tool_base_methods():
    "Test Tool base class methods"
    view = ImageView()
    tool = Tool(view)
    assert tool.view() == view
    assert tool.button_pressed(None) is False
    assert tool.button_released(None) is False
    assert tool.motion(None) is None
    assert tool.cursor_type_at_point(0, 0) is None
    assert tool.cursor_at_point(0, 0) is None

    # test connect/disconnect
    handler_id = tool.connect("zoom-changed", lambda *args: None)
    tool.disconnect(handler_id)


def test_dragger_edge_cases(rose_png, mock_view):
    "Test Dragger tool edge cases"
    view = mock_view
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png.name), False)
    dragger = Dragger(view)
    view.set_tool(dragger)

    # button 3 should not block context menu
    event = MockEvent(button=3, x=10, y=10)
    assert dragger.button_pressed(event) is False

    # dragging and motion
    event = MockEvent(button=1, x=10, y=10)
    dragger.button_pressed(event)
    assert dragger.dragging is True

    event.x, event.y = 15, 15
    dragger.motion(event)
    assert dragger.drag_start == {"x": 15, "y": 15}

    dragger.button_released(event)
    assert dragger.dragging is False

    # cursor types
    assert dragger.cursor_type_at_point(10, 10) == "grab"
    dragger.dragging = True
    assert dragger.cursor_type_at_point(10, 10) == "grabbing"
    dragger.dragging = False
    assert dragger.cursor_type_at_point(-10, -10) is None


def test_selector_edge_cases(rose_png, mock_view):
    "Test Selector tool edge cases"
    view = mock_view
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png.name), False)
    selector = Selector(view)
    view.set_tool(selector)

    # button 3
    event = MockEvent(button=3, x=10, y=10)
    assert selector.button_pressed(event) is False

    # selector without selection
    assert selector.cursor_type_at_point(10, 10) == "crosshair"

    # motion without dragging
    selector.motion(MockEvent(button=1, x=10, y=10))

    # set/get selection convenience methods
    selection = Gdk.Rectangle()
    selection.x, selection.y, selection.width, selection.height = 5, 5, 5, 5
    selector.set_selection(selection)
    assert selector.get_selection().x == 5


def test_selector_dragger_tool(rose_png, mock_view):
    "Test SelectorDragger tool"
    view = mock_view
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png.name), False)
    tool = SelectorDragger(view)
    view.set_tool(tool)

    # LMB -> Selector
    event = MockEvent(button=1, x=10, y=10)
    tool.button_pressed(event)
    assert isinstance(tool._tool, Selector)

    # MMB -> Dragger
    event = MockEvent(button=2, x=10, y=10)
    tool.button_pressed(event)
    assert isinstance(tool._tool, Dragger)

    # RMB -> False
    event = MockEvent(button=3, x=10, y=10)
    assert tool.button_pressed(event) is False

    # motion and released
    tool.motion(event)
    tool.button_released(event)
    assert isinstance(tool._tool, Selector)

    # cursor
    assert tool.cursor_type_at_point(10, 10) == "se-resize"


def test_imageview_more_basics(rose_png):
    "Test more ImageView methods"
    view = ImageView()
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png.name), False)

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

    view.set_fitting(False)
    assert view.getzoom_is_fit() is False

    # interpolation
    view.set_interpolation(cairo.FILTER_BEST)
    assert view.get_interpolation() == cairo.FILTER_BEST

    # resolution ratio
    view.set_resolution_ratio(1.5)
    assert view.get_resolution_ratio() == 1.5


def test_imageview_events(rose_png, mock_view):
    "Test ImageView event handlers"
    view = mock_view
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png.name), False)

    # button events (mostly covered via tools, but call direct)
    event = MockEvent(button=1, x=10, y=10)
    view.do_button_press_event(event)
    view.do_motion_notify_event(event)
    view.do_button_release_event(event)

    # scroll event
    event = MockEvent(button=0, x=10, y=10, direction=Gdk.ScrollDirection.UP)
    view.do_scroll_event(event)
    assert view.get_zoom() > 1.0

    event.direction = Gdk.ScrollDirection.DOWN
    view.do_scroll_event(event)

    # configure event
    view.setzoom_is_fit(True)
    view.do_configure_event(None)


def test_imageview_draw(rose_png):
    "Test ImageView do_draw"
    view = ImageView()
    # Use a pixbuf with alpha to hit line 518
    pixbuf = GdkPixbuf.Pixbuf.new_from_file(rose_png.name)
    # Ensure it has alpha
    pixbuf_alpha = pixbuf.add_alpha(True, 0, 0, 0)
    view.set_pixbuf(pixbuf_alpha, False)

    # draw with selection
    selection = Gdk.Rectangle()
    selection.x, selection.y, selection.width, selection.height = 5, 5, 5, 5
    view.set_selection(selection)

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 100, 100)
    context = cairo.Context(surface)
    view.do_draw(context)

    # draw without pixbuf
    view.set_pixbuf(None)
    view.do_draw(context)


def test_imageview_coordinate_conversions(rose_png):
    "Test ImageView coordinate conversion methods"
    view = ImageView()
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png.name), False)
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


def test_imageview_zoom_to_selection(rose_png):
    "Test zoom_to_selection"
    view = ImageView()
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png.name), False)
    selection = Gdk.Rectangle()
    selection.x, selection.y, selection.width, selection.height = 5, 5, 5, 5
    view.set_selection(selection)
    view.zoom_to_selection(1.1)


def test_selector_drag_edges(rose_png, mock_view):
    "Test Selector edge dragging logic"
    view = mock_view
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png.name), False)
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
    selector.cursor_type_at_point(20, 30)
    assert selector.h_edge == "lower"
    assert selector.v_edge == "mid"

    # Right edge
    selector.cursor_type_at_point(40, 30)
    assert selector.h_edge == "upper"
    assert selector.v_edge == "mid"

    # Top edge
    selector.cursor_type_at_point(30, 20)
    assert selector.h_edge == "mid"
    assert selector.v_edge == "lower"

    # Bottom edge
    selector.cursor_type_at_point(30, 40)
    assert selector.h_edge == "mid"
    assert selector.v_edge == "upper"

    # Corner (Top-Left) - Using values inside the CURSOR_PIXELS range but hitting the edges
    selector.cursor_type_at_point(21, 21)
    assert selector.h_edge == "lower"
    assert selector.v_edge == "lower"

    # Dragging an edge
    event = MockEvent(button=1, x=20, y=30)
    selector.button_pressed(event)
    event.x = 10
    selector.motion(event)
    new_sel = view.get_selection()
    assert new_sel.x == 10
    assert new_sel.width == 30
    selector.button_released(event)


def test_dragger_dnd_start(rose_png, mock_view):
    "Test Dragger DND start logic"
    view = mock_view
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png.name), False)
    dragger = Dragger(view)
    view.set_tool(dragger)

    # Mock drag_check_threshold to return True
    view.drag_check_threshold = MagicMock(return_value=True)
    # Mock emit to return True for dnd-start
    view.emit = MagicMock(return_value=True)

    event = MockEvent(button=1, x=10, y=10)
    dragger.button_pressed(event)

    # Move enough to trigger DND (clamped offset shouldn't move if already at edge)
    event.x = 100
    dragger.motion(event)

    assert dragger.dragging is False
    view.emit.assert_any_call("dnd-start", 100, 10, 1)


def test_imageview_clamping(rose_png):
    "Test ImageView offset clamping"
    view = ImageView()
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png.name), False)
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


def test_zoom_clamping():
    "Test zoom clamping"
    view = ImageView()
    view._set_zoom(1000)
    assert view.get_zoom() == 100
    view._set_zoom(0.00001)
    assert view.get_zoom() == 0.001


def test_selector_flip_edges(rose_png, mock_view):
    "Test Selector edge flipping when dragging"
    view = mock_view
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png.name), False)
    selector = Selector(view)
    view.set_tool(selector)

    # Start dragging a new selection from (50, 50) to (60, 60)
    event = MockEvent(button=1, x=50, y=50)
    selector.button_pressed(event)

    event.x, event.y = 60, 60
    selector.motion(event)
    sel = view.get_selection()
    assert sel.x == 50
    assert sel.width == 10

    # Drag past the start point to flip edge
    event.x = 40
    selector.motion(event)
    sel = view.get_selection()
    assert sel.x == 40
    assert sel.width == 10


def test_imageview_no_pixbuf_offset():
    "Test set_offset when pixbuf is None"
    view = ImageView()
    view.set_offset(10, 10)
    assert view.get_offset() is None


def test_update_cursor_none(mock_view, rose_png):
    "Test update_cursor when cursor_at_point returns None"
    view = mock_view
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png.name), False)
    view.get_tool().cursor_at_point = MagicMock(return_value=None)
    view.update_cursor(10, 10)
    # Should not crash and not call win.set_cursor
    view.get_window.return_value.set_cursor.assert_not_called()


def test_selector_update_selection_direct(rose_png):
    "Test Selector._update_selection directly to hit mid/mid branch"
    view = ImageView()
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png.name), False)
    # Ensure it has an allocation for coordinate conversion if needed,
    # though here we use scale factor 1.
    selector = Selector(view)

    # Manually set dragging and drag_start
    selector.dragging = True
    selector.drag_start = {"x": 10, "y": 10}

    # h_edge and v_edge are None, will be set to "mid" in _update_selection
    event = MockEvent(button=1, x=20, y=20)
    selector._update_selection(event)

    sel = view.get_selection()
    assert sel.x == 10
    assert sel.y == 10
    assert sel.width == 10
    assert sel.height == 10


def test_selector_update_selection_edge_branches(rose_png):
    "Test Selector._update_selection edge branches"
    view = ImageView()
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png.name), False)

    # Set an initial selection
    initial_sel = Gdk.Rectangle()
    initial_sel.x, initial_sel.y, initial_sel.width, initial_sel.height = 20, 20, 20, 20
    view.set_selection(initial_sel)

    selector = Selector(view)
    selector.dragging = True

    # Test dragging only horizontal edge (v_edge is mid)
    selector.h_edge = "lower"
    selector.v_edge = "mid"
    selector.drag_start = {"x": 40, "y": None}

    event = MockEvent(button=1, x=10, y=30)
    selector._update_selection(event)

    sel = view.get_selection()
    assert sel.x == 10
    assert sel.width == 30
    assert sel.y == 20
    assert sel.height == 20

    # Test dragging only vertical edge (h_edge is mid)
    # rose_png height is 46. y=20 + height=20 = 40.
    selector.h_edge = "mid"
    selector.v_edge = "upper"
    selector.drag_start = {"x": None, "y": 20}

    event = MockEvent(button=1, x=30, y=40)
    selector._update_selection(event)

    sel = view.get_selection()
    assert sel.x == 10  # from previous selection
    assert sel.width == 30
    assert sel.y == 20
    assert sel.height == 20


def test_selector_cursor_dragging_branches(rose_png, mock_view):
    "Test Selector.cursor_type_at_point dragging branches"
    view = mock_view
    view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(rose_png.name), False)
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
    selector.cursor_type_at_point(30, 30)
    assert selector.h_edge == "upper"
    assert selector.v_edge == "upper"
    assert selector.drag_start == {"x": 30, "y": 30}

    # 2. Hit h_edge=="mid" and v_edge!="mid" branch
    selector.h_edge = "mid"
    selector.v_edge = "lower"
    selector.drag_start = {}
    # to_widget_coords for (20, 20) and (40, 40) with scale 1, zoom 1, offset 0
    # is (20, 20) and (40, 40). sx2 is 40.
    selector.cursor_type_at_point(30, 20)
    assert selector.drag_start["x"] == 40

    # test case where "x" is already in drag_start
    selector.drag_start = {"x": 50}
    selector.cursor_type_at_point(30, 20)
    assert selector.drag_start["x"] == 50

    # 3. Hit h_edge!="mid" and v_edge=="mid" branch
    selector.h_edge = "lower"
    selector.v_edge = "mid"
    selector.drag_start = {}
    # sy2 is 40
    selector.cursor_type_at_point(20, 30)
    assert selector.drag_start["y"] == 40

    # test case where "y" is already in drag_start
    selector.drag_start = {"y": 50}
    selector.cursor_type_at_point(20, 30)
    assert selector.drag_start["y"] == 50
