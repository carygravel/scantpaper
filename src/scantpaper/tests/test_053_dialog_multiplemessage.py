"""test MultipleMessage class."""

from __future__ import annotations

import gi

from scantpaper.const import DIALOG_ROW_SPACING
from scantpaper.dialog import (
    COL_MESSAGE,
    MultipleMessage,
    filter_message,
    munge_message,
)

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk  # noqa: E402


def test_1() -> None:
    """Test MultipleMessage class."""
    window = Gtk.Window()

    dialog = MultipleMessage(title="title", transient_for=window)
    assert isinstance(dialog, MultipleMessage), "Created dialog"

    dialog.add_row(
        {
            "page": 1,
            "process": "scan",
            "message_type": "error",
            "text": "message",
            "store_response": True,
        }
    )
    assert dialog.grid_rows == 2, "1 message"

    dialog.add_row(
        {"page": 2, "process": "scan", "message_type": "warning", "text": "message2"}
    )
    assert dialog.grid_rows == 3, "2 messages"

    dialog.cbn.set_active(True)
    assert dialog.list_messages_to_ignore("ok") == ["message"], (
        "list_messages_to_ignore"
    )

    dialog.add_row(
        {
            "page": 1,
            "process": "scan",
            "message_type": "error",
            "text": "my message3\n",
            "store_response": True,
        }
    )
    assert dialog.cbn.get_inconsistent(), "inconsistent if states different"
    dialog.cbn.set_active(False)
    dialog.cbn.set_active(True)
    assert dialog.list_messages_to_ignore("ok") == [
        "message",
        "my message3",
    ], "chop trailing whitespace"

    dialog = MultipleMessage(title="title", transient_for=window)
    dialog.add_message(
        {
            "page": 1,
            "process": "scan",
            "message_type": "error",
            "text": "[image2 @ 0x1338180] Encoder did not produce proper pts, making some up.",
        }
    )
    assert dialog.grid_rows == 2, "add_message single message"

    responses = {}
    dialog = MultipleMessage(title="title", transient_for=window)
    dialog.add_message(
        {
            "page": 1,
            "process": "scan",
            "message_type": "error",
            "store_response": True,
            "responses": responses,
            "text": "[image2 @ 0xc596e0] Using AVStream.codec to pass codec parameters "
            """to muxers is deprecated, use AVStream.codecpar instead.
[image2 @ 0x1338180] Encoder did not produce proper pts, making some up.""",
        }
    )
    assert dialog.grid_rows == 3, "add_message added 2 messages"
    dialog.grid.get_child_at(4, 1).set_active(True)
    assert dialog.cbn.get_inconsistent(), "inconsistent if states different"

    dialog.grid.get_child_at(4, 2).set_active(True)
    dialog.store_responses("ok", responses)
    assert len(responses.keys()) == 2, "stored 2 responses"

    assert dialog.cbn.get_inconsistent() is False, "consistent as states same"

    dialog = MultipleMessage(title="title", transient_for=window)
    dialog.add_message(
        {
            "page": 1,
            "process": "scan",
            "message_type": "error",
            "store_response": True,
            "responses": responses,
            "text": "[image2 @ 0xc596e0] Using AVStream.codec to pass codec parameters "
            """to muxers is deprecated, use AVStream.codecpar instead.
[image2 @ 0x1338180] Encoder did not produce proper pts, making some up.""",
        }
    )
    assert dialog.grid_rows == 1, "add_message added no messages"

    assert munge_message(
        "(gimp:26514): GLib-GObject-WARNING : g_object_set_valist: object class "
        """'GeglConfig' has no property named 'cache-size'
(gimp:26514): GEGL-gegl-operation.c-WARNING : Cannot change name of operation class """
        '0xE0FD30 from "gimp:point-layer-mode" to "gimp:dissolve-mode"',
    ) == [
        (
            "(gimp:26514): GLib-GObject-WARNING : g_object_set_valist: object class "
            "'GeglConfig' has no property named 'cache-size'"
        ),
        (
            "(gimp:26514): GEGL-gegl-operation.c-WARNING : Cannot change name of "
            'operation class 0xE0FD30 from "gimp:point-layer-mode" to "gimp:dissolve-mode"'
        ),
    ], "split gimp messages"

    assert munge_message(
        "[image2 @ 0xc596e0] Using AVStream.codec to pass codec parameters to "
        """muxers is deprecated, use AVStream.codecpar instead.
[image2 @ 0x1338180] Encoder did not produce proper pts, making some up.""",
    ) == [
        (
            "[image2 @ 0xc596e0] Using AVStream.codec to pass codec parameters to "
            "muxers is deprecated, use AVStream.codecpar instead."
        ),
        "[image2 @ 0x1338180] Encoder did not produce proper pts, making some up.",
    ], "split unpaper messages"

    expected = (
        """Exception 400: memory allocation failed

This error is normally due to ImageMagick exceeding its resource limits. These """
        """can be extended by editing its policy file, which on my system is found at """
        "/etc/ImageMagick-6/policy.xml Please see the ImageMagick resource "
        "documentation for more information: "
        "https://imagemagick.org/script/resources.php"
    )
    assert munge_message("Exception 400: memory allocation failed") == expected, (
        "extend imagemagick Exception 400"
    )

    assert munge_message("""(gimp:26514): GLib-GObject-WARNING
Some other error""") == ["(gimp:26514): GLib-GObject-WARNING", "Some other error"], (
        "split gimp message with other message"
    )

    assert (
        filter_message(
            "[image2 @ 0x1338180] Encoder did not produce proper pts, making some up."
        )
        == "[image2 @ %%x] Encoder did not produce proper pts, making some up."
    ), "Filter out memory address from unpaper warning"

    expected = (
        "[image2 @ %%x] Using AVStream.codec to pass codec parameters to "
        """muxers is deprecated, use AVStream.codecpar instead.
[image2 @ %%x] Encoder did not produce proper pts, making some up."""
    )
    assert (
        filter_message(
            "[image2 @ 0xc596e0] Using AVStream.codec to pass codec parameters "
            """to muxers is deprecated, use AVStream.codecpar instead.
[image2 @ 0x1338180] Encoder did not produce proper pts, making some up."""
        )
        == expected
    ), "Filter out double memory address from unpaper warning"

    assert (
        filter_message("Error processing with tesseract: Detected 440 diacritics")
        == "Error processing with tesseract: Detected %%d diacritics"
    ), "Filter out integer from tesseract warning"

    assert (
        filter_message(
            "Error processing with tesseract: Warning. Invalid resolution 0 dpi. "
            "Using 70 instead."
        )
        == "Error processing with tesseract: Warning. Invalid resolution %%d dpi. "
        "Using %%d instead."
    ), "Filter out 1 and 2 digit integers from tesseract warning"

    assert (
        filter_message(
            "[image2 @ 0x1338180] Encoder did not produce proper pts, making some up. \n "
        )
        == "[image2 @ %%x] Encoder did not produce proper pts, making some up."
    ), "Filter out trailing whitespace"

    assert (
        filter_message(
            "[image2 @ 0x56054e417040] The specified filename "
            "'/tmp/scantpaper-ldks/OHSk_wKy5v.pnm' does not contain an image sequence "
            "pattern or a pattern is invalid."
        )
        == "[image2 @ %%x] The specified filename '/tmp/%%t' does not contain an "
        "image sequence pattern or a pattern is invalid."
    ), "Filter out temporary filename from unpaper warning"


