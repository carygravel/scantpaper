"Test preferences dialog"

from unittest.mock import patch, MagicMock
import pytest
from config import DEFAULTS
from dialog.preferences import PreferencesDialog
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


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


@patch("dialog.preferences.Gtk.FileChooserDialog")
@patch("dialog.preferences.get_tmp_dir")
def test_choose_temp_dir(mock_get_tmp_dir, mock_file_chooser_dialog):
    "Test the _choose_temp_dir method"
    settings = DEFAULTS.copy()
    settings["TMPDIR"] = "/tmp"

    # Create the PreferencesDialog with the mocked settings
    dialog = PreferencesDialog(settings=settings)

    # Mock the FileChooserDialog behavior
    mock_file_chooser = MagicMock()
    mock_file_chooser.run.return_value = Gtk.ResponseType.OK
    mock_file_chooser.get_filename.return_value = "/new/tmp"
    mock_file_chooser_dialog.return_value = mock_file_chooser

    # Mock the get_tmp_dir function
    mock_get_tmp_dir.return_value = "/new/tmp/scantpaper-xxxx"

    # Call the _choose_temp_dir method
    dialog._choose_temp_dir(None)

    # Assert that the FileChooserDialog was created and run
    mock_file_chooser_dialog.assert_called_once_with(
        title="Select temporary directory",
        parent=dialog,
        action=Gtk.FileChooserAction.SELECT_FOLDER,
    )
    mock_file_chooser.run.assert_called_once()
    mock_file_chooser.get_filename.assert_called_once()
    mock_file_chooser.destroy.assert_called_once()

    # Assert that get_tmp_dir was called with the correct arguments
    mock_get_tmp_dir.assert_called_once_with("/new/tmp", r"scantpaper-\w\w\w\w")

    # Assert that the TMPDIR setting was updated
    assert dialog._tmpentry.get_text() == "/new/tmp/scantpaper-xxxx"


def test_clicked_add_udt():
    "Test the _clicked_add_udt method"
    settings = DEFAULTS.copy()
    settings["TMPDIR"] = "/tmp"
    settings["user_defined_tools"] = []

    # Create the PreferencesDialog with the mocked settings
    dialog = PreferencesDialog(settings=settings)

    # Create a mock button to pass as the argument
    mock_button = Gtk.Button()

    # Call the _clicked_add_udt method with the mock button
    dialog._clicked_add_udt(mock_button)

    # Verify that a new entry was added to the user-defined tools box
    children = dialog._vboxt.get_children()
    assert len(children) > 0, "No children were added to the user-defined tools box"

    # Verify that the last child is a horizontal box containing the new entry
    last_child = children[-1]
    assert isinstance(last_child, Gtk.Box), "Last child is not a Gtk.Box"
    entry_found = any(
        isinstance(widget, Gtk.Entry) for widget in last_child.get_children()
    )
    assert entry_found, "No Gtk.Entry found in the last child box"
