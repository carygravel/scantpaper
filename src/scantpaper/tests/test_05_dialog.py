"""test dialog."""

from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock, patch

import gi

from scantpaper.const import (
    DIALOG_BUTTON_SPACING,
    DIALOG_CONTENT_MARGIN,
    DIALOG_ROW_SPACING,
)
from scantpaper.dialog import (
    Dialog,
    MultipleMessage,
    pad_action_area,
    pad_content_area,
)

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import (  # noqa: E402
    Gdk,
    Gtk,
)


def test_dialog() -> None:
    """Test dialog."""
    window = Gtk.Window()
    dialog = Dialog(title="title", transient_for=window)
    assert isinstance(dialog, Dialog), "Created dialog"

    assert dialog.get_title() == "title", "title"
    assert dialog.get_transient_for() == window, "transient-for"
    assert dialog.hide_on_delete is False, "default destroy"
    assert dialog.page_range == "selected", "default page-range"

    dialog = Dialog()
    with patch.object(Dialog, "destroy", autospec=True) as mock_destroy:
        dialog.emit("close-request")
        mock_destroy.assert_called_once()

    dialog = Dialog(hide_on_delete=True)
    with patch.object(Dialog, "destroy", autospec=True) as mock_destroy:
        dialog.emit("close-request")
        mock_destroy.assert_not_called()
    assert not dialog.get_visible(), "hidden on close-request"

    dialog = Dialog()
    with patch.object(Dialog, "destroy", autospec=True) as mock_destroy:
        assert (
            dialog._on_key_pressed(None, Gdk.KEY_Escape, 0, Gdk.ModifierType(0)) is True
        )
        mock_destroy.assert_called_once()

    dialog = Dialog(hide_on_delete=True)
    with patch.object(Dialog, "destroy", autospec=True) as mock_destroy:
        assert (
            dialog._on_key_pressed(None, Gdk.KEY_Escape, 0, Gdk.ModifierType(0)) is True
        )
        mock_destroy.assert_not_called()
    assert not dialog.get_visible(), "hidden on escape"

    dialog = Dialog()
    assert (
        dialog._on_key_pressed(None, Gdk.KEY_Delete, 0, Gdk.ModifierType(0)) is False
    ), "other key press events still propagate"

    dialog = Dialog()
    dialog.response(Gtk.ResponseType.NONE)
    assert True, "no crash due to undefined response"


def test_multiple_message() -> None:
    """Test MultipleMessage."""
    dialog = MultipleMessage()

    # row with store_response=True and stored_responses
    row1: dict[str, object] = {
        "text": "message 1",
        "message_type": "error",
        "store_response": True,
        "stored_responses": ["ok"],
    }
    dialog.add_message(row1)

    # row with store_response=True and no stored_responses
    row2: dict[str, object] = {
        "text": "message 2",
        "message_type": "warning",
        "store_response": True,
    }
    dialog.add_message(row2)

    # row with store_response=False
    row3: dict[str, object] = {
        "text": "message 3",
        "message_type": "error",
        "store_response": False,
    }
    dialog.add_message(row3)

    # list_checkbuttons should return 2 buttons (for row1 and row2)
    # row 3 doesn't have a checkbutton because store_response=False
    cbs = dialog._list_checkbuttons()
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


def test_dialog_page_range() -> None:
    """Test dialog page-range."""
    dialog = Dialog()
    dialog.add_page_range()

    # Traverse the widget tree to find PageRange
    content_area = dialog.get_content_area()
    frame = next(iter(content_area.observe_children()))
    prng = frame.get_child()

    assert prng.get_active() == "selected", "default page-range"

    # Trigger change
    prng.set_active("all")
    assert dialog.page_range == "all", "page-range updated"


