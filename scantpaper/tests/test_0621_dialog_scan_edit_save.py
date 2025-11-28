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


def test_save_profile_overwrite_dialog(mocker):
    """
    Tests that the save profile overwrite dialog is created with the correct buttons.
    This covers changes from commit 1bd730e.
    """
    parent = MagicMock(spec=Gtk.Window)
    parent.profiles = {"MyProfile": {}}
    parent.save_current_profile = MagicMock()

    entry_mock = MagicMock(spec=Gtk.Entry)
    entry_mock.get_text.return_value = "MyProfile"
    mocker.patch("dialog.scan.Gtk.Entry", return_value=entry_mock)
    mocker.patch("dialog.scan.Gtk.Box", return_value=MagicMock(spec=Gtk.Box))
    mocker.patch("dialog.scan.Gtk.Label", return_value=MagicMock(spec=Gtk.Label))
    # i18n is not initialised, so we have to mock this
    mocker.patch("dialog.scan._", side_effect=lambda s: s)

    name_dialog_mock = MagicMock(spec=Gtk.Dialog)
    overwrite_dialog_mock = MagicMock(spec=Gtk.Dialog)

    # First call to run() on name_dialog returns OK, second returns CANCEL to exit loop.
    name_dialog_mock.run.side_effect = [Gtk.ResponseType.OK, Gtk.ResponseType.CANCEL]
    overwrite_dialog_mock.run.return_value = Gtk.ResponseType.OK

    def dialog_side_effect(*_args, **kwargs):
        if "exists. Overwrite?" in kwargs.get("title", ""):
            return overwrite_dialog_mock
        return name_dialog_mock

    dialog_mock = mocker.patch("dialog.scan.Gtk.Dialog", side_effect=dialog_side_effect)

    _save_profile_callback(None, parent)

    assert dialog_mock.call_count == 2
    assert "Name of scan profile" in dialog_mock.call_args_list[0][0]
    assert (
        "Profile 'MyProfile' exists. Overwrite?"
        in dialog_mock.call_args_list[1][1]["title"]
    )

    overwrite_dialog_mock.add_buttons.assert_called_once_with(
        "OK",
        Gtk.ResponseType.OK,
        "Cancel",
        Gtk.ResponseType.CANCEL,
    )

    parent.save_current_profile.assert_called_once_with("MyProfile")
