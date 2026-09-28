"""Window-scoped clipboard for copied or cut pages."""

from __future__ import annotations

from typing import ClassVar

import gi

gi.require_version("GObject", "2.0")
from gi.repository import GObject  # noqa: E402


class Clipboard(GObject.Object):
    """Hold copied or cut page data and signal when its contents change."""

    __gsignals__: ClassVar[
        dict[str, tuple[GObject.SignalFlags, object, tuple[object, ...]]]
    ] = {
        "changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    _data: list[list[object]] | None

    def __init__(self) -> None:
        """Initialise Clipboard."""
        super().__init__()
        self._data: list[list[object]] | None = None

    @property
    def data(self) -> list[list[object]] | None:
        """Return the stored page data, or None when the clipboard is empty."""
        return self._data

    @data.setter
    def data(self, value: list[list[object]] | None) -> None:
        """Store page data and notify listeners of the change."""
        self._data = value
        self.emit("changed")

    @property
    def has_data(self) -> bool:
        """Return True when the clipboard currently holds page data."""
        return self._data is not None
