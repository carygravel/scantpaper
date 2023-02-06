"pagerange widget"
import gettext  # For translations
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject  # pylint: disable=wrong-import-position

# from translation import __
# easier to extract strings with xgettext
_ = gettext.gettext

# does not yet work. see https://gitlab.gnome.org/GNOME/pygobject/-/issues/215
# GObject.TypeModule.register_enum( 'Gscan2pdf::PageRange::Range',        ["selected","all"] )


class PageRange(Gtk.VBox):
    "pagerange widget"
    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }
    # active=GObject.Property(
    #     type=GObject.GEnum,default='selected',nick='active',blurb='Either selected or all'
    # )
    active = GObject.Property(
        type=str, default="selected", nick="active", blurb="Either selected or all"
    )
    widget_list = []
    button = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        buttons = {
            "selected": _("Selected"),
            "all": _("All"),
        }
        vbox = Gtk.VBox()
        self.add(vbox)

        # the first radio button has to set the group,
        # which is undef for the first button

        group = None
        self.button = {}

        def on_toggled_event(nick):
            if self.button[nick].get_active():
                self.set_active(nick)

        for nick in sorted(buttons.keys()):
            self.button[nick] = Gtk.RadioButton.new_with_label_from_widget(
                group, buttons[nick]
            )
            self.button[nick].connect("toggled", on_toggled_event, nick)
            vbox.pack_start(self.button[nick], True, True, 0)
            if not group:
                group = self.button["all"]

        self.widget_list.append(self)

    def get_active(self):
        "return active button"
        return self.active

    def set_active(self, active):
        "set active button"
        for widget in self.widget_list:
            widget.active = active
            for nick in self.button:
                if active == nick:
                    widget.button[nick].set_active(True)
                    widget.emit("changed", nick)
