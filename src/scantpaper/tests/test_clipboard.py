"""Tests for the Clipboard class."""

from __future__ import annotations

from scantpaper.clipboard import Clipboard


def test_clipboard_starts_empty() -> None:
    """A new clipboard holds no data."""
    clip = Clipboard()
    assert clip.data is None
    assert clip.has_data is False


def test_clipboard_stores_data() -> None:
    """Setting data stores it and reports has_data."""
    clip = Clipboard()
    data: list[list[object]] = [[1, 2, "page"]]
    clip.data = data
    assert clip.data == data
    assert clip.has_data is True


def test_clipboard_clear_empties() -> None:
    """Setting data to None empties the clipboard."""
    clip = Clipboard()
    clip.data = [[1, 2, "page"]]
    clip.data = None
    assert clip.data is None
    assert clip.has_data is False


def test_clipboard_emits_changed_on_set() -> None:
    """Setting data emits the changed signal."""
    clip = Clipboard()
    emissions: list[object] = []
    clip.connect("changed", lambda *_: emissions.append(1))
    clip.data = [[1, 2, "page"]]
    assert emissions == [1]


def test_clipboard_emits_changed_on_clear() -> None:
    """Clearing data emits the changed signal."""
    clip = Clipboard()
    emissions: list[object] = []
    clip.connect("changed", lambda *_: emissions.append(1))
    clip.data = [[1, 2, "page"]]
    clip.data = None
    assert emissions == [1, 1]
