"test dialog"

from pathlib import Path
import subprocess
import tempfile
from dialog import Dialog
from dialog.pagecontrols import PageControls
from document import Document
import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk  # pylint: disable=wrong-import-position


def test_dialog():
    "test dialog"
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


def test_page_controls(mainloop_with_timeout, clean_up_files):
    "test PageControls"
    dialog = PageControls(title="title", transient_for=Gtk.Window())
    assert isinstance(dialog, PageControls), "Created PageControls dialog"

    slist = Document()
    subprocess.run(["convert", "rose:", "test.pnm"], check=True)
    with tempfile.TemporaryDirectory() as tempdir:
        kwargs = {
            "filename": "test.pnm",
            "resolution": 72,
            "page": 1,
            "dir": tempdir,
        }
        slist.import_scan(**kwargs)
        loop1 = mainloop_with_timeout()
        kwargs["finished_callback"] = lambda response: loop1.quit()
        loop1.run()
        dialog.page_number_start = 5
        dialog.document = slist
        dialog.reset_start_page()
        assert dialog.page_number_start == 2, "PageControls.reset_start_page()"

    clean_up_files([Path(tempfile.gettempdir()) / "document.db"])
