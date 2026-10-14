## 1. Expose the active sort method from the control bar

- [x] 1.1 Add a `get_sort_method()` accessor on `LayerControls` returning the
  combo's active method name (via `ComboBoxText.get_active_index()`), keeping
  the combo encapsulated. Returns the default "confidence" when no row is
  active.
- [x] 1.2 Add a test asserting `LayerControls.get_sort_method()` returns the
  selected method (confidence at construction, then position after
  `set_active(1)`).

## 2. Apply the initial sort selection to the canvas

- [x] 2.1 In `LayerEditor._connect_controls`, after connecting
  `sort-changed` to `_sort`, replay the current sort method by calling
  `_sort` with the value from `self.controls.get_sort_method()` so the
  initially selected method is applied on construction.
- [x] 2.2 Add a test in `test_layer.py` that constructing a `LayerEditor`
  with `features=("sort",)` calls `canvas.sort_by_confidence()` (the default
  selection), and that the canvas's `_current_index` is `"confidence"` after
  construction.

## 3. Quality gates

- [x] 3.1 Run `pytest` and confirm all tests pass and coverage thresholds hold.
- [x] 3.2 Run `ruff format` / `ruff check` with no errors.
- [x] 3.3 Run `ty check .` with no diagnostics.
- [x] 3.4 Confirm uncovered/partially-covered line counts are not worse than
  before.
