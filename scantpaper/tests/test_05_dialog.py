"test dialog"

from dialog import Dialog, MultipleMessage
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


def test_multiple_message():
    "test MultipleMessage"

    dialog = MultipleMessage()

    # row with store_response=True and stored_responses
    row1 = {
        "text": "message 1",
        "message_type": "error",
        "store_response": True,
        "stored_responses": ["ok"],
    }
    dialog.add_message(row1)

    # row with store_response=True and no stored_responses
    row2 = {
        "text": "message 2",
        "message_type": "warning",
        "store_response": True,
    }
    dialog.add_message(row2)

    # row with store_response=False
    row3 = {
        "text": "message 3",
        "message_type": "error",
        "store_response": False,
    }
    dialog.add_message(row3)

    # list_checkbuttons should return 2 buttons (for row1 and row2)
    # row 3 doesn't have a checkbutton because store_response=False
    cbs = dialog._list_checkbuttons()  # pylint: disable=protected-access
    assert len(cbs) == 2, "2 checkbuttons"

    # Activate all checkbuttons
    for cb in cbs:
        cb.set_active(True)

    # If response is "ok", and message 1 has stored_responses ["ok"], it should be returned
    # Message 2 has no stored_responses, so it should also be returned
    messages = dialog.list_messages_to_ignore("ok")
    assert "message 1" in messages
    assert "message 2" in messages

    # If response is "cancel", and message 1 has stored_responses ["ok"], it should NOT be returned
    # Message 2 has no stored_responses, so it should still be returned
    messages = dialog.list_messages_to_ignore("cancel")
    assert "message 1" not in messages
    assert "message 2" in messages

    # Deactivate checkbutton for row 2
    cbs[1].set_active(False)
    messages = dialog.list_messages_to_ignore("ok")
    assert "message 1" in messages
    assert "message 2" not in messages


def test_dialog_page_range():
    "test dialog page-range"
    dialog = Dialog()
    dialog.add_page_range()

    # Traverse the widget tree to find PageRange
    content_area = dialog.get_content_area()
    frame = content_area.get_children()[0]
    prng = frame.get_child()

    assert prng.get_active() == "selected", "default page-range"

    # Trigger change
    prng.set_active("all")
    assert dialog.page_range == "all", "page-range updated"
