"test dialog"

from dialog.crop import Crop
import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # pylint: disable=wrong-import-position


def test_1():
    "test dialog"
    dialog = Crop(transient_for=Gtk.Window(), page_width=100, page_height=100)
    assert isinstance(dialog, Crop), "Created dialog"
    assert (
        dialog.page_width == 100  # pylint: disable=comparison-with-callable
    ), "default page-width"
    assert (
        dialog.page_height == 100  # pylint: disable=comparison-with-callable
    ), "default page-height"

    flag = False
    mlp = GLib.MainLoop()

    def on_changed_selection(*_):
        nonlocal flag
        flag = True
        mlp.quit()

    dialog.connect("changed-selection", on_changed_selection)
    selection = Gdk.Rectangle()
    selection.x, selection.y, selection.width, selection.height = 10, 10, 10, 10
    dialog.selection = selection
    GLib.timeout_add(2000, mlp.quit)  # to prevent it hanging
    mlp.run()
    assert flag, "updating selection emits signal"
    assert (
        dialog._sb_x.get_value() == 10  # pylint: disable=protected-access,no-member
    ), "updating selection changes spinbutton"
