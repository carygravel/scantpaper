"""Helpers for reading pixels from Cairo image surfaces."""

from __future__ import annotations

import sys
from typing import Literal

_NATIVE_BYTEORDER: Literal["little", "big"] = (
    "little" if sys.byteorder == "little" else "big"
)


def argb32_rgb(
    raw: bytes,
    offset: int,
    byteorder: Literal["little", "big"] = _NATIVE_BYTEORDER,
) -> tuple[int, int, int]:
    """Return the red, green and blue of an ARGB32 pixel.

    Cairo's ``CAIRO_FORMAT_ARGB32`` stores a 32-bit quantity with alpha in
    the upper eight bits, then red, green and blue, using the host's native
    byte order. ``byteorder`` is a parameter so the test suite can exercise
    both layouts on a single machine.
    """
    value = int.from_bytes(raw[offset : offset + 4], byteorder)
    return (value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF
