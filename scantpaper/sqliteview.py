"A simple interface to Gtk's complex MVC list widget"

from pathlib import Path
import sqlite3
import tempfile
import gi
from i18n import _
from page import Page

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf  # pylint: disable=wrong-import-position


def scalar_cell_renderer(_tree_column, cell, model, itr, i):
    "custom cell renderer gtype scalar"
    info = model.get(itr, i)
    cell.text = "" if info is None else info


column_types = {
    "hidden": {"type": int, "attr": "hidden"},
    "text": {"type": str, "renderer": Gtk.CellRendererText(), "attr": "text"},
    "markup": {"type": str, "renderer": Gtk.CellRendererText(), "attr": "markup"},
    "int": {"type": int, "renderer": Gtk.CellRendererText(), "attr": "text"},
    "double": {"type": float, "renderer": Gtk.CellRendererText(), "attr": "text"},
    "bool": {"type": bool, "renderer": Gtk.CellRendererToggle(), "attr": "active"},
    "scalar": {
        "type": object,
        "renderer": Gtk.CellRendererText(),
        "attr": scalar_cell_renderer,
    },
    "pixbuf": {
        "type": GdkPixbuf.Pixbuf,
        "renderer": Gtk.CellRendererPixbuf(),
        "attr": "pixbuf",
    },
}

THUMBNAIL = 100  # pixels


