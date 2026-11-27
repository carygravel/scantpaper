"""Shared environment probes and skip markers for the test suite."""

from __future__ import annotations

import locale
import shutil

import pytest
from PIL import features

from scantpaper.dependencies import jbig2_available

DE_LOCALE = "de_DE.utf8"


def has_locale(name: str, category: int = locale.LC_NUMERIC) -> bool:
    """Return whether the locale is available for the category."""
    try:
        saved = locale.setlocale(category)
        locale.setlocale(category, name)
        locale.setlocale(category, saved)
    except locale.Error:
        return False
    return True


def requires_locale(
    name: str, category: int = locale.LC_NUMERIC
) -> pytest.MarkDecorator:
    """Skip a test when the locale is unavailable."""
    return pytest.mark.skipif(
        not has_locale(name, category),
        reason=f"{name} locale not available",
    )


def requires_tool(name: str) -> pytest.MarkDecorator:
    """Skip a test when the tool is not on PATH."""
    return pytest.mark.skipif(
        shutil.which(name) is None,
        reason=f"requires {name}",
    )


def has_jbig2() -> bool:
    """Return whether the JBIG2 encoder is installed."""
    return jbig2_available()


def requires_jbig2() -> pytest.MarkDecorator:
    """Skip a test when the JBIG2 encoder is missing."""
    return pytest.mark.skipif(
        not has_jbig2(),
        reason="jbig2 encoder not installed",
    )


def has_pillow_feature(name: str) -> bool:
    """Return whether Pillow was built with the named feature."""
    return bool(features.check(name))


def requires_pillow_feature(name: str, label: str) -> pytest.MarkDecorator:
    """Skip a test when Pillow lacks the named feature."""
    return pytest.mark.skipif(
        not has_pillow_feature(name),
        reason=f"Pillow built without {label} support",
    )
