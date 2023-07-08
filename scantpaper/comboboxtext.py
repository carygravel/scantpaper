"a ComboBoxText widget with an index"

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GObject, Gtk  # pylint: disable=wrong-import-position


class ComboBoxText(Gtk.ComboBoxText):
    "a ComboBoxText widget with an index"
    index_column = GObject.Property(
        type=int,
        minimum=0,
        maximum=2,
        default=0,
        nick="Index column",
        blurb="Column with which the data is indexed",
    )
    text_column = GObject.Property(
        type=int,
        minimum=0,
        maximum=2,
        default=1,
        nick="Text column",
        blurb="Column of text to be displayed",
    )

    def __init__(self, *args, **kwargs):
        data = None
        if "data" in kwargs:
            data = kwargs["data"]
            del kwargs["data"]
        super().__init__(*args, **kwargs)
        if data is not None:
            col = self.text_column
            for row in data:
                self.append_text(row[col])
            self.data = data

    def set_active_index(self, index):
        """Set the current active item of a combobox
        based on the index column of the array"""
        if index is None:
            return
        col = self.index_column
        for i, row in enumerate(self.data):
            if row[col] is not None and row[col] == index:
                self.set_active(i)

    def get_active_index(self):
        """Get the current active item of a combobox
        based on the index column of the array"""
        return self.data[self.get_active()][self.index_column]

    def get_row_by_text(self, text):
        """Get row number with $text"""
        model = self.get_model()
        if model is not None and text is not None:
            col = self.index_column
            for i, row in enumerate(model):
                if row[col] == text:
                    return i
        return -1

    def set_active_by_text(self, text):
        "set row by the item text"
        index = self.get_row_by_text(text)
        if index > -1 or text is None:
            self.set_active(index)

    def get_num_rows(self):
        "return number of rows"
        return len(self.get_model())

    def remove_item_by_text(self, text):
        "remove row by the item text"
        if text is not None:
            i = self.get_row_by_text(text)
            if i > -1:
                if self.get_active() == i:
                    self.set_active(-1)
                self.remove(i)
