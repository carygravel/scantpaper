"""test LayerControls widget."""

from __future__ import annotations

import gi

from scantpaper.layer import LayerControls

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402


def get_child_by_tooltip(widget: Gtk.Widget, tooltip: str) -> object:
    """Return the first child with the given tooltip, or None."""
    for child in widget.get_children():
        if child.get_tooltip_text() == tooltip:
            return child
    return None


def test_layer_controls_signals() -> None:
    """Test that buttons emit the correct signals."""
    controls = LayerControls(sort=True, nav=True, copy=True)
    signals_received = []

    def on_signal(_widget: object, name: str) -> None:
        signals_received.append(name)

    for signal in [
        "go-to-first",
        "go-to-previous",
        "go-to-next",
        "go-to-last",
        "ok-clicked",
        "copy-clicked",
        "add-clicked",
        "delete-clicked",
    ]:
        controls.connect(signal, lambda w, s=signal: on_signal(w, s))

    buttons = {
        "Go to least confident text": "go-to-first",
        "Go to previous text": "go-to-previous",
        "Go to next text": "go-to-next",
        "Go to most confident text": "go-to-last",
        "Accept corrections": "ok-clicked",
        "Duplicate text": "copy-clicked",
        "Add text": "add-clicked",
        "Delete text": "delete-clicked",
    }

    for tooltip, signal in buttons.items():
        btn = get_child_by_tooltip(controls, tooltip)
        assert btn is not None, f"Button '{tooltip}' not found"
        assert isinstance(btn, Gtk.Button)
        btn.clicked()
        assert signals_received[-1] == signal, f"Signal '{signal}' not received"


def test_layer_controls_sort() -> None:
    """Test sort combo box."""
    controls = LayerControls(sort=True)
    sort_combo = get_child_by_tooltip(controls, "Select sort method for OCR boxes")
    assert sort_combo is not None

    received_sort = []
    controls.connect("sort-changed", lambda _w, val: received_sort.append(val))

    # Index 0 is confidence (default), 1 is position
    sort_combo.set_active(1)
    assert received_sort[-1] == "position"

    sort_combo.set_active(0)
    assert received_sort[-1] == "confidence"


def test_layer_controls_cancel() -> None:
    """Test cancel button existence."""
    controls = LayerControls()
    assert get_child_by_tooltip(controls, "Cancel corrections") is not None


def test_layer_controls_annotation_has_no_sort_nav_copy() -> None:
    """The annotation bar exposes only ok/add/delete/cancel (no sort/nav/copy)."""
    controls = LayerControls()
    assert get_child_by_tooltip(controls, "Select sort method for OCR boxes") is None
    assert get_child_by_tooltip(controls, "Go to least confident text") is None
    assert get_child_by_tooltip(controls, "Duplicate text") is None
    assert get_child_by_tooltip(controls, "Accept corrections") is not None
    assert get_child_by_tooltip(controls, "Add text") is not None
    assert get_child_by_tooltip(controls, "Delete text") is not None
