"""Tests for the Cairo ARGB32 pixel helpers."""

from __future__ import annotations

from typing import Literal

import pytest

from scantpaper.tests.pixel_helpers import argb32_rgb


@pytest.mark.parametrize(
    ("byteorder", "raw", "expected"),
    [
        ("little", b"\x00\x00\xff\xff", (255, 0, 0)),
        ("big", b"\xff\xff\x00\x00", (255, 0, 0)),
        ("little", b"\x00\xff\x00\xff", (0, 255, 0)),
        ("big", b"\xff\x00\xff\x00", (0, 255, 0)),
    ],
)
def test_argb32_rgb_decodes_native_byte_order(
    byteorder: Literal["little", "big"],
    raw: bytes,
    expected: tuple[int, int, int],
) -> None:
    """The decoder reads ARGB32 in the requested byte order."""
    assert argb32_rgb(raw, 0, byteorder) == expected


def test_argb32_rgb_honours_offset() -> None:
    """The decoder starts at the requested byte offset."""
    assert argb32_rgb(b"\x00\x00\x00\x00\x00\x00\xff\xff", 4, "little") == (
        255,
        0,
        0,
    )
