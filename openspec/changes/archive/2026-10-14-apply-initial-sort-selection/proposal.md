## Why

On first entry to the text layer editor, the sort criteria is initialised to
"Sort by confidence" in the combo, but the canvas's active sort index is never
applied, so navigation silently walks the boxes by **position**. The user must
cycle the combo to the other criteria and back to confidence on every fresh
session to get the behaviour the label promises.

## What Changes

- When the text layer editor is constructed, the initially selected sort
  method (confidence) SHALL be applied to the canvas immediately, so the
  displayed selection and the navigation order agree from the start.
- The sort state SHALL be applied through the existing `sort-changed` /
  `_sort` path (no new mechanism), by replaying the combo's initial active
  value after the editor has wired its handlers.

## Capabilities

### New Capabilities

- none

### Modified Capabilities

- `layer-editing`: a new requirement that the initial sort selection shown in
  the control is applied to the canvas's navigation order on first entry,
  closing the gap where the control displayed confidence but navigation used
  position.

## Impact

- `src/scantpaper/layer.py`: `LayerEditor._connect_controls` (and the sort
  combo wiring in `LayerControls`) so the initial selection is applied after
  handler connection.
- `src/scantpaper/tests/test_layer.py`: new test asserting the canvas is
  sorted by the initially selected method on first entry.
- No public API, dependency, or data-model changes.
