## 1. Fix the render axis for 180 degrees

- [x] 1.1 Add a failing test in `tests/test_7_canvas.py`: two slices with the same
  text and the same bounding box, one at `textangle` 0 and one at 180, render
  their text at the same size (assert on the ink extents/scale used, not a
  pixel snapshot); add a case where the 180-degree angle is inherited from an
  ancestor.
- [x] 1.2 In `src/scantpaper/canvas.py` `_draw_bbox`, replace the truthiness
  test with `scale = (w if angle % 180 == 0 else h) / text_w` and make the new
  test pass.

## 2. Text measurement and the fit helper

- [x] 2.1 Add a Canvas method that measures a text's ink extents at the fixed
  layout font, reusing `_create_pango_layout`; test it in
  `tests/test_7_canvas.py` (non-zero width for a normal word, stable for the
  same text).
- [x] 2.2 Add a pure helper (no GTK) that takes the selection width and height,
  the text ink extents, and whether a quarter turn is inherited, and returns 0
  or 90 using the min-fit comparison in `design.md`; unit-test the tall/narrow,
  wide, slightly-tall-short-text, near-square-tie, and degenerate-metrics
  cases.

## 3. Apply the guess when slices are created

- [x] 3.1 Wire the helper into `LayerEditor.add` so a new slice at a selection
  on a flat (or 180-degree) frame gets the guessed angle, while an inherited
  quarter turn is left untouched; cover both in `tests/test_layer.py`.
- [x] 3.2 Apply the same guess to `LayerEditor.copy` and to the first-slice
  path `_new_layer_json`; test each.
- [x] 3.3 Add an integration test asserting a tall selection produces a slice
  whose serialised layer records a 90-degree angle and that the slice remains
  correctable with the rotate controls.

## 4. Documentation and quality gates

- [x] 4.1 Update the OCR section of `README.md` to state that a new slice's
  orientation is inferred from the drawn rectangle and its text when no
  rotation is inherited.
- [x] 4.2 Run `ruff format`, `ruff check .`, `ty check .`, and `pytest`; fix
  any diagnostics and confirm coverage is not reduced.
