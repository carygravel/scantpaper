"""test LayerControls widget."""

from __future__ import annotations

import gi
import pytest

from scantpaper.const import DEFAULT_FOCUS_ZOOM, MAX_FOCUS_ZOOM, MIN_FOCUS_ZOOM
from scantpaper.layer import LayerControls

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402


def get_child_by_tooltip(widget: Gtk.Widget, tooltip: str) -> object:
    """Return the first child with the given tooltip, or None."""
    for child in list(widget.observe_children()):
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
        btn.emit("clicked")
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

    cw.emit("clicked")
    ccw.emit("clicked")
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


def test_layer_controls_focus_zoom_is_optional() -> None:
    """The focus-zoom control only exists when the bar enables it."""
    controls = LayerControls()

    assert controls.focus_zoom_button is None
    assert controls.focus_zoom_scale is None
    assert controls.get_focus_zoom() == pytest.approx(DEFAULT_FOCUS_ZOOM)

    # A bar without the control ignores level changes instead of raising.
    controls.set_focus_zoom(0.75)
    assert controls.get_focus_zoom() == pytest.approx(DEFAULT_FOCUS_ZOOM)
    controls._update_focus_zoom_tooltip(1.5)
    assert controls.focus_zoom_button is None


def test_layer_controls_focus_zoom_starts_at_the_default() -> None:
    """The control shows the default percentage and a value tooltip."""
    controls = LayerControls(focus_zoom=True)

    assert isinstance(controls.focus_zoom_button, Gtk.MenuButton)
    assert controls.focus_zoom_scale is not None
    assert controls.get_focus_zoom() == pytest.approx(DEFAULT_FOCUS_ZOOM)
    assert controls.focus_zoom_scale.get_value() == pytest.approx(
        DEFAULT_FOCUS_ZOOM * 100
    )
    tooltip = controls.focus_zoom_button.get_tooltip_text()
    assert tooltip is not None
    assert "100" in tooltip


def test_layer_controls_focus_zoom_emits_on_a_scale_change() -> None:
    """Dragging the scale emits the level as a multiplier."""
    controls = LayerControls(focus_zoom=True)
    received: list[float] = []
    controls.connect(
        "focus-zoom-changed", lambda _widget, value: received.append(value)
    )
    assert controls.focus_zoom_scale is not None

    controls.focus_zoom_scale.set_value(60)

    assert received == [pytest.approx(0.6)]


def test_layer_controls_focus_zoom_reset_restores_the_default() -> None:
    """Reset returns the scale to 100% and emits the change."""
    controls = LayerControls(focus_zoom=True)
    received: list[float] = []
    controls.connect(
        "focus-zoom-changed", lambda _widget, value: received.append(value)
    )
    assert controls.focus_zoom_scale is not None
    controls.focus_zoom_scale.set_value(60)
    received.clear()

    assert controls.focus_zoom_reset is not None
    controls.focus_zoom_reset.emit("clicked")

    assert controls.focus_zoom_scale.get_value() == pytest.approx(
        DEFAULT_FOCUS_ZOOM * 100
    )
    assert received == [pytest.approx(DEFAULT_FOCUS_ZOOM)]


def test_layer_controls_set_focus_zoom_does_not_emit() -> None:
    """A programmatic level change updates the control without a signal."""
    controls = LayerControls(focus_zoom=True)
    received: list[float] = []
    controls.connect(
        "focus-zoom-changed", lambda _widget, value: received.append(value)
    )

    controls.set_focus_zoom(0.75)

    assert not received
    assert controls.get_focus_zoom() == pytest.approx(0.75)
    assert controls.focus_zoom_scale is not None
    assert controls.focus_zoom_scale.get_value() == pytest.approx(75)
    assert controls.focus_zoom_button is not None
    tooltip = controls.focus_zoom_button.get_tooltip_text()
    assert tooltip is not None
    assert "75" in tooltip


def test_layer_controls_set_focus_zoom_clamps_to_the_range() -> None:
    """Programmatic values are clamped to the supported range."""
    controls = LayerControls(focus_zoom=True)

    controls.set_focus_zoom(5.0)
    assert controls.get_focus_zoom() == pytest.approx(MAX_FOCUS_ZOOM)

    controls.set_focus_zoom(0.01)
    assert controls.get_focus_zoom() == pytest.approx(MIN_FOCUS_ZOOM)
