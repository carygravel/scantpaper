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
