"test dialog"
from dialog import Dialog
import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk  # pylint: disable=wrong-import-position


def test_1():
    "test dialog"
    # Translation.set_domain('gscan2pdf')
    window = Gtk.Window()

    dialog = Dialog(title="title", transient_for=window)
    assert isinstance(dialog, Dialog), "Created dialog"

    assert dialog.get_title() == "title", "title"
    assert dialog.get_transient_for() == window, "transient-for"
    assert dialog.hide_on_delete is False, "default destroy"
    assert dialog.page_range == "selected", "default page-range"

    dialog = Dialog()

    finalized = False

    def on_finalized():
        nonlocal finalized
        finalized = True

    dialog.weak_ref(on_finalized)
    dialog.emit("delete_event", None)
    assert finalized, "destroyed on delete_event"

    dialog = Dialog(hide_on_delete=True)
    dialog.emit("delete_event", None)
    assert isinstance(dialog, Dialog), "not destroyed on delete_event"
    assert not dialog.get_visible(), "hidden on delete_event"

    finalized = False
    dialog = Dialog()
    event = Gdk.Event().new(Gdk.EventType.KEY_PRESS)
    event.keyval = Gdk.KEY_Escape
    dialog.weak_ref(on_finalized)
    dialog.emit("key_press_event", event)
    assert finalized, "destroyed on escape"

    dialog = Dialog(hide_on_delete=True)
    dialog.weak_ref(on_finalized)
    dialog.emit("key_press_event", event)
    assert isinstance(dialog, Dialog), "not destroyed on escape"
    assert not dialog.get_visible(), "hidden on escape"

    dialog = Dialog()

    def on_key_press_event(_widget, _event):
        assert event.keyval == Gdk.KEY_Delete, "other key press events still propagate"

    dialog.connect_after("key-press-event", on_key_press_event)
    event = Gdk.Event().new(Gdk.EventType.KEY_PRESS)
    event.keyval = Gdk.KEY_Delete
    dialog.emit("key_press_event", event)

    def on_close():
        pass

    dialog = Dialog()
    dialog.add_actions([("gtk-close", on_close)])
    dialog.response(Gtk.ResponseType.NONE)
    assert True, "no crash due to undefined response"
