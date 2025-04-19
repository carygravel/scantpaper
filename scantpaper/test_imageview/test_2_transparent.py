"Test transparency"

from imageview import ImageView
import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import (  # pylint: disable=wrong-import-position
    GLib,
    Gdk,
    GdkPixbuf,
    Gtk,
)


def test_1():
    """Test transparency"""
    window = Gtk.Window()
    window.set_size_request(300, 200)
    css_provider_alpha = Gtk.CssProvider()
    Gtk.StyleContext.add_provider_for_screen(  # pylint: disable=no-member
        window.get_screen(), css_provider_alpha, 0  # pylint: disable=no-member
    )
    css_provider_alpha.load_from_data(
        b"""
    .imageview.transparent {
        background-color: #ff0000;
        background-image: none;
    }
    .imageview {
        background-image: url('scantpaper/test_imageview/transp-blue.svg');
    }
"""
    )
    view = ImageView()
    view.set_pixbuf(
        GdkPixbuf.Pixbuf.new_from_file("scantpaper/test_imageview/transp-green.svg"),
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
