"Test PaperList class"

import gi
import pytest
from dialog.paperlist import PaperList

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


def test_paperlist():
    "Test PaperList class"

    with pytest.raises(TypeError):
        PaperList()  # pylint: disable=no-value-for-parameter
    plist = PaperList({"A4": {"x": 210, "y": 297, "l": 0, "t": 0}})
    assert plist is not None

    plist.do_add_clicked(None)
    assert len(plist.data) == 2

    plist.select([0])
    plist.do_add_clicked(None)
    assert len(plist.data) == 3

    plist.select([1])
    plist.do_remove_clicked()
    assert len(plist.data) == 2

    plist.data[1][0] = "A4"
    model = plist.get_model()
    path = Gtk.TreePath(1)
    plist.do_paper_sizes_row_changed(model, path, model.get_iter(path))
    assert plist.data[1][0] == "A4 (2)", "failed to remove the version from the name"

    plist.data[0][0] = "A4 (2)"
    plist.do_paper_sizes_row_changed(model, path, model.get_iter(path))
    assert plist.data[1][0] == "A4 (3)", "failed to duplicate the version in the name"

    # to cover the branch when the name has no version
    plist.data[0][0] = "A4"
    path = Gtk.TreePath(0)
    plist.do_paper_sizes_row_changed(model, path, model.get_iter(path))
    assert plist.data[0][0] == "A4", "name unchanged"

    plist.select([1])
    plist.do_remove_paper(None, None)
    assert len(plist.data) == 1

    plist.select([0])
    with pytest.raises(IndexError):
        plist.do_remove_clicked()


def test_remove_paper_empty(mocker):
    "Test do_remove_paper when no papers left"
    plist = PaperList({})
    mock_window = mocker.Mock()
    mock_app = mocker.Mock()
    mock_app_window = mocker.Mock()
    mock_window.get_application.return_value = mock_app
    mock_app.get_windows.return_value = mock_app_window

    plist.data.clear()

    plist.do_remove_paper(None, mock_window)
    mock_app_window.show_message_dialog.assert_called_once()
