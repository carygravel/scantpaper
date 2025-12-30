"test TextLayerControls widget"

from text_layer_control import TextLayerControls
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


def test_text_layer_control_signals():
    "Test that buttons emit the correct signals"
    tlc = TextLayerControls()

    # Helper to track signals
    signals_received = []

    def on_signal(_widget, name):
        signals_received.append(name)

    # Connect signals
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
        tlc.connect(signal, lambda w, s=signal: on_signal(w, s))

    # Helper to find child by tooltip
    def get_child_by_tooltip(tooltip):
        for child in tlc.get_children():
            if child.get_tooltip_text() == tooltip:
                return child
        return None

    # Test buttons
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
        btn = get_child_by_tooltip(tooltip)
        assert btn is not None, f"Button '{tooltip}' not found"
        # Ensure it's a button before clicking
        assert isinstance(btn, Gtk.Button)
        btn.clicked()
        assert signals_received[-1] == signal, f"Signal '{signal}' not received"


def test_text_layer_control_sort():
    "Test sort combo box"
    tlc = TextLayerControls()

    def get_child_by_tooltip(tooltip):
        for child in tlc.get_children():
            if child.get_tooltip_text() == tooltip:
                return child
        return None

    sort_combo = get_child_by_tooltip("Select sort method for OCR boxes")
    assert sort_combo is not None

    received_sort = []
    tlc.connect("sort-changed", lambda w, val: received_sort.append(val))

    # Change selection
    # Index 0 is confidence (default), 1 is position
    sort_combo.set_active(1)
    assert received_sort[-1] == "position"

    sort_combo.set_active(0)
    assert received_sort[-1] == "confidence"


def test_text_layer_control_cancel():
    "Test cancel button existence"
    tlc = TextLayerControls()

    found = False
    for child in tlc.get_children():
        if child.get_tooltip_text() == "Cancel corrections":
            found = True
            break
    assert found, "Cancel button not found"
