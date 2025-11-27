from unittest.mock import MagicMock
import pytest
from gi.repository import Gtk

from dialog.scan import Scan, _remove_paper_callback
from dialog.paperlist import PaperList


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

    def mock_button_factory(*args, **kwargs):
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

    # 6. Mock _remove_paper_callback
    mocker.patch("dialog.scan._remove_paper_callback")

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