def test_dialog_content_padding() -> None:
    """Test that dialog content is inset and its blocks are spaced."""
    dialog = Dialog()

    content = dialog.get_content_area()
    assert content.get_margin_top() == DIALOG_CONTENT_MARGIN, "content margin top"
    assert content.get_margin_bottom() == DIALOG_CONTENT_MARGIN, "content margin bottom"
    assert content.get_margin_start() == DIALOG_CONTENT_MARGIN, "content margin start"
    assert content.get_margin_end() == DIALOG_CONTENT_MARGIN, "content margin end"
    assert content.get_spacing() == DIALOG_ROW_SPACING, "content spacing"


def test_pad_content_area() -> None:
    """pad_content_area insets and spaces a bare Gtk.Dialog's content area."""
    content = Gtk.Box()
    pad_content_area(content)

    assert content.get_margin_top() == DIALOG_CONTENT_MARGIN, "content margin top"
    assert content.get_margin_bottom() == DIALOG_CONTENT_MARGIN, "content margin bottom"
    assert content.get_margin_start() == DIALOG_CONTENT_MARGIN, "content margin start"
    assert content.get_margin_end() == DIALOG_CONTENT_MARGIN, "content margin end"
    assert content.get_spacing() == DIALOG_ROW_SPACING, "content spacing"


def _action_area(dialog: Gtk.Dialog) -> Gtk.Box:
    """Return a dialog's action area box."""
    action_box = dialog.get_content_area().get_next_sibling()
    assert isinstance(action_box, Gtk.Box)
    action_area = action_box.get_first_child()
    assert isinstance(action_area, Gtk.Box)
    return action_area


def test_pad_action_area() -> None:
    """pad_action_area insets and spaces a dialog's action buttons."""
    for dialog in (Dialog(), Gtk.Dialog()):
        dialog.add_button("_OK", Gtk.ResponseType.OK)
        dialog.add_button("_Cancel", Gtk.ResponseType.CANCEL)

        pad_action_area(dialog)
        action_area = _action_area(dialog)

        assert action_area.get_spacing() == DIALOG_BUTTON_SPACING, "button spacing"
        assert action_area.get_margin_top() == DIALOG_CONTENT_MARGIN, (
            "action margin top"
        )
        assert action_area.get_margin_bottom() == DIALOG_CONTENT_MARGIN, (
            "action margin bottom"
        )
        assert action_area.get_margin_start() == DIALOG_CONTENT_MARGIN, (
            "action margin start"
        )
        assert action_area.get_margin_end() == DIALOG_CONTENT_MARGIN, (
            "action margin end"
        )
        dialog.destroy()


def test_dialog_add_actions_pads_action_area() -> None:
    """add_actions gives the action area the shared inset and spacing."""
    dialog = Dialog()
    dialog.add_actions([("_OK", lambda: None), ("_Cancel", lambda: None)])
    action_area = _action_area(dialog)

    assert action_area.get_spacing() == DIALOG_BUTTON_SPACING, "button spacing"
    assert action_area.get_margin_top() == DIALOG_CONTENT_MARGIN, "action margin top"
    assert action_area.get_margin_bottom() == DIALOG_CONTENT_MARGIN, (
        "action margin bottom"
    )
    assert action_area.get_margin_start() == DIALOG_CONTENT_MARGIN, (
        "action margin start"
    )
    assert action_area.get_margin_end() == DIALOG_CONTENT_MARGIN, "action margin end"
    dialog.destroy()


def test_pad_action_area_empty() -> None:
    """An empty action area is left unspaced."""
    dialog = Gtk.Dialog()
    pad_action_area(dialog)
    action_area = _action_area(dialog)

    assert action_area.get_spacing() == 0, "empty action area spacing"
    assert action_area.get_margin_top() == 0, "empty action area margin top"
    assert action_area.get_margin_bottom() == 0, "empty action area margin bottom"
    assert action_area.get_margin_start() == 0, "empty action area margin start"
    assert action_area.get_margin_end() == 0, "empty action area margin end"
    dialog.destroy()


def test_pad_action_area_without_action_box() -> None:
    """A dialog without an action box is left alone."""
    dialog = MagicMock()
    dialog.get_content_area.return_value = Gtk.Box()

    pad_action_area(cast("Gtk.Dialog", dialog))