class SqliteView(Gtk.TreeView):
    "Gtk.TreeView persisted to a SQLite database"

    heightt = THUMBNAIL
    widtht = THUMBNAIL
    _action_id = 0
    number_undo_steps = 1

    def __init__(self, **kwargs):
        """In order to allow use to be able to undo/redo changes,
        we split the page data from the thumbnails"""
        super().__init__()
        if "db" in kwargs:
            kwargs["db"] = Path(kwargs["db"])
            kwargs["dir"] = kwargs["db"].parent
        if "dir" not in kwargs:
            kwargs["dir"] = Path(tempfile.gettempdir())
        if "db" not in kwargs:
            kwargs["db"] = kwargs["dir"] / "document.db"

        columns = {"#": "int", _("Thumbnails"): "pixbuf", "id": "hidden"}
        column_info = []
        for name, typekey in columns.items():
            column_info.append(
                {
                    "title": name,
                    "type": column_types[typekey]["type"],
                    "renderer": (
                        column_types[typekey]["renderer"]
                        if "renderer" in column_types[typekey]
                        else None
                    ),
                    "attr": (
                        column_types[typekey]["attr"]
                        if "attr" in column_types[typekey]
                        else "hidden"
                    ),
                }
            )

        model = Gtk.ListStore(*[x["type"] for x in column_info])
        self.set_model(model)
        i = 0
        for col in column_info:
            if type(col["attr"]).__name__ == "function":
                self.insert_column_with_data_func(
                    -1,
                    col["title"],
                    col["renderer"],
                    col["attr"],
                    i,
                )
                i += 1

            elif col["attr"] == "hidden":  # skip hidden column
                pass

            else:
                attr = {col["attr"]: i}
                column = Gtk.TreeViewColumn(
                    col["title"],
                    col["renderer"],
                    **attr,
                )
                self.append_column(column)
                if col["attr"] == "text":
                    # attach a decent 'edited' callback to any
                    # columns using a text renderer.  we do NOT
                    # turn on editing by default.
                    row = column.get_cells()
                    col["renderer"].connect(
                        "edited", self.do_text_cell_edited, col["type"]
                    )
                    col["renderer"].column = i
                    i += 1

        self._con = sqlite3.connect(kwargs["db"])
        self._cur = self._con.cursor()
        self._cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='page';"
        )
        if self._cur.fetchone():
            self._cur.execute(
                """SELECT id, image, x_res, y_res, text, annotations
                   FROM page ORDER BY id"""
            )
            for row in self._cur.fetchall():
                page = Page.from_bytes(row[1])
                thumb = page.get_pixbuf_at_scale(self.heightt, self.widtht)
                self.data.append([row[0], thumb, row[0]])
        else:

            # ideally, we would cache the thumbnail in the database, but it
            # seems non-trivial to create a blob from a pixbuf and vice-versa.
            self._cur.execute(
                """CREATE TABLE page(
                    id INTEGER PRIMARY KEY,
                    image BLOB,
                    x_res FLOAT,
                    y_res FLOAT,
                    text TEXT,
                    annotations TEXT)"""
            )
            self._cur.execute(
                """CREATE TABLE page_numbers(
                    action_id INTEGER PRIMARY KEY,
                    page_number INTEGER NOT NULL,
                    page_id INTEGER NOT NULL,
                    FOREIGN KEY (page_id) REFERENCES page(id))"""
            )

    def __iter__(self, *args, **kwargs):
        return iter(self.get_model(), *args, **kwargs)

    @property
    def data(self):
        "getter for data property"
        return TiedList(self.get_model())

    @data.setter
    def data(self, new_data):
        "setter for data property"
        self.get_model().clear()
        self.data.extend(new_data)

    def do_toggled(self, renderer, row):
        "callback for toggled signal of boolean cell"
        col = renderer.column
        model = self.get_model()
        itr = model.iter_nth_child(None, int(row))
        model[itr][col] = not model[itr][col]

    def do_text_cell_edited(self, renderer, text_path, new_text, col_type):
        "callback for edited signal of text cell"
        path = Gtk.TreePath.new_from_string(text_path)
        model = self.get_model()
        if col_type == int:
            new_text = int(new_text)
        elif col_type == float:
            new_text = float(new_text)
        model[model.get_iter(path)][renderer.column] = new_text

    def set_column_editable(self, index, editable):
        "set whether a column can be edited"
        column = self.get_column(index)
        if column is None:
            raise ValueError(f"invalid column index {index}")
        cell_renderer = column.get_cells()
        return cell_renderer[0].set_property("editable", editable)

    def get_column_editable(self, index):
        "return whether a column can be edited"
        column = self.get_column(index)
        if column is None:
            raise ValueError(f"invalid column index {index}")
        cell_renderer = column.get_cells()
        return cell_renderer[0].get_property("editable")

    def get_selected_indices(self):
        "get selected indices"
        selection = self.get_selection()

        # warning: this assumes that the TreeModel is actually a ListStore.
        # if the model is a TreeStore, get_indices will return more than one
        # index, which tells you how to get all the way down into the tree,
        # but all the indices will be squashed into one array... so, ah,
        # don't use this for TreeStores!
        _model, indices = selection.get_selected_rows()
        return [x.get_indices()[0] for x in indices]

    def _modify_selection(self, indices, func):
        "helper function for select/unselect()"
        selection = self.get_selection()
        if (
            isinstance(indices, list)
            and len(indices) > 1
            and selection.get_mode() != "multiple"
        ):
            indices = [indices[0]]
        elif isinstance(indices, int):
            indices = [indices]
        model = self.get_model()
        func = getattr(selection, func)
        for i in indices:
            # to avoid TypeError: Argument 3 does not allow None as a value from iter_nth_child()
            if i is None:
                continue
            itr = model.iter_nth_child(None, i)
            if not itr:
                continue
            func(itr)

    def select(self, indices):
        "select indices"
        self._modify_selection(indices, "select_iter")

    def unselect(self, indices):
        "unselect indices"
        self._modify_selection(indices, "unselect_iter")

    def get_row_data_from_path(self, path):
        """get row for given path

        path.get_depth() always 1 for SimpleList
        depth = path.get_depth()
        array has only one member for SimpleList"""
        indices = path.get_indices()
        index = indices[0]
        return list(self.get_model()[index])

    @classmethod
    def add_column_type(cls, **kwargs):
        "add column type"
        for name, typedict in kwargs.items():
            column_types[name] = typedict

    @classmethod
    def get_column_types(cls):
        "return column types"
        return column_types

    def add_page(self, number, page):
        "add a page to the database"
        x_res, y_res = None, None
        if page.resolution:
            x_res, y_res = page.resolution[0], page.resolution[1]
        self._cur.execute(
            """INSERT INTO page (id, image, x_res, y_res, text, annotations)
               VALUES (NULL, ?, ?, ?, ?, ?)""",
            (page.to_bytes(), x_res, y_res, page.text_layer, page.annotations),
        )
        thumb = page.get_pixbuf_at_scale(self.heightt, self.widtht)
        self.data.append([number, thumb, self._cur.lastrowid])
        self._con.commit()

    def find_page_by_number(self, number):
        "find a page by its page number using binary search"
        l = 0
        r = len(self.data) - 1
        while l <= r:
            mid = (l + r) // 2
            if self.data[mid][0] == number:
                return mid
            if self.data[mid][0] < number:
                l = mid + 1
            else:
                r = mid - 1
        return None

    def delete_page(self, number):
        "delete a page from the database"
        i = self.find_page_by_number(number)
        if i is None:
            raise ValueError(f"Page number {number} not found")
        self._cur.execute("DELETE FROM page WHERE id = ?", (self.data[i][2],))
        self._con.commit()
        del self.data[i]

    def get_page(self, number):
        "get a page from the database"
        i = self.find_page_by_number(number)
        if i is None:
            raise ValueError(f"Page number {number} not found")
        self._cur.execute(
            "SELECT image, x_res, y_res, text, annotations FROM page WHERE id = ?",
            (self.data[i][2],),
        )
        row = self._cur.fetchone()
        if row is None:
            raise ValueError(f"Page number {number} not found")
        return Page.from_bytes(
            row[0], resolution=(row[1], row[2]), text_layer=row[3], annotations=row[4]
        )

    def take_snapshot(self):
        "take a snapshot of the current state of the document"

        # in case the user has undone one or more action, before taking a
        # snapshot, remove the redo steps
        self._cur.execute(
            "DELETE FROM page_numbers WHERE action_id > ?", (self._action_id,)
        )
        self._action_id += 1

        # save current pages
        for row in self.data:
            self._cur.execute(
                "INSERT INTO page_numbers (action_id, page_number, page_id) VALUES (?, ?, ?)",
                (self._action_id, row[0], row[2]),
            )

        # delete those outside the undo limit
        self._cur.execute(
            "DELETE FROM page_numbers WHERE action_id < ?",
            (self._action_id - self.number_undo_steps,),
        )
        self._con.commit()

    def _get_snapshot(self, action_id):
        "fetch the snapshot of the document with the given action id"
        self._cur.execute(
            """SELECT page_number, page_id
                FROM page_numbers
                WHERE action_id = ?
                ORDER BY page_number""",
            (action_id,),
        )
        return self._cur.fetchall()


