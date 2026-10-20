"""Helpers for driving widgets in tests."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk  # noqa: E402


def emit_spinbutton_enter(widget: Gtk.SpinButton) -> None:
    """Emit the Return key that commits a fractional spin button."""
    controller = next(
        c for c in widget.observe_controllers() if isinstance(c, Gtk.EventControllerKey)
    )
    controller.emit("key-pressed", Gdk.KEY_Return, 0, 0)
