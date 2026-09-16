"""tests for SimpleList."""

import gi
import pytest

from scantpaper.simplelist import (
    SimpleList,
    float_g_cell_renderer,
    scalar_cell_renderer,
)

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402


def test_basic():
    """Basic functionality tests for SimpleList."""
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

    assert slist.get_row_data_from_path(Gtk.TreePath(0)) == ["row1"], (
        "get_row_data_from_path"
    )

    assert slist.data.pop() == ["row2"], "pop"
    assert slist.data == [["row1"]], "data after pop"

    slist.data = [["new data"]]
    assert model[model.iter_nth_child(None, 0)][0] == "new data", "set data"


def test_iterators():
    """Test iterators in SimpleList."""
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
    """Test error handling in SimpleList."""
    with pytest.raises(TypeError):
        SimpleList()

    with pytest.raises(TypeError):
        SimpleList(col=None)

    SimpleList.add_column_type(new={})
    with pytest.warns(UserWarning, match="column type 'new' has no 'type' field"):
        slist = SimpleList(col1="new", col2="markup", col3="bool", col4="scalar")
    assert slist.get_column_types()["new"]["type"] is str, (
        "unknown custom renderers default to str"
    )

    slist = SimpleList(col1="text")
    with pytest.raises(ValueError, match="invalid column index"):
        slist.get_column_editable(1)

    with pytest.raises(ValueError, match="invalid column index"):
        slist.set_column_editable(1, editable=True)

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
    """Test renderer in SimpleList."""
    window = Gtk.Window()
    slist = SimpleList(col="scalar")
    slist.data.append(["row1"])
    window.add(slist)
    window.show_all()
    assert True, "scalar_cell_renderer() threw no error"


def test_signals():
    """Test signals in SimpleList."""
    slist = SimpleList(col1="text", col2="bool")
    slist.data.append(["row1", True])

    assert not slist.get_column_editable(0), "get_column_editable"
    slist.set_column_editable(0, editable=True)
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
    """Test pixbuf column."""
    slist = SimpleList(col="pixbuf")
    assert isinstance(slist, SimpleList), "Created simplelist"


def test_shared_renderer_isolation():
    """Test that modifying one SimpleList does not affect another."""
    slist1 = SimpleList(col1="text")
    slist1.set_column_editable(0, editable=True)

    slist2 = SimpleList(col1="text")
    assert not slist2.get_column_editable(0), (
        "Second list should not inherit editability"
    )


def test_edited_types():
    """Test edited signal with different column types."""
    slist = SimpleList(col1="int", col2="double")
    slist.data.append([1, 1.1])

    slist.set_column_editable(0, editable=True)
    slist.set_column_editable(1, editable=True)

    column0 = slist.get_column(0)
    cell_renderer0 = column0.get_cells()[0]
    cell_renderer0.emit("edited", "0", "2")
    assert slist.data[0][0] == 2
    assert isinstance(slist.data[0][0], int)

    column1 = slist.get_column(1)
    cell_renderer1 = column1.get_cells()[0]
    cell_renderer1.emit("edited", "0", "2.2")
    assert slist.data[0][1] == 2.2
    assert isinstance(slist.data[0][1], float)


def test_edited_double_fractional():
    """Editing a double cell accepts fractional text."""
    slist = SimpleList(col1="double")
    slist.data.append([210])
    slist.set_column_editable(0, editable=True)
    column0 = slist.get_column(0)
    cell_renderer0 = column0.get_cells()[0]
    cell_renderer0.emit("edited", "0", "115.2")
    assert slist.data[0][0] == 115.2
    assert isinstance(slist.data[0][0], float)


def test_edited_double_rejects_invalid():
    """Editing a double cell with non-numeric text keeps the old value."""
    slist = SimpleList(col1="double")
    slist.data.append([210])
    slist.set_column_editable(0, editable=True)
    column0 = slist.get_column(0)
    cell_renderer0 = column0.get_cells()[0]
    cell_renderer0.emit("edited", "0", "abc")
    assert slist.data[0][0] == 210


def test_mm_display_without_trailing_decimal():
    """An mm cell renders whole numbers without a trailing decimal."""
    slist = SimpleList(col="mm")
    slist.data.append([210.0])
    slist.data.append([115.2])
    model = slist.get_model()
    cell = Gtk.CellRendererText()
    itr1 = model.iter_nth_child(None, 0)
    itr2 = model.iter_nth_child(None, 1)
    float_g_cell_renderer(Gtk.TreeViewColumn(), cell, model, itr1, 0)
    assert cell.get_property("text") == "210", (
        "whole numbers render without trailing .0"
    )
    float_g_cell_renderer(Gtk.TreeViewColumn(), cell, model, itr2, 0)
    assert cell.get_property("text") == "115.2", (
        "fractional values keep their decimal part"
    )


