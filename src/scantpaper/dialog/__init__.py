"""subclass Gtk.Dialog to add some boilerplate."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, cast

import gi

from scantpaper.const import (
    DIALOG_BUTTON_SPACING,
    DIALOG_CONTENT_MARGIN,
    DIALOG_ROW_SPACING,
)
from scantpaper.i18n import _
from scantpaper.pagerange import PageRange

if TYPE_CHECKING:
    from collections.abc import Callable

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import (  # noqa: E402
    Gdk,
    GObject,
    Gtk,
)


def pad_content_area(content: Gtk.Box) -> None:
    """Inset a dialog's content from the window edge and space its blocks.

    Used by ``Dialog`` and by the few dialogs built on a bare ``Gtk.Dialog``.
    GTK3 took the inset from the theme; GTK4 does not, and a Gtk.Box spaces
    its children by 0, so both are set here.
    """
    content.set_spacing(DIALOG_ROW_SPACING)
    content.set_margin_top(DIALOG_CONTENT_MARGIN)
    content.set_margin_bottom(DIALOG_CONTENT_MARGIN)
    content.set_margin_start(DIALOG_CONTENT_MARGIN)
    content.set_margin_end(DIALOG_CONTENT_MARGIN)


def pad_action_area(dialog: Gtk.Dialog) -> None:
    """Inset and space a dialog's action buttons.

    GTK3 took the action area's inset and the gap between its buttons from
    the theme. GTK4's action area is a plain GtkBox with spacing 0, so restore
    both here. The action area is the first child of the box that follows the
    content area.

    A joined, homogeneous action area - the bar a message dialog presents -
    keeps its presentation. An empty action area is left alone so a dialog
    without action buttons does not gain blank space.
    """
    content = dialog.get_content_area()
    action_box = content.get_next_sibling()
    if action_box is None:
        return

    action_area = action_box.get_first_child()
    if action_area is None:
        return

    action_area = cast("Gtk.Box", action_area)
    if action_area.get_homogeneous():
        return

    if action_area.get_first_child() is None:
        return

    action_area.set_spacing(DIALOG_BUTTON_SPACING)
    action_area.set_margin_top(DIALOG_CONTENT_MARGIN)
    action_area.set_margin_bottom(DIALOG_CONTENT_MARGIN)
    action_area.set_margin_start(DIALOG_CONTENT_MARGIN)
    action_area.set_margin_end(DIALOG_CONTENT_MARGIN)


class Dialog(Gtk.Dialog):
    """subclass Gtk.Dialog to add some boilerplate."""

    hide_on_delete = GObject.Property(
        type=bool,
        default=False,
        nick="Hide on delete",
        blurb="Whether to destroy or hide the dialog when it is dismissed",
    )
    page_range = GObject.Property(
        type=str, default="selected", nick="page-range", blurb="Either selected or all"
    )

    def _on_close_request(self, _widget: Gtk.Widget) -> bool:
        """Handle the close-request signal (replaces the GTK3 delete-event)."""
        if self.hide_on_delete:
            self.hide()
            return True  # prevent the dialog from being destroyed

        self.destroy()
        return False

    def _on_key_pressed(
        self,
        _controller: Gtk.EventControllerKey,
        keyval: int,
        _keycode: int,
        _state: Gdk.ModifierType,
    ) -> bool:
        """Handle a key press via the GTK4 event controller."""
        if keyval == Gdk.KEY_Escape:
            if self.hide_on_delete:
                self.hide()
            else:
                self.destroy()
            return True
        return False

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialise ."""
        super().__init__(*args, **kwargs)

        # Inset the content from the window edge and space the blocks appended
        # to it. GTK3 took the inset from the theme; GTK4 does not, and a
        # Gtk.Box spaces its children by 0, so both are set here.
        pad_content_area(self.get_content_area())

        self.connect("close-request", self._on_close_request)
        self._key_controller = Gtk.EventControllerKey()
        self._key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(self._key_controller)

    def add_page_range(self) -> None:
        """Add a frame and radio buttons to content area."""
        frame = Gtk.Frame(label=_("Page Range"))
        self.get_content_area().append(frame)
        prng = PageRange()
        prng.set_active(self.page_range)

        def page_range_changed_callback(_widget: Gtk.Widget, data: str) -> None:
            self.page_range = data

        prng.connect("changed", page_range_changed_callback)
        frame.set_child(prng)

    def add_actions(
        self, button_list: list[tuple[str, Callable[[], object]]]
    ) -> list[Gtk.Button]:
        """Add buttons and link up their actions."""
        responses = [Gtk.ResponseType.OK, Gtk.ResponseType.CANCEL]
        buttons, callbacks = [], {}
        for button in button_list:
            text, callback = button
            if not responses:
                break
            response = responses.pop(0)
            callbacks[response] = callback
            buttons.append(self.add_button(text, response))

        self.set_default_response(Gtk.ResponseType.OK)
        pad_action_area(self)

        def on_response(_widget: Gtk.Widget, response: int) -> None:
            if response in callbacks:
                callbacks[response]()

        self.connect("response", on_response)
        return buttons