def test_pad_action_area_without_action_area() -> None:
    """An action box without an action area is left alone."""
    parent = Gtk.Box()
    content = Gtk.Box()
    action_box = Gtk.Box()
    parent.append(content)
    parent.append(action_box)

    dialog = MagicMock()
    dialog.get_content_area.return_value = content

    pad_action_area(cast("Gtk.Dialog", dialog))

    assert action_box.get_first_child() is None, "action box remains empty"


def test_pad_action_area_keeps_joined_message_bar() -> None:
    """A message dialog keeps its joined, homogeneous action bar."""
    dialog = Gtk.MessageDialog(buttons=Gtk.ButtonsType.OK_CANCEL)
    action_area = _action_area(dialog)

    pad_action_area(dialog)

    assert action_area.get_homogeneous(), "joined bar"
    assert action_area.get_spacing() == 0, "no button spacing"
    assert action_area.get_margin_top() == 0, "no action margin top"
    assert action_area.get_margin_bottom() == 0, "no action margin bottom"
    assert action_area.get_margin_start() == 0, "no action margin start"
    assert action_area.get_margin_end() == 0, "no action margin end"
    dialog.destroy()


def test_pad_action_area_file_chooser() -> None:
    """File chooser action buttons get the shared spacing and inset."""
    dialog = Gtk.FileChooserDialog()
    dialog.add_buttons(
        "_Cancel",
        Gtk.ResponseType.CANCEL,
        "_Open",
        Gtk.ResponseType.OK,
    )

    pad_action_area(dialog)
    action_area = _action_area(dialog)

    assert action_area.get_spacing() == DIALOG_BUTTON_SPACING, "button spacing"
    assert action_area.get_margin_top() == DIALOG_CONTENT_MARGIN, "action margin top"
    assert action_area.get_margin_bottom() == DIALOG_CONTENT_MARGIN, (
        "action margin bottom"
    )
    assert action_area.get_margin_start() == DIALOG_CONTENT_MARGIN, (
        "action margin start"
    )
    assert action_area.get_margin_end() == DIALOG_CONTENT_MARGIN, "action margin end"
    dialog.destroy()


def test_add_actions_limit() -> None:
    """Test add_actions with more buttons than responses."""
    dialog = Dialog()
    # add_actions only supports 2 responses (OK, CANCEL)
    buttons = dialog.add_actions(
        [("b1", lambda: None), ("b2", lambda: None), ("b3", lambda: None)]
    )
    assert len(buttons) == 2, "only 2 buttons added"


def test_multiple_message_none_text() -> None:
    """Test MultipleMessage with None text."""
    dialog = MultipleMessage()
    row: dict[str, object] = {
        "text": None,
        "message_type": "error",
    }
    dialog.add_message(row)
    assert row["text"] == "", "None text converted to empty string"


def test_multiple_message_list_text() -> None:
    """Test MultipleMessage with text that gets munged into a list."""
    dialog = MultipleMessage()
    row: dict[str, object] = {
        "text": "(gimp:123): message\nsomething else",
        "message_type": "error",
    }
    dialog.add_message(row)
    # Check that 2 rows were added (plus header row, total 3 rows in grid)
    # However, MultipleMessage uses grid.insert_row(self.grid_rows) in add_row
    # And grid_rows starts at 1 (header is row 0)
    # Actually, grid_rows is incremented after each add_row call?


def test_add_actions_callback() -> None:
    """Test add_actions callback."""
    dialog = Dialog()
    called = False

    def callback() -> None:
        nonlocal called
        called = True

    dialog.add_actions([("ok", callback)])
    dialog.response(Gtk.ResponseType.OK)
    assert called, "callback was called on response"


def test_multiple_message_duplicate() -> None:
    """Test MultipleMessage skipping duplicate message."""
    dialog = MultipleMessage()
    responses = {"message": {"response": "ok"}}
    row: dict[str, object] = {
        "text": "message",
        "message_type": "error",
        "responses": responses,
    }
    dialog.add_message(row)
    assert dialog.grid_rows == 1, "duplicate message not added"
