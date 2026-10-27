"""pagerange widget."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import gi

from scantpaper.const import DIALOG_ROW_SPACING
from scantpaper.i18n import _

if TYPE_CHECKING:
    from typing import ClassVar

gi.require_version("Gtk", "4.0")
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
    """pagerange widget."""

    __gsignals__: ClassVar[
        dict[str, tuple[GObject.SignalFlags, object, tuple[object, ...]]]
    ] = {
        "changed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }
    active = GObject.Property(
        type=str, default="selected", nick="active", blurb="Either selected or all"
    )
    widget_list: ClassVar[list[PageRange]] = []  # list of all PageRange widgets

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialise PageRange."""
        super().__init__(*args, **kwargs)

        buttons = {
            "selected": _("Selected"),
            "all": _("All"),
        }
        self.set_orientation(orientation=Gtk.Orientation.VERTICAL)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=DIALOG_ROW_SPACING)
        self.append(vbox)

        # GTK4 has no Gtk.RadioButton: grouped Gtk.CheckButtons behave like
        # radio buttons. The first button sets the group leader.
        group = None
        self.button = {}

        def on_toggled_event(button: Gtk.CheckButton, active: str) -> None:
            if button.get_active():
                self.set_active(active)

        for nick in sorted(buttons.keys()):
            widget = Gtk.CheckButton.new_with_label(buttons[nick])
            if group is not None:
                widget.set_group(group)
            self.button[nick] = widget
            widget.connect("toggled", on_toggled_event, nick)
            vbox.append(widget)
            widget.set_vexpand(True)
            if group is None:
                group = widget

            # initial state
            if self.active == nick:
                widget.set_active(True)

        self.widget_list.append(self)

    def get_active(self) -> str:
        """Return active button."""
        return cast("str", (self.active))

    def set_active(self, active: str) -> None:
        """Set active button."""
        if self.active == active:
            return
        for widget in self.widget_list:
            widget.active = active
            for nick in self.button:
                if active == nick and not widget.button[nick].get_active():
                    widget.button[nick].set_active(True)
        self.emit("changed", active)
