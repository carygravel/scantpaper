## 1. Tests first (TDD)

- [x] 1.1 In `test_layer.py`, add a test that activating rotate-clockwise
  changes a slice's stored `textangle` so its drawn angle increases by 90
  (clockwise), and that rotate-anticlockwise does the opposite.
- [x] 1.2 In `test_layer.py`, add a test that adding a slice while a rotated
  slice is focused draws the new slice at the focused slice's angle, including
  the case where the new slice is inserted as a child of that same focused
  slice (the angle must not be applied twice).
- [x] 1.3 In `test_7_canvas.py`, add a test that a slice nested below a rotated
  ancestor (e.g. a page with `textangle 90`) is drawn with the ancestor's angle
  at every depth, and that a fully unrotated tree is unchanged.
- [x] 1.4 Confirm the new tests fail against the current code for the expected
  reason before implementing.

## 2. Ancestor-angle helper

- [x] 2.1 Add public `Canvas.accumulated_textangle(bbox)` returning the sum of
  `textangle` over a box *and* its ancestors (inclusive), i.e. the rotation of
  the box's local frame, returning 0 for a root parent.
- [x] 2.2 Change `add_box`'s transformation fallback to use
  `accumulated_textangle(parent)` for `transformation[0]` (keeping
  `parent.bbox.x/y` for the other slots and `[0, 0, 0]` for a root parent).
- [x] 2.3 Remove the now-dead `transformations` list from `set_text` and
  `_boxed_text`, adjusting `_boxed_text` to no longer read or append to it.

## 3. Rotation sign

- [x] 3.1 Swap the deltas so `rotate_clockwise` applies `-90` and
  `rotate_anticlockwise` applies `+90` through `_apply_rotation`.

## 4. Inherited rotation when adding

- [x] 4.1 In `LayerEditor.add`, resolve the new slice's parent once via
  `canvas.get_bbox_at(selection)`, preserving the current behaviour when the
  selection is not over any box.
- [x] 4.2 Compute the added slice's `textangle` as
  `(accumulated_textangle(focused) - accumulated_textangle(parent)) % 360`, or
  0 when nothing is focused, and pass the resolved parent explicitly to
  `add_box`.
- [x] 4.3 Apply the same inherited angle through `_new_layer_json` for the
  first-slice-on-an-empty-layer path.

## 5. Verification

- [x] 5.1 Run the affected tests (`pytest` on `test_layer.py` and
  `test_7_canvas.py`) and the full suite.
- [x] 5.2 Run `ruff format` and `ruff check` with no new findings.
- [x] 5.3 Run `ty check .` with no new diagnostics.
- [x] 5.4 Update `README.md` if the rotation direction wording there changed
  meaning, and archive the change once approved.
