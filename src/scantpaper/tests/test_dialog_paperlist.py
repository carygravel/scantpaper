"""Test PaperList class."""

import json

import gi
import pytest

from scantpaper.dialog.paperlist import PaperList

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402


def test_paperlist():
    """Test PaperList class."""
    with pytest.raises(TypeError):
        PaperList()
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
    """Test do_remove_paper when no papers left."""
    plist = PaperList({})
    mock_window = mocker.Mock()
    mock_app = mocker.Mock()
    mock_app_window = mocker.Mock()
    mock_window.get_application.return_value = mock_app
    mock_app.get_windows.return_value = mock_app_window

    plist.data.clear()

    plist.do_remove_paper(None, mock_window)
    mock_app_window.show_message_dialog.assert_called_once()


def test_fractional_dimensions_preserved():
    """PaperList keeps sub-millimetre dimensions intact."""
    plist = PaperList({"RPB_quer": {"x": 115.2, "y": 174.5, "l": 0.5, "t": 0}})
    assert plist.data[0][1] == 115.2, "width preserved"
    assert isinstance(plist.data[0][1], float), "width stored as float"
    assert plist.data[0][2] == 174.5, "height preserved"
    assert isinstance(plist.data[0][2], float), "height stored as float"
    assert plist.data[0][3] == 0.5, "left preserved"
    assert plist.data[0][4] == 0.0, "top preserved"


def test_integer_whole_mm_roundtrip():
    """Integer-defined whole-millimetre sizes stay numerically equal."""
    plist = PaperList({"A4": {"x": 210, "y": 297, "l": 0, "t": 0}})
    assert plist.data[0][1] == 210, "width numerically equal"
    assert plist.data[0][2] == 297, "height numerically equal"


def test_apply_roundtrip_json_identical():
    """Apply-style round-trip writes floats kept numerically identical in JSON."""
    plist = PaperList({"A4": {"x": 210, "y": 297, "l": 0, "t": 0}})
    formats = {}
    for row in plist.data:
        formats[row[0]] = {
            side: row[j] for j, side in enumerate(["x", "y", "l", "t"], start=1)
        }
    roundtrip = json.loads(json.dumps(formats))
    assert roundtrip["A4"]["x"] == 210, "width preserved in JSON"
    assert isinstance(roundtrip["A4"]["x"], float), "stored as float"
    assert roundtrip["A4"]["y"] == 297, "height preserved in JSON"
