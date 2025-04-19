"Test interpolation (filters)"

import cairo
from imageview import ImageView
import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import (  # pylint: disable=wrong-import-position
    Gdk,
    GdkPixbuf,
    GLib,
    Gtk,
)


def test_1():
    "Test interpolation (filters)"
    window = Gtk.Window()
    window.set_size_request(300, 200)
    view = ImageView()
    view.set_pixbuf(
        GdkPixbuf.Pixbuf.new_from_file("scantpaper/test_imageview/2color.svg"), True
    )
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