def _descendants(widget: Gtk.Widget) -> list[Gtk.Widget]:
    """Return every widget below widget, depth first."""
    found = []
    child = widget.get_first_child()
    while child is not None:
        found.append(child)
        found.extend(_descendants(child))
        child = child.get_next_sibling()

    return found


def test_unknown_page_is_an_empty_cell() -> None:
    """A message without a page number leaves the Page cell empty."""
    dialog = MultipleMessage()
    dialog.add_row(
        {
            "page": None,
            "process": "scan",
            "message_type": "error",
            "text": "message",
        }
    )
    dialog.add_row(
        {
            "page": 3,
            "process": "scan",
            "message_type": "error",
            "text": "another message",
        }
    )

    unknown_page = dialog.grid.get_child_at(0, 1)
    known_page = dialog.grid.get_child_at(0, 2)
    assert isinstance(unknown_page, Gtk.Label), "Page cell is a label"
    assert isinstance(known_page, Gtk.Label), "Page cell is a label"
    assert unknown_page.get_text() == "", "no placeholder text for an unknown page"
    assert known_page.get_text() == "3", "known page numbers are unchanged"


def test_global_hide_control_outside_message_list() -> None:
    """The global control is a fixed row after the scrolling message list."""
    dialog = MultipleMessage(title="title", transient_for=Gtk.Window())
    dialog.add_row(
        {
            "page": 1,
            "process": "scan",
            "message_type": "error",
            "text": "message",
            "store_response": True,
        }
    )

    assert dialog.scrolled_window.get_vexpand(), "message list expands vertically"
    assert dialog.grid in _descendants(dialog.scrolled_window), "grid scrolls"
    assert dialog.grid.get_valign() == Gtk.Align.START, "rows keep their height"
    assert dialog.grid.get_column_spacing() == DIALOG_ROW_SPACING, "column spacing"
    assert dialog.grid.get_row_spacing() == DIALOG_ROW_SPACING, "row spacing"

    content = dialog.get_content_area()
    assert dialog.global_row.get_parent() is content, "fixed row in content area"
    assert dialog.global_row.get_prev_sibling() is dialog.scrolled_window, (
        "fixed row follows the scrolling list"
    )
    assert dialog.cbl.get_parent() is dialog.global_row, "label in fixed row"
    assert dialog.cbn.get_parent() is dialog.global_row, "checkbox in fixed row"

    scrolled = _descendants(dialog.scrolled_window)
    assert dialog.cbl not in scrolled, "label is outside the scrolling list"
    assert dialog.cbn not in scrolled, "checkbox is outside the scrolling list"


