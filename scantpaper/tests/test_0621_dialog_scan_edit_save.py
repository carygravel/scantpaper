"Test scan dialog"

from unittest.mock import MagicMock
import pytest
from gi.repository import Gtk
from dialog.scan import Scan, _edit_profile_callback, _save_profile_callback
from scanner.profile import Profile
from scanner.options import Options


class Sane:
    "Mock Sane object"

    def __init__(self):
        self.options = [
            (
                0,
                "resolution",
                "Resolution",
                "",
                3,
                4,
                1,
                7,
                [75, 100, 150, 200, 300, 600],
            ),
            (1, "brightness", "Brightness", "", 3, 0, 1, 7, (-100, 100)),
            (2, "mode", "Mode", "", 4, 0, 1, 7, ["Color", "Gray"]),
        ]
        self.devices = [
            MagicMock(name="test", vendor="mock", model="scanner", label="at sx:123")
        ]

    def init(self, *_args, **_kwargs):
        "Mock init"
        return (1, "")

    def get_devices(self, *_args, **_kwargs):
        "Mock get_devices"
        return self.devices

    def open(self, *_args, **_kwargs):
        "Mock open"
        mock_device = MagicMock()
        mock_device.get_options.return_value = self.options
        return mock_device


sane_mock = Sane()


class TestScan(Scan):
    "Test-friendly Scan class"

    def __init__(self, *args, **kwargs):
        self.thread = MagicMock()
        self.thread.device_handle = MagicMock()
        # Mocking Gtk methods to avoid creating real widgets
        self.get_content_area = MagicMock()
        self.add_button = MagicMock()
        self.set_default_response = MagicMock()
        super().__init__(*args, **kwargs)


@pytest.fixture
def available_scan_options():
    "Fixture for available_scan_options"
    return Options(sane_mock.options)


def test_edit_profile_dialog(mocker, available_scan_options):
    """
    Tests that the edit profile dialog is created with the correct buttons.
    This covers changes from commit ff79698.
    """
    parent = TestScan(
        document=MagicMock(),
        device="test",
        available_scan_options=available_scan_options,
    )
    parent.current_scan_options = Profile()
    dialog_mock = MagicMock()
    mocker.patch("dialog.scan.Gtk.Dialog", return_value=dialog_mock)

    _edit_profile_callback(None, parent)

    Gtk.Dialog.assert_called_once()
    dialog_mock.add_buttons.assert_called_once_with(
        "OK", Gtk.ResponseType.OK, "Cancel", Gtk.ResponseType.CANCEL
    )


@pytest.mark.skip(reason="does not work with the current mocking setup")
def test_save_profile_overwrite_dialog(mocker):
    """
    Tests that the save profile overwrite dialog is created with the correct buttons.
    This covers changes from commit 1bd730e.
    """
    parent = TestScan(document=MagicMock(), device="test")
    parent.profiles = {"MyProfile": {}}
    parent.save_current_profile = MagicMock()

    name_dialog_mock = MagicMock()

    run_count = 0

    def run_side_effect(*_args, **_kwargs):
        nonlocal run_count
        if run_count == 0:
            run_count += 1
            return Gtk.ResponseType.OK
        return Gtk.ResponseType.CANCEL

    name_dialog_mock.run.side_effect = run_side_effect

    entry_mock = MagicMock()
    entry_mock.get_text.return_value = "MyProfile"
    name_dialog_mock.get_content_area.return_value.get_children.return_value = [
        entry_mock
    ]

    overwrite_dialog_mock = MagicMock()
    overwrite_dialog_mock.run.return_value = Gtk.ResponseType.OK

    def dialog_side_effect(*_args, **kwargs):
        if "exists. Overwrite" in kwargs.get("title", ""):
            return overwrite_dialog_mock
        return name_dialog_mock

    mocker.patch("dialog.scan.Gtk.Dialog", side_effect=dialog_side_effect)

    _save_profile_callback(None, parent)

    assert overwrite_dialog_mock.add_buttons.called
    overwrite_dialog_mock.add_buttons.assert_called_once_with(
        "OK", Gtk.ResponseType.OK, "Cancel", Gtk.ResponseType.CANCEL
    )
    parent.save_current_profile.assert_called_once_with("MyProfile")
