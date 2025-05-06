"tests for SqliteView"

from pathlib import Path
import subprocess
import tempfile
import pytest
from PIL import Image
import gi
from page import Page
from sqliteview import SqliteView

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf  # pylint: disable=wrong-import-position


def rose():
    "return test pixbuf"
    with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
        subprocess.run(["convert", "rose:", tmp.name], check=True)
        return GdkPixbuf.Pixbuf.new_from_file(tmp.name)


def test_basic(clean_up_files):
    "basic functionality tests for SqliteView"
    view = SqliteView()
    assert isinstance(view, SqliteView), "Created SqliteView"
    assert isinstance(view.data, list), "SqliteView data is a list"
    assert len(view.data) == 0, "len emty data"

    pixbuf = rose()
    view.data.append([1, pixbuf, 1])
    model = view.get_model()
    assert model[model.iter_nth_child(None, 0)][0] == 1, "append"
    assert len(view.data) == 1, "len"

    view.data.append([2, pixbuf, 2])
    del view.data[0]
    assert model[model.iter_nth_child(None, 0)][0] == 2, "del"

    view.data[0] = [3, pixbuf, 3]
    assert model[model.iter_nth_child(None, 0)][0] == 3, "setitem row"

    view.data[0][0] = 4
    assert model[model.iter_nth_child(None, 0)][0] == 4, "setitem col"

    view.data[0][0] = None
    assert len(view.data[0]) == 3, "len(row)"
    assert 0 in view.data[0], "in (contains) row"

    model[model.iter_nth_child(None, 0)][0] = 5
    assert view.data[0][0] == 5, "getitem"

    view.data.insert(0, [6, pixbuf, 6])
    assert model[model.iter_nth_child(None, 0)][0] == 6, "insert"

    assert view.get_selected_indices() == [], "get_selected_indices"
    view.select([0])
    assert view.get_selected_indices() == [0], "select"
    view.select(0)
    assert view.get_selected_indices() == [0], "select + int"
    view.select([0, 4])
    assert view.get_selected_indices() == [0], "select too many indices"
    view.select([4])
    assert view.get_selected_indices() == [0], "select with invalid indices"
    view.select([None])
    assert view.get_selected_indices() == [0], "select with invalid indices #2"
    view.unselect([0])
    assert view.get_selected_indices() == [], "unselect"
    view.unselect(0)
    assert view.get_selected_indices() == [], "unselect + int"
    view.unselect([0, 4])
    assert view.get_selected_indices() == [], "unselect too many indices"
    view.unselect([4])
    assert view.get_selected_indices() == [], "unselect with invalid indices"

    assert (
        view.get_row_data_from_path(Gtk.TreePath(0))[0] == 6
    ), "get_row_data_from_path"

    assert view.data.pop()[0] == 5, "pop"
    assert view.data[0][0] == 6, "data after pop"

    view.data = [[1, pixbuf, 1]]
    assert model[model.iter_nth_child(None, 0)][0] == 1, "set data"

    clean_up_files([Path(tempfile.gettempdir()) / "document.db"])


def test_iterators(clean_up_files):
    "test iterators in SqliteView"

    view = SqliteView()
    pixbuf = rose()
    view.data = [[1, pixbuf, 1]]
    flag = False
    for _row in view.data:
        flag = True
    assert flag, "iterated over data"

    flag = False
    for _row in view:
        flag = True
    assert flag, "iterated over view"

    clean_up_files([Path(tempfile.gettempdir()) / "document.db"])


def test_error(clean_up_files):
    "test error handling in SqliteView"

    view = SqliteView()
    with pytest.raises(TypeError):
        view.get_column_editable(1)

    with pytest.raises(TypeError):
        view.set_column_editable(1, True)

    with pytest.raises(IndexError):
        view.data.pop()

    pixbuf = rose()
    view.data.append([1, pixbuf, 1])
    with pytest.raises(NotImplementedError):
        del view.data[0][0]

    with pytest.raises(NotImplementedError):
        view.data[0].extend([])

    with pytest.raises(NotImplementedError):
        view.data[0].clear()

    with pytest.raises(NotImplementedError):
        view.data[0].pop()

    with pytest.raises(NotImplementedError):
        view.data[0].append("item")

    with pytest.raises(NotImplementedError):
        view.data[0].insert(0, "item")

    with pytest.raises(IndexError):
        view.data[10] = ["something"]

    with pytest.raises(IndexError):
        _i = view.data[10]

    with pytest.raises(IndexError):
        del view.data[10]

    clean_up_files([Path(tempfile.gettempdir()) / "document.db"])


def test_renderer(clean_up_files):
    "test renderer in SqliteView"
    window = Gtk.Window()
    view = SqliteView()
    pixbuf = rose()
    view.data.append([1, pixbuf, 1])
    window.add(view)
    window.show_all()
    assert True, "cell_renderer() threw no error"

    clean_up_files([Path(tempfile.gettempdir()) / "document.db"])


def test_signals(clean_up_files):
    "test signals in SqliteView"
    view = SqliteView()
    pixbuf = rose()
    view.data.append([1, pixbuf, 1])

    assert not view.get_column_editable(0), "get_column_editable"
    view.set_column_editable(0, True)
    assert view.get_column_editable(0), "set_column_editable"

    column = view.get_column(0)
    cell_renderer = column.get_cells()
    cell_renderer[0].emit("edited", 0, 2)
    assert view.data[0][0] == 2, "edited"

    clean_up_files([Path(tempfile.gettempdir()) / "document.db"])


def test_db(clean_up_files):
    "test database access"
    view = SqliteView()
    view.add_page(1, Page(image_object=Image.new("RGB", (210, 297))))
    assert view.data[0][0] == 1, "add page"

    view = SqliteView(db=Path(tempfile.gettempdir()) / "document.db")
    assert view.data[0][0] == 1, "load from db"

    view.take_snapshot()
    view.add_page(2, Page(image_object=Image.new("RGB", (210, 297))))
    view.delete_page(1)
    assert view.data[0][0] == 2, "delete page"

    page = view.get_page(2)
    assert isinstance(page, Page), "get_page"

    view.take_snapshot()
    view.undo()
    assert view.data[0][0] == 1, "undo"

    clean_up_files([Path(tempfile.gettempdir()) / "document.db"])
