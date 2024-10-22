"tests for SimpleList"
import pytest
import gi

gi.require_version("Gtk", "3.0")
from simplelist import SimpleList  # pylint: disable=wrong-import-position
from gi.repository import Gtk  # pylint: disable=wrong-import-position


def test_basic():
    "basic functionality tests for SimpleList"
    slist = SimpleList(col1="text")
    assert isinstance(slist, SimpleList), "Created simplelist"
    assert isinstance(slist.data, list), "simplelist data is a list"

    slist.data.append(["row1"])
    model = slist.get_model()
    assert model[model.iter_nth_child(None, 0)][0] == "row1", "append"
    assert f"{slist.data}" == "[['row1']]", "stringify"

    slist.data.append(["row2"])
    assert len(slist.data) == 2, "len"
    assert model[model.iter_nth_child(None, 1)][0] == "row2", "append #2"

    del slist.data[0]
    assert model[model.iter_nth_child(None, 0)][0] == "row2", "del"

    slist.data[0] = ["next row"]
    assert model[model.iter_nth_child(None, 0)][0] == "next row", "setitem row"

    slist.data[0][0] = "last row"
    assert model[model.iter_nth_child(None, 0)][0] == "last row", "setitem col"

    slist.data[0][0] = None
    assert len(slist.data[0]) == 1, "len(row)"
    assert 0 in slist.data[0], "in (contains) row"

    model[model.iter_nth_child(None, 0)][0] = "row2"
    assert slist.data[0][0] == "row2", "getitem"

    slist.data.insert(0, ["row1"])
    assert model[model.iter_nth_child(None, 0)][0] == "row1", "insert"

    assert slist.get_selected_indices() == [], "get_selected_indices"
    slist.select([0])
    assert slist.get_selected_indices() == [0], "select"
    slist.select(0)
    assert slist.get_selected_indices() == [0], "select + int"
    slist.select([0, 4])
    assert slist.get_selected_indices() == [0], "select too many indices"
    slist.select([4])
    assert slist.get_selected_indices() == [0], "select with invalid indices"
    slist.select([None])
    assert slist.get_selected_indices() == [0], "select with invalid indices #2"
    slist.unselect([0])
    assert slist.get_selected_indices() == [], "unselect"
    slist.unselect(0)
    assert slist.get_selected_indices() == [], "unselect + int"
    slist.unselect([0, 4])
    assert slist.get_selected_indices() == [], "unselect too many indices"
    slist.unselect([4])
    assert slist.get_selected_indices() == [], "unselect with invalid indices"

    assert slist.get_row_data_from_path(Gtk.TreePath(0)) == [
        "row1"
    ], "get_row_data_from_path"

    assert slist.data.pop() == ["row2"], "pop"
    assert slist.data == [["row1"]], "data after pop"

    slist.data = [["new data"]]
    assert model[model.iter_nth_child(None, 0)][0] == "new data", "set data"


def test_iterators():
    "test iterators in SimpleList"

    slist = SimpleList(col1="text")
    slist.data = [["new data"]]
    flag = False
    for _row in slist.data:
        flag = True
    assert flag, "iterated over data"

    flag = False
    for _row in slist:
        flag = True
    assert flag, "iterated over slist"


def test_error():
    "test error handling in SimpleList"

    with pytest.raises(TypeError):
        SimpleList()

    with pytest.raises(TypeError):
        SimpleList(col=None)

    SimpleList.add_column_type(new={})
    slist = SimpleList(col1="new", col2="markup", col3="bool", col4="scalar")
    assert (
        slist.get_column_types()["new"]["type"] == str
    ), "unknown custom renderers default to str"

    slist = SimpleList(col1="text")
    with pytest.raises(ValueError):
        slist.get_column_editable(1)

    with pytest.raises(ValueError):
        slist.set_column_editable(1, True)

    with pytest.raises(IndexError):
        slist.data.pop()

    slist.data.append(["row1"])
    with pytest.raises(NotImplementedError):
        del slist.data[0][0]

    with pytest.raises(NotImplementedError):
        slist.data[0].extend([])

    with pytest.raises(NotImplementedError):
        slist.data[0].clear()

    with pytest.raises(NotImplementedError):
        slist.data[0].pop()

    with pytest.raises(NotImplementedError):
        slist.data[0].append("item")

    with pytest.raises(NotImplementedError):
        slist.data[0].insert(0, "item")

    with pytest.raises(IndexError):
        slist.data[10] = ["something"]

    with pytest.raises(IndexError):
        _i = slist.data[10]

    with pytest.raises(IndexError):
        del slist.data[10]


def test_renderer():
    "test renderer in SimpleList"
    window = Gtk.Window()
    slist = SimpleList(col="scalar")
    slist.data.append(["row1"])
    window.add(slist)
    window.show_all()
    assert True, "scalar_cell_renderer() threw no error"


def test_signals():
    "test signals in SimpleList"
    slist = SimpleList(col1="text", col2="bool")
    slist.data.append(["row1", True])

    assert not slist.get_column_editable(0), "get_column_editable"
    slist.set_column_editable(0, True)
    assert slist.get_column_editable(0), "set_column_editable"

    column = slist.get_column(0)
    cell_renderer = column.get_cells()
    cell_renderer[0].emit("edited", "0", "new text")
    assert slist.data[0][0] == "new text", "edited"

    column = slist.get_column(1)
    cell_renderer = column.get_cells()
    cell_renderer[0].emit("toggled", 0)
    assert not slist.data[0][1], "toggled"


def test_pixbuf():
    "test pixbuf column"
    slist = SimpleList(col="pixbuf")
    assert isinstance(slist, SimpleList), "Created simplelist"
