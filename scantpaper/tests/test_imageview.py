"Basic tests for imageview"

from dataclasses import dataclass
import cairo
import gi
import pytest
from imageview import ImageView, Dragger, Selector

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import (  # pylint: disable=wrong-import-position
    GLib,
    Gdk,
    GdkPixbuf,
    Gtk,
)


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

    if False:
        assert isinstance(view.get_draw_rect(), Gdk.Rectangle)
        assert view.get_check_colors(), "get_check_colors()"

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

    if False:
        assert (
            Gtk.ImageView.Zoom.get_min_zoom() < Gtk.ImageView.Zoom.get_max_zoom()
        ), "Ensure that the gtkimageview.zooms_* functions are present and work as expected."
        assert view.get_black_bg() is not None, "get_black_bg()"
        assert view.get_show_frame() is not None, "get_show_frame()"
        assert view.get_interpolation() is not None, "get_interpolation()"
        assert view.get_show_cursor() is not None, "get_show_cursor()"

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

    if False:
        assert not view.get_draw_rect(), "correctly cleared draw rectangle"
        allocation = Gdk.Rectangle()
        allocation.x, allocation.y, allocation.width, allocation.height = 0, 0, 100, 100
        view.size_allocate(allocation)
        view.set_pixbuf(GdkPixbuf.Pixbuf(Gdk.colormap_get_system(), False, 8, 50, 50))
        rect = view.get_viewport()
        assert (
            rect.x == 0 and rect.y == 0 and rect.width == 50 and rect.height == 50
        ), "Ensure that getting the viewport of the view works as expected."
        assert hasattr(view, "get_check_colors") and callable(view.get_check_colors)
        rect = view.get_draw_rect()
        assert (
            rect.x == 25 and rect.y == 25 and rect.width == 50 and rect.height == 50
        ), "Ensure that getting the draw rectangle works as expected."
        view.set_pixbuf(GdkPixbuf.Pixbuf(Gdk.colormap_get_system(), False, 8, 200, 200))
        view.set_zoom(1)
        view.set_offset(0, 0)
        rect = view.get_viewport()
        assert (
            rect.x == 0 and rect.y == 0
        ), "Ensure that setting the offset works as expected."
        view.set_offset(100, 100)
        rect = view.get_viewport()
        assert (
            rect.x == 100 and rect.y == 100
        ), "Ensure that setting the offset works as expected."
        view.set_transp("color", 0xFF0000)
        (col1, col2) = view.get_check_colors()
        assert (
            col1 == 0xFF0000 and col2 == 0xFF0000
        ), "Ensure that setting the views transparency settings works as expected."
        view.set_transp("grid")
        # assert (
        #     GObject.TypeModule.list_values("Gtk3::ImageView::Transp") is not None
        # ), "Check GtkImageTransp enum."


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
    # view.set_fitting(True)
    # assert view.get_zoom() == scale, "no need to zoom"
    # view.set_pixbuf(
    #     GdkPixbuf.Pixbuf.new_from_file("scantpaper/tests/transp-green.svg"),
    #     True,
    # )
    # assert view.get_zoom() == scale, "no need to zoom even when True"
    # view.set_pixbuf(
    #     GdkPixbuf.Pixbuf.new_from_file("scantpaper/tests/bigpic.svg"), True
    # )
    # assert view.get_zoom() == pytest.approx(0.2 * scale, 0.0001), "still shrunk"


@dataclass
class MockEvent:
    "mock enough of the event class to test it"

    button: int
    x: int  # pylint: disable=invalid-name
    y: int  # pylint: disable=invalid-name


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
    event = MockEvent(button=0, x=7, y=5)
    view.get_tool().button_pressed(event)
    event.x = 93
    event.y = 67
    view.get_tool().button_pressed(event)
    view.get_tool().button_released(event)

    if view.get_scale_factor() <= 1:
        selection = view.get_selection()
        assert selection.x == 32, "get_selection x"
        assert selection.y == 38, "get_selection y"
        assert selection.width == 11, "get_selection width"
        assert selection.height == 7, "get_selection height"


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
