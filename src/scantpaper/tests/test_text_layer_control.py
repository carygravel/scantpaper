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


def test_layer_controls_rotate_buttons_emit_signals() -> None:
    """The rotate buttons emit their signals on the text bar."""
    controls = LayerControls(rotate=True)
    received: list[str] = []
    controls.connect("rotate-clockwise-clicked", lambda _w: received.append("cw"))
    controls.connect("rotate-anticlockwise-clicked", lambda _w: received.append("ccw"))

    cw = get_child_by_tooltip(controls, "Rotate text clockwise")
    ccw = get_child_by_tooltip(controls, "Rotate text anticlockwise")
    assert cw is not None
    assert isinstance(cw, Gtk.Button)
    assert ccw is not None
    assert isinstance(ccw, Gtk.Button)

    cw.clicked()
    ccw.clicked()
    assert received == ["cw", "ccw"]


def test_layer_controls_annotation_has_no_rotate() -> None:
    """The annotation bar must not expose rotate controls."""
    controls = LayerControls()
    assert get_child_by_tooltip(controls, "Rotate text clockwise") is None
    assert get_child_by_tooltip(controls, "Rotate text anticlockwise") is None


def test_layer_controls_set_rotate_enabled() -> None:
    """set_rotate_enabled() toggles the rotate buttons' sensitivity."""
    controls = LayerControls(rotate=True)
    controls.set_rotate_enabled(enabled=True)
    assert controls.rotate_cw_button.get_sensitive()
    assert controls.rotate_ccw_button.get_sensitive()

    controls.set_rotate_enabled(enabled=False)
    assert not controls.rotate_cw_button.get_sensitive()
    assert not controls.rotate_ccw_button.get_sensitive()


def test_layer_controls_set_rotate_enabled_noop_without_rotate() -> None:
    """set_rotate_enabled() is a no-op on a bar with no rotate controls.

    The annotation bar is built without rotate controls; enabling rotation
    there must not create buttons or raise.
    """
    controls = LayerControls()
    controls.set_rotate_enabled(enabled=True)
    assert controls.rotate_cw_button is None
    assert controls.rotate_ccw_button is None
