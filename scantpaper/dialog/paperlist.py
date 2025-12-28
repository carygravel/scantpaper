"A list of paper sizes"

import re
from simplelist import SimpleList
from i18n import _


class PaperList(SimpleList):
    "A list of paper sizes"

    def __init__(self, formats):
        columns = {
            _("Name"): "text",
            _("Width"): "int",
            _("Height"): "int",
            _("Left"): "int",
            _("Top"): "int",
            _("Units"): "text",
        }
        super().__init__(**columns)
        for name in formats:
            self.data.append(
                [
                    name,
                    formats[name]["x"],
                    formats[name]["y"],
                    formats[name]["l"],
                    formats[name]["t"],
                    "mm",
                ]
            )

        # Set everything to be editable except the units
        columns = self.get_columns()
        for col in range(len(columns) - 1):
            self.set_column_editable(col, True)

        self.get_column(0).set_sort_column_id(0)

    def do_add_clicked(self):
        "Add button callback"
        rows = self.get_selected_indices()
        if not rows and len(self.data) > 0:
            rows = [0]
        name = self.data[rows[0]][0]
        version = 2
        i = 0
        while i < len(self.data):
            if self.data[i][0] == f"{name} ({version})":
                version += 1
                i = 0
            else:
                i += 1

        line = [f"{name} ({version})"]
        columns = self.get_columns()
        for i in range(1, len(columns)):
            line.append(self.data[rows[0]][i])

        self.data.insert(rows[0] + 1, line)

    def do_remove_clicked(self):
        "Remove button callback"
        rows = self.get_selected_indices()
        if len(rows) == len(self.data):
            raise IndexError(_("Cannot delete all paper sizes"))

        while rows:
            del self.data[rows.pop(0)]

    def do_paper_sizes_row_changed(self, _model, path, _iter):
        "Setup the callback to check that no two Names are the same"
        path = int(path.to_string())
        for index, row in enumerate(self.data):
            if index != path and self.data[path][0] == row[0]:
                name = row[0]
                version = 2
                regex = re.search(
                    r"""
                    (.*) # name
                    [ ][(] # space, opening bracket
                    (\d+) # version
                    [)] # closing bracket
                """,
                    name,
                    re.MULTILINE | re.DOTALL | re.VERBOSE,
                )
                if regex:
                    name = regex.group(1)
                    version = int(regex.group(2)) + 1

                self.data[path][0] = f"{name} ({version})"
                return
