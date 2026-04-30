"""
Tests for i18n module.
"""

import importlib
import gettext
from unittest.mock import patch, MagicMock
import i18n


def test_i18n_fallbacks(caplog):
    "Test the fallback logic when translations are not found."
    with patch("gettext.translation", side_effect=FileNotFoundError):
        # Reload the module to trigger the logic at the module level
        importlib.reload(i18n)

    # Check for expected log messages
    assert (
        "No translations found for 'scantpaper'; falling back to untranslated strings"
        in caplog.text
    )

    # Check fallbacks are correctly set
    assert isinstance(i18n.translate, gettext.NullTranslations)
    assert i18n._ == i18n.translate.gettext
    assert i18n.d_sane is gettext.gettext


def test_i18n_load_success():
    "Test the successful loading of translations."
    mock_translation = MagicMock()
    with patch("gettext.translation", return_value=mock_translation):
        importlib.reload(i18n)

    assert i18n.translate == mock_translation
    assert i18n._ == mock_translation.gettext
    assert i18n.d_sane == mock_translation.gettext