COL_MESSAGE = 3
COL_CHECKBUTTON = 4
MIN_ROWS_FOR_CHECKBOX = 2
TYPES = {
    "error": _("Error"),
    "warning": _("Warning"),
    "info": _("Info"),
}


class MultipleMessage(Dialog):
    """Subclass of Dialog to display messages and let the user respond or ignore."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialise MultipleMessage."""
        super().__init__(*args, **kwargs)

        # to ensure dialog can't grow too big if we have too many messages
        scwin = Gtk.ScrolledWindow()
        self.get_content_area().append(scwin)
        self.grid = Gtk.Grid()
        self.grid_rows = 0
        self.stored_responses = {}
        self.grid.attach(Gtk.Label(label=_("Page")), 0, self.grid_rows, 1, 1)
        self.grid.attach(Gtk.Label(label=_("Process")), 1, self.grid_rows, 1, 1)
        self.grid.attach(Gtk.Label(label=_("Message type")), 2, self.grid_rows, 1, 1)
        self.grid.attach(
            Gtk.Label(label=_("Message")), COL_MESSAGE, self.grid_rows, 1, 1
        )
        self.grid.attach(
            Gtk.Label(label=_("Hide")), COL_CHECKBUTTON, self.grid_rows, 1, 1
        )
        self.grid_rows += 1
        self.cbl = Gtk.Label(label=_("Don't show this message again"))
        self.cbl.set_halign(Gtk.Align.END)
        self.grid.attach(self.cbl, COL_MESSAGE, self.grid_rows, 1, 1)
        self.cbn = Gtk.CheckButton()
        self.cbn.set_halign(Gtk.Align.CENTER)
        self.grid.attach(self.cbn, COL_CHECKBUTTON, self.grid_rows, 1, 1)
        scwin.set_child(self.grid)
        self.cbn.connect("toggled", self.on_toggled)
        self.add_actions([(_("_Close"), close_callback)])

    def on_toggled(self, _data: object | None = None) -> None:
        """Handle a checkbutton toggle."""
        state = self.cbn.get_active()
        for cbn in self._list_checkbuttons():
            cbn.set_active(state)

    def add_row(self, row: dict[str, object]) -> None:
        """Add a row with a new message."""
        self.grid.insert_row(self.grid_rows)
        if "page" in row:
            self.grid.attach(Gtk.Label(label=str(row["page"])), 0, self.grid_rows, 1, 1)
        if "process" in row:
            self.grid.attach(Gtk.Label(label=row["process"]), 1, self.grid_rows, 1, 1)
        self.grid.attach(
            Gtk.Label(label=TYPES[cast("str", row["message_type"])]),
            2,
            self.grid_rows,
            1,
            1,
        )
        view = Gtk.TextView()
        buffer = view.get_buffer()

        # strip newlines from the end of the string, but not the end of the line
        row["text"] = re.sub(
            r"\s+\Z",
            r"",
            str(row["text"]),
            count=1,
            flags=re.MULTILINE | re.DOTALL | re.VERBOSE,
        )
        buffer.set_text(row["text"])
        view.set_editable(False)
        view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        view.set_hexpand(True)
        self.grid.attach(view, COL_MESSAGE, self.grid_rows, 1, 1)
        self.grid_rows += 1
        if row.get("store_response"):
            button = Gtk.CheckButton()
            button.connect("toggled", self._checkbutton_consistency)
            button.set_halign(Gtk.Align.CENTER)
            self.grid.attach(button, COL_CHECKBUTTON, self.grid_rows - 1, 1, 1)
            if "stored_responses" in row:
                self.stored_responses[self.grid_rows - 1] = row["stored_responses"]

            self._checkbutton_consistency()

        if self.grid_rows > MIN_ROWS_FOR_CHECKBOX:
            self.cbl.set_label(_("Don't show these messages again"))

    def _checkbutton_consistency(self, _widget: Gtk.Widget | None = None) -> None:
        state = None
        for cbn in self._list_checkbuttons():
            if state is None:
                state = cbn.get_active()

            elif state != cbn.get_active():
                state = None
                break

        if state is not None:
            self.cbn.set_inconsistent(False)
            self.cbn.set_active(state)

        else:
            self.cbn.set_inconsistent(True)

    def add_message(self, row: dict[str, object]) -> None:
        """Possibly split messages or explain them."""
        if row["text"] is None:
            row["text"] = ""
        text = munge_message(cast("str", row["text"]))
        if isinstance(text, list):
            for line in text:
                row["text"] = filter_message(line)
                if "responses" not in row or not response_stored(
                    row["text"],
                    cast("dict[str, dict[str, object]]", row["responses"]),
                ):
                    self.add_row(row)
        elif "responses" not in row or not response_stored(
            filter_message(cast("str", row["text"])),
            cast("dict[str, dict[str, object]]", row["responses"]),
        ):
            self.add_row(row)

    def store_responses(
        self, response: str | int | None, responses: dict[str, dict[str, object]]
    ) -> None:
        """Store response in responses."""
        for raw_text in self.list_messages_to_ignore(response):
            text = filter_message(raw_text)
            responses[text] = {}
            responses[text]["response"] = response

    def _list_checkbuttons(self) -> list[Gtk.CheckButton]:
        cbs = []
        for row in range(1, self.grid_rows - 1 + 1):
            cbn = self.grid.get_child_at(COL_CHECKBUTTON, row)
            if cbn is not None:
                cbs.append(cbn)

        return cbs

    def list_messages_to_ignore(self, response: str | int | None) -> list[str]:
        """Return messages that can be ignored."""
        messages = []
        for row in range(1, self.grid_rows):
            cbn = self.grid.get_child_at(COL_CHECKBUTTON, row)
            if (cbn is not None) and cbn.get_active():
                filt = True
                if self.stored_responses.get(row):
                    filt = False
                    for i in self.stored_responses[row]:
                        if i == response:
                            filt = True
                            break

                if filt:
                    buffer = self.grid.get_child_at(COL_MESSAGE, row).get_buffer()
                    messages.append(
                        buffer.get_text(
                            buffer.get_start_iter(),
                            buffer.get_end_iter(),
                            include_hidden_chars=True,
                        )
                    )

        return cast("list[str]", (messages))