class TiedRow(list):
    "TiedRow is the lowest-level tie, allowing you to treat a row as an array of column data."

    def __init__(self, model, itr):
        super().__init__()
        self.model = model
        self.iter = itr

    def __getitem__(self, index):
        return self.model[self.iter][index]

    def __setitem__(self, index, value):
        self.model[self.iter][index] = value

    def __len__(self):
        return self.model.get_n_columns()

    def __contains__(self, index):
        return index < self.model.get_n_columns()

    def __delitem__(self, _index):
        raise NotImplementedError(
            "delete called on a TiedRow, but you can't change its size"
        )

    def extend(self, _items):
        raise NotImplementedError(
            "extend called on a TiedRow, but you can't change its size"
        )

    def clear(self):
        raise NotImplementedError(
            "clear called on a TiedRow, but you can't change its size"
        )

    def pop(self):
        raise NotImplementedError(
            "pop called on a TiedRow, but you can't change its size"
        )

    def append(self, _item):
        raise NotImplementedError(
            "append called on a TiedRow, but you can't change its size"
        )

    def insert(self, _index, _item):
        raise NotImplementedError(
            "push called on a TiedRow, but you can't change its size"
        )


class TiedList(list):
    "TiedList is an array in which each element is a row in the liststore."

    def __init__(self, model):
        super().__init__()
        self.model = model

    def __getitem__(self, index):
        itr = self.model.iter_nth_child(None, index)
        if itr is None:
            raise IndexError("list index out of range")
        return TiedRow(self.model, itr)

    def __setitem__(self, index, value):
        itr = self.model.iter_nth_child(None, index)
        if itr is None:
            raise IndexError("list index out of range")
        self.model[itr] = value

    def __len__(self):
        return len(self.model)

    def __str__(self):
        return str([list(x) for x in self.model])

    def __eq__(self, other):
        return [list(x) for x in self.model] == other

    def append(self, values):
        self.model.append(values)

    def __iter__(self):
        return iter(self.model)

    def extend(self, values):
        for row in values:
            self.model.append(row)

    def insert(self, position, row):
        self.model.insert(position, row)

    def pop(self):
        model = self.model
        index = model.iter_n_children(None) - 1
        itr = model.iter_nth_child(None, index)
        if itr is None:
            raise IndexError("pop from empty list")
        ret = list(model[itr])
        model.remove(itr)
        return ret

    def __delitem__(self, index):
        model = self.model
        itr = model.iter_nth_child(None, index)
        if itr is None:
            raise IndexError("list assignment index out of range")
        model.remove(itr)
