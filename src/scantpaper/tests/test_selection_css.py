"""Tests for the application CSS that makes selection rectangles visible."""

from __future__ import annotations

from typing import TYPE_CHECKING

import gi

from scantpaper.app_window import _attach_selection_css

if TYPE_CHECKING:
    import pytest

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk  # noqa: E402


def test_attach_selection_css_installs_rule() -> None:
    """The provider ships the .rubberband rule at APPLICATION priority."""
    display = Gdk.Display.get_default()
    provider = _attach_selection_css()
    assert provider is not None, "expected a CSS provider"
    try:
        assert "rubberband" in provider.to_string()
    finally:
        Gtk.StyleContext.remove_provider_for_display(display, provider)


def test_attach_selection_css_tolerates_no_display(
    mocker: pytest.MockerFixture,
) -> None:
    """Attaching the stylesheet is a no-op before GTK opens a display."""
    mocker.patch("gi.repository.Gdk.Display.get_default", return_value=None)
    assert _attach_selection_css() is None
