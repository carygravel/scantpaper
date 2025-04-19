"Basic tests for imageview"

import tempfile
import subprocess
import gi
import pytest

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GdkPixbuf, Gtk  # pylint: disable=wrong-import-position
from imageview import (  # pylint: disable=wrong-import-position
    ImageView,
    Dragger,
    Selector,
)


def test_1():
    """Basic tests for imageview"""

    view = ImageView()
    assert isinstance(view, ImageView)
    assert isinstance(view.get_tool(), Dragger), "get_tool() defaults to dragger"

    def on_offset_changed(_widget, offset_x, offset_y):
        view.disconnect(signal)
        if view.get_scale_factor() <= 1:
            assert offset_x == 0, "emitted offset-changed signal x"
            assert offset_y == 12, "emitted offset-changed signal y"

    with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
        subprocess.run(["convert", "rose:", tmp.name], check=True)
        signal = view.connect("offset-changed", on_offset_changed)
        view.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file(tmp.name), True)

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
