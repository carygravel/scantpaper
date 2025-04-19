"Test selector tool"

from dataclasses import dataclass
import gi
from imageview import ImageView, Selector

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf  # pylint: disable=wrong-import-position


@dataclass
class MockEvent:
    "mock enough of the event class to test it"

    button: int
    x: int  # pylint: disable=invalid-name
    y: int  # pylint: disable=invalid-name


def test_1():
    "Test selector tool"
    window = Gtk.Window()
    window.set_size_request(300, 200)
    view = ImageView()
    window.add(view)
    view.set_tool(Selector(view))
    view.set_pixbuf(
        GdkPixbuf.Pixbuf.new_from_file("scantpaper/test_imageview/transp-green.svg"),
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
