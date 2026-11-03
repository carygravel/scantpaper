# Tasks

## 1. Ignore selection input without an image

- [x] 1.1 Add an early return to `Selector.button_pressed` when the view has no
  pixbuf, before `dragging`, `drag_start` or the selection is changed. Verify a
  press with no pixbuf neither raises nor sets `dragging`.
- [x] 1.2 Make `Selector._update_selection` a no-op that clears the in-progress
  gesture when the view has no pixbuf, so motion during a missing image cannot
  resume a stale drag. Verify pressing with no pixbuf and then moving raises no
  exception.

## 2. Normalise the drag origin

- [x] 2.1 Initialise the selector's drag origin as an empty mapping and use
  `.get(axis)` wherever an axis is read. Verify a press with a pixbuf still
  records both axes and the existing selector tests pass.
- [x] 2.2 Change `cursor_type_at_point` to treat an absent axis and one whose
  value is `None` as unset, and make `_update_selection` fall back to the current
  selection or the event coordinate instead of casting an unset axis. Verify
  direct `_update_selection` tests for `{}` and `{"x": None}` origins pass.

## 3. Cover the no-image gestures and document the fix

- [x] 3.1 Add unit tests for `Selector` and `SelectorDragger` that press and
  move with no pixbuf using the primary button, assert no selection change and
  no exception, and repeat for the combined tool's middle button. Verify the
  tests pass.
- [x] 3.2 Add a test that ignores a press before a pixbuf exists, then displays
  a pixbuf and performs a real drag, asserting the selection starts at the new
  press and the ignored gesture left no origin behind. Verify the test passes.
- [x] 3.3 Add a `changelog.md` entry describing the empty-view fix. Verify
  `pytest -q src/scantpaper/tests/test_markdown_line_length.py` passes (ignoring
  the coverage gate for this partial run).

## 4. Integration checks

- [x] 4.1 Run `ruff format --check .`, `ruff check .`, `ty check .` and the full
  `pytest` suite, and confirm the coverage gate still passes with no new
  uncovered or partially covered lines.
- [x] 4.2 Run `openspec validate --specs --strict --no-interactive` and
  `openspec validate --archived --no-interactive`, plus
  `openspec validate ignore-selector-input-without-image --strict
  --no-interactive`, and confirm they pass.
