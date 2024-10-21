"subclass Gtk.Dialog to add some boilerplate"
import re
from pagerange import PageRange
import gi
from i18n import _

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk, GObject  # pylint: disable=wrong-import-position


class Dialog(Gtk.Dialog):
    "subclass Gtk.Dialog to add some boilerplate"
    hide_on_delete = GObject.Property(
        type=bool,
        default=False,
        nick="Hide on delete",
        blurb="Whether to destroy or hide the dialog when it is dismissed",
    )
    # page_range = GObject.Property(
    #     type=GObject.GEnum,
    #     default="selected",
    #     nick="page-range",
    #     blurb="Either selected or all",
    # )
    page_range = GObject.Property(
        type=str, default="selected", nick="page-range", blurb="Either selected or all"
    )

    def do_delete_event(self, _event):  # pylint: disable=arguments-differ
        if self.hide_on_delete:
            self.hide()
            return Gdk.EVENT_STOP  # ensures that the window is not destroyed

        self.destroy()
        return Gdk.EVENT_PROPAGATE

    def do_key_press_event(self, event):  # pylint: disable=arguments-differ
        if event.keyval != Gdk.KEY_Escape:
            return Gdk.EVENT_PROPAGATE

        if self.hide_on_delete:
            self.hide()
        else:
            self.destroy()
        return Gdk.EVENT_STOP

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

    def add_page_range(self):
        "Add a frame and radio buttons to $vbox"
        frame = Gtk.Frame(label=_("Page Range"))
        self.get_content_area().pack_start(frame, False, False, 0)
        prng = PageRange()
        prng.set_active(self.page_range)

        def set_page_range():
            self.page_range = prng

        prng.connect("changed", set_page_range)
        frame.add(prng)

    def add_actions(self, button_list):
        "Add buttons and link up their actions"
        responses = [Gtk.ResponseType.OK, Gtk.ResponseType.CANCEL]
        buttons, callbacks = [], {}
        for button in button_list:
            text, callback = button
            response = responses.pop(0)
            if response is None:
                break
            callbacks[response] = callback
            buttons.append(self.add_button(text, response))

        self.set_default_response(Gtk.ResponseType.OK)

        def on_response(_widget, response):

            if (response is not None) and response in callbacks:
                callbacks[response]()

        self.connect("response", on_response)
        return buttons


COL_MESSAGE = 3
COL_CHECKBUTTON = 4
TYPES = {
    "error": _("Error"),
    "warning": _("Warning"),
}


class MultipleMessage(Dialog):
    """subclass of Dialog to display messages and allow the user to automatically
    respond or ignore them"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        vbox = self.get_content_area()

        # to ensure dialog can't grow too big if we have too many messages
        scwin = Gtk.ScrolledWindow()
        vbox.pack_start(scwin, True, True, 0)
        self.grid = Gtk.Grid()
        self.grid_rows = 0
        self.stored_responses = []
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
        scwin.add(self.grid)  # pylint: disable=no-member
        self.cbn.connect("toggled", self.on_toggled)
        self.add_actions([("gtk-close", close_callback)])

    def on_toggled(self, _data=None):
        "callback for checkbutton toggle"
        state = self.cbn.get_active()
        for cbn in self._list_checkbuttons():
            cbn.set_active(state)

    def add_row(self, row):
        "add a row with a new message"
        self.grid.insert_row(self.grid_rows)
        self.grid.attach(Gtk.Label(label=row["page"]), 0, self.grid_rows, 1, 1)
        self.grid.attach(Gtk.Label(label=row["process"]), 1, self.grid_rows, 1, 1)
        self.grid.attach(
            Gtk.Label(label=TYPES[row["message_type"]]), 2, self.grid_rows, 1, 1
        )
        view = Gtk.TextView()
        buffer = view.get_buffer()

        # strip newlines from the end of the string, but not the end of the line
        row["text"] = re.sub(
            r"\s+\Z",
            r"",
            row["text"],
            count=1,
            flags=re.MULTILINE | re.DOTALL | re.VERBOSE,
        )
        buffer.set_text(row["text"])
        view.set_editable(False)
        view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        view.expand = True
        self.grid.attach(view, COL_MESSAGE, self.grid_rows, 1, 1)
        self.grid_rows += 1
        if "store_response" in row and row["store_response"]:
            button = Gtk.CheckButton()
            button.connect("toggled", self._checkbutton_consistency)
            button.set_halign(Gtk.Align.CENTER)
            self.grid.attach(button, COL_CHECKBUTTON, self.grid_rows - 1, 1, 1)
            if "stored_responses" in row:
                self.stored_responses[self.grid_rows - 1] = row["stored_responses"]

            self._checkbutton_consistency()

        if self.grid_rows > 2:
            self.cbl.set_label(_("Don't show these messages again"))

    def _checkbutton_consistency(self, _widget=None):
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

    def add_message(self, row):
        "possibly split messages or explain them"
        text = munge_message(row["text"])
        if isinstance(text, list):
            for line in text:
                row["text"] = filter_message(line)
                if "responses" not in row or not response_stored(
                    row["text"], row["responses"]
                ):
                    self.add_row(row)
        else:
            if "responses" not in row or not response_stored(
                filter_message(row["text"]), row["responses"]
            ):
                self.add_row(row)

    def store_responses(self, response, responses):
        "store response in responses"
        for text in self.list_messages_to_ignore(response):
            text = filter_message(text)
            responses[text] = {}
            responses[text]["response"] = response

    def _list_checkbuttons(self):

        cbs = []
        for row in range(1, self.grid_rows - 1 + 1):
            cbn = self.grid.get_child_at(COL_CHECKBUTTON, row)
            if cbn is not None:
                cbs.append(cbn)

        return cbs

    def list_messages_to_ignore(self, response):
        "return messages that can be ignored"
        messages = []
        for row in range(1, self.grid_rows):
            cbn = self.grid.get_child_at(COL_CHECKBUTTON, row)
            if (cbn is not None) and cbn.get_active():
                filt = True
                if row in self.stored_responses and self.stored_responses[row]:
                    filt = False
                    for i in self.stored_responses[row]:
                        if i == response:
                            filt = True
                            break

                if filt:
                    buffer = self.grid.get_child_at(COL_MESSAGE, row).get_buffer()
                    messages.append(
                        buffer.get_text(
                            buffer.get_start_iter(), buffer.get_end_iter(), True
                        )
                    )

        return messages


def response_stored(text, responses):
    "helper function to return whether there is a response stored for the message"
    return bool(responses) and text in responses and "response" in responses[text]


def munge_message(messages):
    """Has to be carried out separately to filter_message in order to show the user
    any addresses, error numbers, etc."""
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
        if (messages is not None) and not re.search(
            r"^\s*$", messages, re.MULTILINE | re.DOTALL | re.VERBOSE
        ):
            out.append(messages)
        return out

    if (messages is not None) and re.search(
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
                "Please see https://imagemagick.org/script/resources.php for more information"
            )
        )

    return messages


def filter_message(message):
    """External tools sometimes throws warning messages including a number,
    e.g. hex address. As the number is very rarely the same, although the message
    itself is, filter out the number from the message"""
    message = message.rstrip()

    # temp files -> %%t
    message = re.sub(r"gscan2pdf-[0-9a-zA-Z_/]+\.\w+", "%%t", message)

    # hex -> %%x
    message = re.sub(r"\b0[xX][0-9a-fA-F]+\b", "%%x", message)

    # int -> %%d
    message = re.sub(r"\b\d+\b", "%%d", message)
    return message


def close_callback():
    "close callback"
