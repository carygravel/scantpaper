"""Tests for i18n helpers."""

from __future__ import annotations

import gettext
import importlib
import logging
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from scantpaper import i18n

if TYPE_CHECKING:
    import pytest


def test_i18n_fallbacks(caplog: pytest.LogCaptureFixture) -> None:
    """Test the fallback logic when translations are not found."""
    with (
        caplog.at_level(logging.DEBUG),
        patch("gettext.translation", side_effect=FileNotFoundError),
    ):
        # Reload the module to trigger the logic at the module level
        importlib.reload(i18n)
        i18n.log_i18n_status()

    # Only the final "nothing found" message should be a warning; the
    # per-directory misses are debug-level only.
    warnings = [
        record for record in caplog.records if record.levelno >= logging.WARNING
    ]
    assert len(warnings) == 1
    assert (
        "No translations found for 'scantpaper'; falling back to untranslated strings"
        in warnings[0].getMessage()
    )

    # Check fallbacks are correctly set
    assert isinstance(i18n.TRANSLATE, gettext.NullTranslations)
    assert i18n._ == i18n.TRANSLATE.gettext
    assert i18n.d_sane is gettext.gettext


def test_i18n_load_success(caplog: pytest.LogCaptureFixture) -> None:
    """Test the successful loading of translations."""
    mock_translation = MagicMock()
    with (
        caplog.at_level(logging.DEBUG),
        patch("gettext.translation", return_value=mock_translation),
    ):
        importlib.reload(i18n)
        i18n.log_i18n_status()

    assert mock_translation == i18n.TRANSLATE
    assert i18n._ == mock_translation.gettext
    assert i18n.d_sane == mock_translation.gettext
    assert "Loaded translations for 'scantpaper'" in caplog.text
    assert not [
        record for record in caplog.records if record.levelno >= logging.WARNING
    ]
