"subclass Gtk.Dialog to add some boilerplate"
import gettext  # For translations
from pagerange import PageRange
import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk, GObject  # pylint: disable=wrong-import-position

_ = gettext.gettext


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
        frame = Gtk.Frame(_("Page Range"))
        self.get_content_area().pack_start(frame, False, False, 0)
        prng = PageRange()
        prng.set_active(self.page_range)

        def set_page_range():
            self.page_range = prng

        prng.connect("changed", set_page_range)
        frame.add(prng)

    def add_actions(self, button_list):
        "Add buttons and link up their actions"
        responses = ["ok", "cancel"]
        (buttons, callbacks) = ([], {})
        i = 0
        while i < len(button_list) - 1:
            _text, callback = button_list
            response = responses.pop(0)
            if response is None:
                break
            callbacks[response] = callback
            buttons.append(self.add_button(text=response))

        self.set_default_response(Gtk.ResponseType.OK)

        def on_response(_widget, response):

            if (response is not None) and response in callbacks:
                callbacks[response]()

        self.connect("response", on_response)
        return buttons
