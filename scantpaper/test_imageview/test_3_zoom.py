"Test zoom"

import pytest
from imageview import ImageView
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf  # pylint: disable=wrong-import-position


def test_1():
    """Test zoom"""
    window = Gtk.Window()
    window.set_size_request(300, 200)
    view = ImageView()
    scale = view.get_scale_factor()
    window.add(view)
    window.show_all()
    view.set_pixbuf(
        GdkPixbuf.Pixbuf.new_from_file("scantpaper/test_imageview/bigpic.svg"), True
    )
    assert view.get_zoom() == pytest.approx(0.2 * scale, 0.0001), "shrunk"
    view.set_zoom(1)

    # the transp-green picture is 100x100 which is less than 200.
    view.set_pixbuf(
        GdkPixbuf.Pixbuf.new_from_file("scantpaper/test_imageview/transp-green.svg"),
        False,
    )
    assert view.get_zoom() == 1, "picture fully visible"
    view.set_pixbuf(
        GdkPixbuf.Pixbuf.new_from_file("scantpaper/test_imageview/transp-green.svg"),
        True,
    )
    assert view.get_zoom() == 2 * scale, "zoomed"
    # view.set_fitting(True)
    # assert view.get_zoom() == scale, "no need to zoom"
    # view.set_pixbuf(
    #     GdkPixbuf.Pixbuf.new_from_file("scantpaper/test_imageview/transp-green.svg"),
    #     True,
    # )
    # assert view.get_zoom() == scale, "no need to zoom even when True"
    # view.set_pixbuf(
    #     GdkPixbuf.Pixbuf.new_from_file("scantpaper/test_imageview/bigpic.svg"), True
    # )
    # assert view.get_zoom() == pytest.approx(0.2 * scale, 0.0001), "still shrunk"
