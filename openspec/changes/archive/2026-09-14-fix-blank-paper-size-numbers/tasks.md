## 1. Tests

- [x] 1.1 Update `test_mm_display_without_trailing_decimal` in
      `test_simplelist.py` to assert `cell.get_property("text")` (the GObject
      property GTK paints) instead of the Python attribute `cell.text`;
      confirm it fails against the current broken renderer.
- [x] 1.2 Add a regression test asserting `scalar_cell_renderer` sets the
      GObject `text` property the same way.

## 2. Fix the renderers

- [x] 2.1 In `float_g_cell_renderer` (simplelist.py) set the renderer text
      with `cell.set_property("text", ...)` instead of `cell.text = ...`.
- [x] 2.2 In `scalar_cell_renderer` (simplelist.py) do the same.

## 3. Verification

- [x] 3.1 Render `PaperList` (e.g. with int and fractional sizes) offscreen
      and confirm the dimension cells display their values.
- [x] 3.2 Run the full test suite with coverage (`pytest` per
      `pyproject.toml`) and confirm no covered-line regressions.
- [x] 3.3 Run `ruff format` and `ruff check` on the changed files.

## 4. Docs

- [x] 4.1 Note the fix in `changelog.md` (unreleased section).