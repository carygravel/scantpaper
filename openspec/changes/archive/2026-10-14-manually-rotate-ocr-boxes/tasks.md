## 1. Controls

- [x] 1.1 Add rotate-clockwise and rotate-anticlockwise signals to
  `LayerControls.__gsignals__` in `src/scantpaper/layer.py`.
- [x] 1.2 Add two icon buttons to `LayerControls` emitting those signals, with
  tooltips describing the rotation direction.
- [x] 1.3 Add a `set_rotate_enabled(enabled)` helper on `LayerControls` (and
  explanatory tooltips when disabled) mirroring `set_add_enabled`.

## 2. Editor behaviour

- [x] 2.1 Wire the two rotate signals in `LayerEditor._connect_controls` to new
  handlers in `src/scantpaper/layer.py`.
- [x] 2.2 Implement the rotate handlers: no-op when `_current_bbox` is None;
  otherwise adjust `_current_bbox.textangle` by +90 (clockwise) or -90
  (anticlockwise) mod 360.
- [x] 2.3 After rotating, call `self.canvas.queue_draw()` to redraw the page
  and `self._commit()` to persist the layer (reusing the undoable commit path).
- [x] 2.4 Update the rotate controls' enabled state whenever the focused slice
  changes (in `edit`, `clear`, `add`, and after rotate), so they are disabled
  when no slice is focused.

## 3. New-slice inheritance

- [x] 3.1 In `LayerEditor.add`, pass the focused slice's `textangle` (0 when
  nothing is focused) to `canvas.add_box` so a newly added slice inherits the
  current rotation.
- [x] 3.2 Confirm `_new_layer_json` (first-slice-on-empty-page path) accepts a
  rotation and emits `textangle` in the seed layer, so the very first vertical
  slice is drawn rotated.

## 4. Tests

- [x] 4.1 Add canvas tests to `src/scantpaper/tests/test_7_canvas.py` that a
  slice added with a `textangle` is drawn/serialised with it, and that adding
  with no angle defaults to 0.
- [x] 4.2 Add layer-editor tests to `src/scantpaper/tests/test_layer.py` /
  `test_text_layer_control.py`: rotating clockwise and anticlockwise updates
  the slice's `textangle`, redraws, and persists via the layer; no slice
  focused means the control is disabled and rotating does nothing.
- [x] 4.3 Add a test that a slice added while a rotated slice is focused
  inherits that rotation, and that other slices are left unchanged.
- [x] 4.4 Add a test that a rotated slice's `textangle` survives the hOCR
  round-trip into the persisted layer (and, if cheap to exercise, that it is
  emitted in the saved text layer).

## 5. Quality gates

- [x] 5.1 Run `ruff format` and `ruff check` on the changed files and fix any
  findings without disabling checks.
- [x] 5.2 Run `ty check .` and fix any diagnostics.
- [x] 5.3 Run the full `pytest` suite and confirm coverage and pass rate meet
  the configured thresholds (no newly uncovered lines beyond the permitted
  `if TYPE_CHECKING:` imports).
- [x] 5.4 Update README.md if the user-visible behaviour (rotating text slices)
  is documented there.
