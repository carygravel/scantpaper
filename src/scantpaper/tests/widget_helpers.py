"""Helpers for driving widgets in tests."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk  # noqa: E402

if TYPE_CHECKING:
    from collections.abc import Iterable

WidgetT = TypeVar("WidgetT", bound=Gtk.Widget)


def emit_spinbutton_enter(widget: Gtk.SpinButton) -> None:
    """Emit the Return key that commits a fractional spin button."""
    controller = next(
        c for c in widget.observe_controllers() if isinstance(c, Gtk.EventControllerKey)
    )
    controller.emit("key-pressed", Gdk.KEY_Return, 0, 0)


def find_descendant(widget: Gtk.Widget, widget_type: type[WidgetT]) -> WidgetT | None:
    """Return the first descendant of the given type, depth-first."""
    child = widget.get_first_child()
    while child is not None:
        if isinstance(child, widget_type):
            return child
        found = find_descendant(child, widget_type)
        if found is not None:
            return found
        child = child.get_next_sibling()
    return None


class ProfileDialogResponder:
    """Answer the scan profile name and overwrite dialogs for run_dialog.

    The name dialog is recognised by its text entry; it has one, the overwrite
    dialog does not. ``titles`` records every dialog title so a test can prove
    the real dialog was built.
    """

    def __init__(
        self,
        name: str = "",
        *,
        name_responses: Iterable[int] | None = None,
        overwrite_response: int = Gtk.ResponseType.OK,
    ) -> None:
        """Set the name to enter and the responses to return."""
        self.name = name
        self.name_responses: list[int] = list(
            name_responses or [int(Gtk.ResponseType.OK)]
        )
        self.overwrite_response = overwrite_response
        self.titles: list[str] = []

    def __call__(self, dialog: Gtk.Dialog) -> int:
        """Answer one dialog and record its title."""
        self.titles.append(dialog.get_title() or "")
        entry = find_descendant(dialog, Gtk.Entry)
        if entry is not None:
            entry.set_text(self.name)
            if len(self.name_responses) > 1:
                return self.name_responses.pop(0)
            return self.name_responses[0]
        return self.overwrite_response