def test_mm_display_renders_none_as_empty():
    """An mm cell renders a None value as empty text."""
    model = Gtk.ListStore(object)
    model.append([None])
    cell = Gtk.CellRendererText()
    itr = model.iter_nth_child(None, 0)
    float_g_cell_renderer(Gtk.TreeViewColumn(), cell, model, itr, 0)
    assert cell.get_property("text") == ""


def test_mm_cell_edited():
    """An mm cell parses edits like a double and keeps invalid values."""
    slist = SimpleList(col1="mm")
    slist.data.append([210.0])
    slist.set_column_editable(0, editable=True)
    column0 = slist.get_column(0)
    cell_renderer0 = column0.get_cells()[0]
    cell_renderer0.emit("edited", "0", "115.2")
    assert slist.data[0][0] == 115.2
    assert isinstance(slist.data[0][0], float)
    cell_renderer0.emit("edited", "0", "abc")
    assert slist.data[0][0] == 115.2


def test_scalar_renderer_sets_gobject_text_property():
    """scalar_cell_renderer sets the GObject text property GTK paints."""
    slist = SimpleList(col="scalar")
    slist.data.append(["row1"])
    model = slist.get_model()
    cell = Gtk.CellRendererText()
    itr = model.iter_nth_child(None, 0)
    scalar_cell_renderer(Gtk.TreeViewColumn(), cell, model, itr, 0)
    assert cell.get_property("text") == "row1", "GObject text property set"
    slist.data[0][0] = None
    scalar_cell_renderer(Gtk.TreeViewColumn(), cell, model, itr, 0)
    assert cell.get_property("text") == "", "None renders as empty text"


def test_connect_edited_non_text_renderer_is_noop():
    """do_connect_text_edited ignores non-text renderers."""
    slist = SimpleList(col1="text")
    pixbuf_renderer = Gtk.CellRendererPixbuf()
    slist.do_connect_text_edited(pixbuf_renderer, int, 0)
    assert not hasattr(pixbuf_renderer, "column"), "no column set for non-text"


def test_edited_double_accepts_comma_locale(comma_locale):
    """A double cell accepts the locale decimal separator, storing a float."""
    assert comma_locale == ","
    slist = SimpleList(col1="double")
    slist.data.append([210.0])
    slist.set_column_editable(0, editable=True)
    column0 = slist.get_column(0)
    cell_renderer0 = column0.get_cells()[0]
    cell_renderer0.emit("edited", "0", "115,2")
    assert slist.data[0][0] == 115.2
    assert isinstance(slist.data[0][0], float)


def test_edited_double_period_still_works_in_comma_locale(comma_locale):
    """A period still parses in a comma locale."""
    assert comma_locale == ","
    slist = SimpleList(col1="double")
    slist.data.append([210.0])
    slist.set_column_editable(0, editable=True)
    column0 = slist.get_column(0)
    cell_renderer0 = column0.get_cells()[0]
    cell_renderer0.emit("edited", "0", "115.2")
    assert slist.data[0][0] == 115.2


def test_edited_double_rejects_invalid_in_comma_locale(comma_locale):
    """Invalid input is still rejected in a comma locale."""
    assert comma_locale == ","
    slist = SimpleList(col1="double")
    slist.data.append([210.0])
    slist.set_column_editable(0, editable=True)
    column0 = slist.get_column(0)
    cell_renderer0 = column0.get_cells()[0]
    cell_renderer0.emit("edited", "0", "abc")
    assert slist.data[0][0] == 210.0
    cell_renderer0.emit("edited", "0", "1,2.3")
    assert slist.data[0][0] == 210.0


def test_mm_display_with_comma_locale(comma_locale):
    """An mm cell renders fractional values with the locale's separator."""
    assert comma_locale == ","
    slist = SimpleList(col="mm")
    slist.data.append([115.2])
    model = slist.get_model()
    cell = Gtk.CellRendererText()
    itr = model.iter_nth_child(None, 0)
    float_g_cell_renderer(Gtk.TreeViewColumn(), cell, model, itr, 0)
    assert cell.get_property("text") == "115,2"


def test_mm_display_whole_with_comma_locale(comma_locale):
    """An mm cell still renders whole numbers without decimals in a comma locale."""
    assert comma_locale == ","
    slist = SimpleList(col="mm")
    slist.data.append([210.0])
    model = slist.get_model()
    cell = Gtk.CellRendererText()
    itr = model.iter_nth_child(None, 0)
    float_g_cell_renderer(Gtk.TreeViewColumn(), cell, model, itr, 0)
    assert cell.get_property("text") == "210"
