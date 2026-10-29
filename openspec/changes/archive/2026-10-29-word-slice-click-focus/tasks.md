# Tasks

## 1. Slice predicate and click boundary

- [x] 1.1 Add `Bbox.is_slice` returning `type == "word"`; verify with a
  failing-first unit test that a word box is a slice while page, column and
  line boxes are not (`pytest src/scantpaper/tests/test_7_canvas.py -k
  is_slice`).
- [x] 1.2 Gate `Canvas._button_pressed()` on `is_slice` so a non-slice press
  leaves focus alone and calls `_start_draw()`; verify with a regression test
  that presses a line's whitespace under confidence sort, asserts the edit
  callback was not called, that no exception is raised, and that `_drawing` is
  true (`pytest src/scantpaper/tests/test_7_canvas.py -k container`).
- [x] 1.3 Verify a drag begun in container whitespace on a page with a loaded
  layer emits `selection-drawn` with the expected image-coordinate rectangle;
  extend the canvas selection-drawing test so its page box carries an edit
  callback.
- [x] 1.4 Update the tests that pin the old rule:
  `test_canvas_click_on_bbox_does_not_draw_selection` uses a word box, and
  `test_hit_test_nonzero_offset` still expects the geometric hit test to
  return a line; verify both pass.

## 2. Editor focus guard

- [x] 2.1 Make `LayerEditor.edit()` ignore a non-slice bbox, leaving
  `_current_bbox`, the control text and the canvas indexes untouched; verify
  with a unit test that calls `edit()` with a line box and asserts
  `canvas.set_index_by_bbox` was not called and the previous focus survived.
- [x] 2.2 Update `test_edit_sets_focus` so its mock carries a word type, and
  verify the layer editor suite passes (`pytest
  src/scantpaper/tests/test_layer.py -k edit`).
- [x] 2.3 Add an integration test driving the canvas hit test into a real
  `LayerEditor`: pressing container whitespace leaves the previous slice
  focused and accepting an empty control does not remove the line or its
  words; verify the test reproduces the old crash on the pre-fix code and
  passes with both guards in place.

## 3. Documentation and full verification

- [x] 3.1 Update the README layer-editing paragraph to state that a click
  focuses a slice only on the slice itself, and that pressing or dragging
  elsewhere in the layer pane starts a selection; verify the wording matches
  the implemented behaviour and stays wrapped at 80 characters.
- [x] 3.2 Run the full `pytest` suite and confirm coverage is no worse than
  before (no new uncovered or partial lines).
- [x] 3.3 Run `ruff format` and `ruff check` and confirm no diagnostics.
- [x] 3.4 Run `ty check .` and confirm no diagnostics.

## Workflow follow-up

- Archive the change after review and confirm the archived spec deltas applied
  cleanly.