def response_stored(text: str, responses: dict[str, dict[str, object]]) -> bool:
    """Return whether there is a response stored for the message."""
    return bool(responses) and text in responses and "response" in responses[text]


def munge_message(messages: str) -> str | list[str]:
    """Separate from filter_message to show addresses, error numbers, etc."""
    out = []
    regex = re.findall(
        r"""^(
            (?: # either
                \(gimp:\d+\):[^\n]+ # gimp message
            )|(?: #or
                \[\S+\s@\s\b0[xX][0-9a-fA-F]+\b\][^\n]+ # hexadecimal + message
            )
        )""",
        messages,
        re.MULTILINE | re.DOTALL | re.VERBOSE,
    )
    for message in regex:
        out.append(message)
        messages = messages.replace(message, "")

    messages = messages.strip()
    if out:
        if not re.search(r"^\s*$", messages, re.MULTILINE | re.DOTALL | re.VERBOSE):
            out.append(messages)
        return cast("str | list[str]", (out))

    if re.search(
        r"Exception[ ](?:400|445):[ ]memory[ ]allocation[ ]failed",
        messages,
        re.MULTILINE | re.DOTALL | re.VERBOSE,
    ):
        messages += (
            "\n\n"
            + _(
                "This error is normally due to ImageMagick exceeding its resource limits."
            )
            + " "
            + _(
                "These can be extended by editing its policy file, which on my "
                "system is found at /etc/ImageMagick-6/policy.xml"
            )
            + " "
            + _(
                "Please see the ImageMagick resource documentation for more "
                "information: %(url)s"
            )
            % {"url": "https://imagemagick.org/script/resources.php"}
        )

    return messages


def filter_message(message: str) -> str:
    """External tools sometimes throw warning messages including a number.

    E.g. hex address. As the number is very rarely the same, although the message
    itself is, filter out the number from the message.
    """
    message = message.rstrip()

    # temp files -> %%t
    message = re.sub(r"scantpaper-[0-9a-zA-Z_/]+\.\w+", "%%t", message)

    # hex -> %%x
    message = re.sub(r"\b0[xX][0-9a-fA-F]+\b", "%%x", message)

    # int -> %%d
    return re.sub(r"\b\d+\b", "%%d", message)


def close_callback() -> None:
    """Close callback."""
