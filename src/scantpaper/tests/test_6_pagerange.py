"""test pagerange widget."""

from __future__ import annotations

import gi

from scantpaper.pagerange import PageRange

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402


class SignalCatch:
    """catch signal."""

    def __init__(self) -> None:
        """Initialise SignalCatch."""
        self.signal_emitted = False

    def catch_signal(self, _widget: object, _data: object) -> None:
        """Catch signal."""
        self.signal_emitted = True


def test_1() -> None:
    """Test pagerange widget."""
    prg = PageRange()
    assert isinstance(prg, PageRange), "Created PageRange widget"
    assert prg.active == "selected", "selected"

    prg2 = PageRange()
    assert prg2.get_active() == "selected", "selected2"

    prg2.set_active("all")
    assert prg2.get_active() == "all", "all"
    assert prg.get_active() == "all", "all2"


def test_signal() -> None:
    """Test that changed signal is emitted."""
    prg = PageRange()
    catcher = SignalCatch()
    prg.connect("changed", catcher.catch_signal)

    # change the value, signal should be emitted
    prg.set_active("all")
    assert catcher.signal_emitted, "Signal emitted"

    # reset the catcher
    catcher.signal_emitted = False

    # set to same value, signal should not be emitted
    prg.set_active("all")
    assert not catcher.signal_emitted, "Signal not emitted"


def test_page_range_does_not_expand_vertically() -> None:
    """The page-range frame should keep its natural height."""
    prg = PageRange()
    assert not prg.compute_expand(Gtk.Orientation.VERTICAL)
    for button in prg.button.values():
        assert not button.get_vexpand(), "radio button requests vertical expansion"
