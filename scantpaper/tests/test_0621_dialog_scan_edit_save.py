"Test scan dialog"

from unittest.mock import MagicMock
import pytest
from gi.repository import Gtk
from dialog.scan import (
    Scan,
    _edit_profile_callback,
    _save_profile_callback,
)
from dialog.paperlist import PaperList
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

    __test__ = False

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


def test_edit_paper_cancel(mocker):
    """
    Tests that _edit_paper() method correctly opens the dialog and cancels.
    """
    # 1. Mock the Scan instance (self)
    mock_self = MagicMock(spec=Scan)
    mock_self.paper_formats = {"A4": [1, 2, 3, 4], "Letter": [5, 6, 7, 8]}
    mock_self.ignored_paper_formats = []
    mock_self.paper = "A4"  # Simulate current paper selection
    mock_self.combobp = MagicMock()  # Will be used by do_cancel_paper_sizes

    # 2. Mock dialog.Dialog (scantpaper.dialog.Dialog)
    mock_editor_window = MagicMock(spec=Gtk.Dialog)
    mock_editor_window.get_content_area.return_value = MagicMock(spec=Gtk.Box)
    mock_editor_window.run.return_value = (
        Gtk.ResponseType.CANCEL
    )  # Simulate clicking Cancel
    mock_editor_window.parent = mock_self

    # Path to Dialog is now relative to dialog.scan module
    patched_dialog_class = mocker.patch(
        "dialog.scan.Dialog", return_value=mock_editor_window
    )

    # 3. Mock Gtk Widgets
    button_mocks = []

    def mock_button_factory(*_args, **_kwargs):
        mock_button = MagicMock()
        button_mocks.append(mock_button)
        return mock_button

    # Mock all Gtk.Button instances and their new_with_label factory
    mocker.patch("dialog.scan.Gtk.Box", return_value=MagicMock(spec=Gtk.Box))
    mocker.patch("dialog.scan.Gtk.Label", return_value=MagicMock(spec=Gtk.Label))
    mocker.patch(
        "dialog.scan.Gtk.Image.new_from_icon_name",
        return_value=MagicMock(spec=Gtk.Image),
    )
    mocker.patch("dialog.scan.Gtk.Button", side_effect=mock_button_factory)
    mocker.patch(
        "dialog.scan.Gtk.Button.new_with_label", side_effect=mock_button_factory
    )

    # 4. Mock PaperList
    mock_slist = MagicMock(spec=PaperList)
    mock_slist.get_model.return_value.connect.return_value = (
        None  # Mock the connect call
    )
    patched_paperlist_class = mocker.patch(
        "dialog.scan.PaperList", return_value=mock_slist
    )

    # 5. Mock i18n _ function
    mocker.patch("dialog.scan._", side_effect=lambda s: s)

    # Execute the method under test
    Scan._edit_paper(mock_self)

    # Assertions
    # 1. Editor window was created with correct title and parent
    patched_dialog_class.assert_called_once_with(
        transient_for=mock_self,
        title="Edit paper size",
    )
    # 2. window.show_all() was called
    mock_editor_window.show_all.assert_called_once()

    # Simulate Cancel button click
    # The cbutton (Cancel) is the fourth button created.
    # dbutton, rbutton, abutton, cbutton
    assert len(button_mocks) >= 4  # ensure enough buttons were created
    cbutton_mock = button_mocks[3]  # Index 3 for the 4th button (cbutton)

    # Find the connect call for cbutton and invoke the handler
    cbutton_mock.connect.assert_called_once()
    assert cbutton_mock.connect.call_args[0][0] == "clicked"
    cancel_handler = cbutton_mock.connect.call_args[0][1]
    cancel_handler()

    # 3. window.destroy() was called after handler invocation
    mock_editor_window.destroy.assert_called_once()
    # 4. combobp was set back
    mock_self.combobp.set_active_by_text.assert_called_once_with(mock_self.paper)
    # 5. PaperList was initialized with self.paper_formats
    patched_paperlist_class.assert_called_once_with(mock_self.paper_formats)
