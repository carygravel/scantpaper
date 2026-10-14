## 1. Editor behaviour

- [x] 1.1 In `LayerEditor.ok()` (`src/scantpaper/layer.py`), capture the
      successor with `self.canvas.get_next_bbox()` before calling `update_word`,
      then focus that captured successor via `self.edit(successor)` instead of
      `self.edit(bbox)`, leaving the empty-text → delete branch unchanged.
- [x] 1.2 Verify the correction branch still writes the corrected text,
      commits, and persists (existing `_commit()` path untouched).

## 2. Tests

- [x] 2.1 Update `test_ok_commits_and_reedits` in `tests/test_layer.py` to
      assert that after a successful correction the editor focuses the next
      slice returned by `get_next_bbox()`, not the corrected slice.
- [x] 2.2 Add an editor-level test that, under confidence sort, OK advances
      focus to the next-least-confident surviving slice and leaves the
      corrected slice in the layer with its corrected text.
- [x] 2.3 Add an editor-level test that, under position sort, OK advances focus
      to the next slice in reading order.
- [x] 2.4 Add a test that correcting the final slice in navigation order keeps
      that slice focused.
- [x] 2.5 Confirm canvas-level tests such as
      `test_correction_moves_word_in_confidence_order` still pass unchanged.

## 3. Quality gates

- [x] 3.1 Run the full suite: `pytest` passes and coverage is unchanged or
      better.
- [x] 3.2 Run `ruff format` and `ruff check`; no new lint errors.
- [x] 3.3 Run `ty check .`; no new type diagnostics.
- [x] 3.4 Update README.md if any user-visible behaviour is documented there.
