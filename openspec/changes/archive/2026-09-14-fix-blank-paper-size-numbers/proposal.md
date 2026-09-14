## Why

Since the preserve-sub-millimeter-paper-sizes change, opening the paper-sizes
editor renders the dimension columns (Width/Height/Left/Top) blank: only the
name and units columns show text. The numbers are stored and formatted
correctly, but the new cell renderer never actually applies the text it
computes, so GTK paints empty cells.

## What Changes

- Fix the `"mm"` column renderer (`float_g_cell_renderer`) so it sets the
  GObject `text` property it computes instead of a plain Python attribute
  that GTK ignores. The formatted value (`210`, `115.2`) then displays.
- Align the renderer test in `test_simplelist.py` with the paint path: assert
  the GObject property (`get_property("text")`) rather than reading the
  Python attribute back, which currently passes while the cell stays blank.
- Apply the same fix to `scalar_cell_renderer` (identical latent bug, unused
  in practice) to keep both data-func renderers correct.
- No behavior change to the config, storage, edit, or apply paths; only
  display of the four dimension columns changes (blank -> value).

## Capabilities

### New Capabilities

<!-- None. -->

### Modified Capabilities

- `paper-size-editor`: the "Whole-millimetre sizes display without decimals"
  requirement gains a scenario asserting the values are actually rendered
  (visible) in the dimension cells, not merely formatted as a string.

## Impact

- `src/scantpaper/simplelist.py`: `float_g_cell_renderer` and
  `scalar_cell_renderer` switch from `cell.text = ...` to
  `cell.set_property("text", ...)`.
- `src/scantpaper/tests/test_simplelist.py`: `test_mm_display_without_trailing_decimal`
  asserts `get_property("text")`; add coverage for `scalar_cell_renderer` if
  feasible.
- No changes to `paperlist.py`, config, or other modules; no new
  dependencies.