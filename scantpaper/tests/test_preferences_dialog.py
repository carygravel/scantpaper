"Test preferences dialog"

import pytest
from config import DEFAULTS
from dialog.preferences import PreferencesDialog


def test_preferences_dialog():
    "Test preferences dialog"

    with pytest.raises(KeyError):
        PreferencesDialog()
    settings = DEFAULTS.copy()
    settings["TMPDIR"] = "/tmp"
    dialog = PreferencesDialog(settings=settings)
    assert dialog is not None

    del dialog.settings["TMPDIR"]
    dialog._apply_callback()
    assert dialog.settings["TMPDIR"] == "/tmp", "updated settings"


def test_preferences_blacklist_setting():
    "Test that the device blacklist is set correctly in the preferences dialog"
    # Mock settings with a device blacklist
    settings = DEFAULTS.copy()
    settings["device blacklist"] = "scanner1|scanner2"
    settings["TMPDIR"] = "/tmp"

    # Create the PreferencesDialog with the mocked settings
    dialog = PreferencesDialog(settings=settings)

    # Assert that the blacklist entry is set correctly
    assert dialog._blacklist.get_text() == "scanner1|scanner2"
