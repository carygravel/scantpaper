# Tasks

- [x] 1.1 Write a failing unit test in `test_dialog_paperlist.py` asserting
      that a paper size with a fractional dimension (e.g. `x: 115.2`)
      loads into the `PaperList` model as a float and reads back as `115.2`
      (not `115`).
- [x] 1.2 In `src/scantpaper/dialog/paperlist.py` change the Width/Height/
      Left/Top column types from `"int"` to `"double"` (paperlist.py:16-19)
      so the `Gtk.ListStore` stores float values without truncation.

## 2. Accept fractional dimension input

- [x] 2.1 Write a failing unit test in `test_simplelist.py` asserting that
      editing a `"double"`-typed cell with the text `115.2` stores the float
      `115.2` via `do_text_cell_edited`.
- [x] 2.2 Write a failing unit test in `test_simplelist.py` asserting that
      editing a `"double"`-typed cell with non-numeric text rejects the edit
      and keeps the previous value.
- [x] 2.3 Confirm `SimpleList.do_text_cell_edited` (simplelist.py:153-161)
      already parses `"double"` columns with `float(new_text)`; fix if the
      tests in 2.1/2.2 expose a gap.

## 3. Display whole numbers without a trailing decimal

- [x] 3.1 Write a failing unit test asserting that a `"double"`-typed cell
      holding `210.0` renders as `210` (no trailing `.0`) and a cell holding
      `115.2` renders as `115.2`.
- [x] 3.2 Add a cell display function (e.g. via
      `Gtk.TreeViewColumn.set_cell_data_func` or a dedicated column type in
      `simplelist.py` `column_types`) that formats float cell values with
      `f"{value:g}"`, and apply it to the four dimension columns in
      `PaperList`.

## 4. Backward compatibility

- [x] 4.1 Write a unit test asserting that a paper size stored with
      whole-millimetre integer values in the config (e.g. `x: 210`) reads
      back numerically equal to `210` after a `PaperList` round-trip.
- [x] 4.2 Write a unit test asserting `do_apply_paper_sizes`-style
      round-trip writes `210.0` (float) for an integer-defined size and that
      JSON serialisation of the result keeps it numerically identical.

## 5. Existing tests and docs

- [x] 5.1 Review `test_dialog_paperlist.py`, `test_simplelist.py` and the
      scan-dialog paper-size tests for assertions that pin the old `"int"`
      column types and align them with the new float storage.
- [x] 5.2 Run the full test suite with coverage and confirm no covered-line
      regressions (`pytest` per pyproject.toml).
- [x] 5.3 Run `ruff format` and `ruff check` on all touched files.
- [x] 5.4 Document the change in `changelog.md` (unreleased section).