def test_message_text_is_a_selectable_label() -> None:
    """Message text is selectable and does not take text input focus.

    A Gtk.TextView would create an input-method context, and closing the
    dialog with the text focused crashes the ibus GTK4 module when it calls
    gdk_x11_surface_get_xid(NULL) on focus-out.
    """
    dialog = MultipleMessage()
    dialog.add_row(
        {
            "page": 1,
            "process": "scan",
            "message_type": "error",
            "text": "message",
            "store_response": True,
        }
    )
    label = dialog.grid.get_child_at(COL_MESSAGE, 1)

    assert isinstance(label, Gtk.Label), "message text is a label"
    assert label.get_selectable(), "message text can be selected"
    assert label.get_wrap(), "message text wraps"
    dialog.cbn.set_active(True)
    assert dialog.list_messages_to_ignore("ok") == ["message"]


def test_escape_closes_with_a_response() -> None:
    """Escape returns a response instead of just destroying the dialog."""
    dialog = MultipleMessage()
    dialog.set_visible(True)
    responses = []
    dialog.connect("response", lambda _dialog, response: responses.append(response))

    assert dialog._on_key_pressed(None, Gdk.KEY_Escape, 0, Gdk.ModifierType(0))
    assert responses == [Gtk.ResponseType.CLOSE]
    assert not dialog.get_visible(), "dialog is hidden"


def test_escape_ignores_other_keys() -> None:
    """Other keys still propagate."""
    dialog = MultipleMessage()

    assert not dialog._on_key_pressed(None, Gdk.KEY_a, 0, Gdk.ModifierType(0))


def test_close_request_closes_with_a_response() -> None:
    """The window close control returns a response and hides the dialog."""
    dialog = MultipleMessage()
    dialog.set_visible(True)
    responses = []
    dialog.connect("response", lambda _dialog, response: responses.append(response))

    assert dialog._on_close_request(dialog)
    assert responses == [Gtk.ResponseType.CLOSE]
    assert not dialog.get_visible(), "dialog is hidden"
