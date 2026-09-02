"pagerange widget"

from typing import ClassVar

import gi
from i18n import _

gi.require_version("Gtk", "3.0")
from gi.repository import (  # noqa: E402
    GObject,
    Gtk,
)

# TODO: can now be done with enums:
# Enumerations can now be registered from Python since pygobject 3.52.0
# (see https://gitlab.gnome.org/GNOME/pygobject/-/merge_requests/400
#  and https://gitlab.gnome.org/GNOME/pygobject/-/issues/215).
# Some target distros currently ship < 3.52 (e.g. noble LTS: 3.48.2,
# Debian trixie/stable: 3.50), so this must stay behind a runtime guard:


class PageRange(Gtk.Box):
    "pagerange widget"

    __gsignals__: ClassVar[dict] = {
        "changed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }
    active = GObject.Property(
        type=str, default="selected", nick="active", blurb="Either selected or all"
    )
    widget_list: ClassVar[list] = []  # list of all PageRange widgets

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        buttons = {
            "selected": _("Selected"),
            "all": _("All"),
        }
        self.set_orientation(orientation=Gtk.Orientation.VERTICAL)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(vbox)

        # the first radio button has to set the group,
        # which is None for the first button
        group = None
        self.button = {}

        def on_toggled_event(button, active):
            if button.get_active():
                self.set_active(active)

        for nick in sorted(buttons.keys()):
            self.button[nick] = Gtk.RadioButton.new_with_label_from_widget(
                group, buttons[nick]
            )
            self.button[nick].connect("toggled", on_toggled_event, nick)
            vbox.pack_start(self.button[nick], True, True, 0)
            if not group:
                group = self.button["all"]

            # initial state
            if self.active == nick:
                self.button[nick].set_active(True)

        self.widget_list.append(self)

    def get_active(self):
        "return active button"
        return self.active

    def set_active(self, active):
        "set active button"
        if self.active == active:
            return
        for widget in self.widget_list:
            widget.active = active
            for nick in self.button:
                if active == nick and not widget.button[nick].get_active():
                    widget.button[nick].set_active(True)
        self.emit("changed", active)
