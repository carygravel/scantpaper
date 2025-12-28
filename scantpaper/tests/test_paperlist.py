"Test PaperList class"

import pytest
from dialog.paperlist import PaperList
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # pylint: disable=wrong-import-position


def test_paperlist():
    "Test PaperList class"

    with pytest.raises(TypeError):
        PaperList()  # pylint: disable=no-value-for-parameter
    plist = PaperList({"A4": {"x": 210, "y": 297, "l": 0, "t": 0}})
    assert plist is not None

    plist.do_add_clicked()
    assert len(plist.data) == 2

    plist.select([0])
    plist.do_add_clicked()
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
    plist.do_remove_clicked()
    assert len(plist.data) == 1

    plist.select([0])
    with pytest.raises(IndexError):
        plist.do_remove_clicked()
