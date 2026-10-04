## 1. Reproduction tests (written first, expected to fail)

- [x] 1.1 Add a `tests/test_7_canvas.py` test asserting a deleted word is absent
  from `canvas.hocr()` and from its parent's children, and that the surviving
  sibling texts are still present. Verify it fails against current `main` before
  any implementation change.
- [x] 1.2 Add a `tests/test_7_canvas.py` test asserting the same for a word
  deleted from an annotation layer (page-level parent), and for the last word of
  a line leaving no empty `ocr_line` element in `hocr()`. Verify both fail
  first.
- [x] 1.3 Add a rendering test asserting that after a word's text changes, the
  text layout used for the next draw carries the new text. Verify it fails
  first.
- [x] 1.4 Add a `tests/test_layer.py` integration test driving the real
  `LayerEditor` against a real `Canvas` (no `MagicMock` bbox): delete a slice,
  then assert it is absent from the committed layer; and accept an emptied
  slice, then assert the slice is gone and the control shows a different slice.
  Verify both fail first.
- [x] 1.5 Add a navigation test covering deletion in *position* order: delete
  every word in turn and assert forward iteration visits exactly the survivors
  in reading order and never a deleted word. Verify it fails first.
- [x] 1.6 Add a round-trip test asserting
  `Bboxtree.from_hocr(canvas.hocr())` preserves the scene graph's word count and
  texts. Verify it passes before and after the change (guards against
  regressions in unrelated to deletion).

## 2. Scene graph ownership (design D1, D2)

- [x] 2.1 Change `Bbox.get_children()` to return `self.children` directly and
  drop the `isinstance` filter; add `Bbox.detach_from_parent()` performing
  identity-based removal from `self.parent.children`. Verify the existing
  `tests/test_7_canvas.py` hierarchy assertions still pass and task 1.1 now
  passes.
- [x] 2.2 Move `update_box`'s data effects onto `Bbox` as a side-effect-free
  setter (text, bbox, confidence) and move the index maintenance and
  `queue_draw` onto a new `Canvas.update_word(bbox, text, selection)`. Verify
  task 1.3 passes and `tests/test_7_canvas.py` update scenarios still pass.
- [x] 2.3 Move `delete_box`'s effects onto `Canvas.delete_word(bbox)`, which
  detaches the bbox, removes it from the confidence index by identity, rebuilds
  the position cursor, prunes empty ancestors and redraws. Verify tasks 1.1,
  1.2 and 1.5 pass.
- [x] 2.4 Route `Canvas.add_box` and `Canvas.add_word`'s index insertion through
  the same owner so add/copy no longer reach into `ListIter` from outside, and
  verify the existing add-box scenarios and `tests/test_layer.py` copy/add tests
  still pass.
- [x] 2.5 Delete or reduce `Bbox.delete_box` / `Bbox.update_box` to thin data
  setters with no canvas side effects, and verify no remaining caller reaches
  into `Canvas.confidence_index` or `Canvas.position_index` from `Bbox`
  (grep for it).

## 3. Index consistency (design D3)

- [x] 3.1 Add `ListIter.remove_bbox(bbox)` performing identity-based removal and
  clamping the cursor to the following entry (or the preceding one at the end);
  keep `remove_current_box_from_index` only if still used elsewhere. Verify
  tasks 1.1 and 1.5 pass.
- [x] 3.2 Rebuild the position `TreeIter` from the next surviving word (falling
  back to the previous) after a deletion, in both sort orders, rather than
  advancing a possibly-stale iterator. Verify task 1.5 passes with the sort
  order parameterised over both values.
- [x] 3.3 Re-establish both cursors after a correction so a slice corrected to
  full confidence sits at the high-confidence end and is absent from its old
  position. Verify with a test asserting forward confidence iteration order
  before and after a correction.
- [x] 3.4 Make `Canvas.get_current_bbox()` and the navigation getters report
  "no current slice" as `None` instead of raising `StopIteration`, and verify a
  test covering deleting the final word on a page.
- [x] 3.5 Confirm no `logger.warning("Attempted to delete undefined index from
  confidence list")` is emitted during the task 3.2–3.4 test runs, by asserting
  on `caplog` in at least one test.

## 4. Empty ancestor pruning (design D5)

- [x] 4.1 Extract the "no text and no descendants" predicate from
  `bboxtree._prune_empty_branches` into a form usable by both the parse path and
  the canvas delete path, keeping the existing parse behaviour identical.
  Verify the `tests/test_75_bboxtree.py` prune tests and
  `tests/test_101_document.py`
  still pass unchanged.
- [x] 4.2 Walk up from a deleted word, removing ancestors that have become
  empty, exempting the root page box. Verify task 1.2's "last word of a line"
  and "last line of a paragraph" cases pass, and that `hocr()` for a fully
  emptied page contains no empty word/line/paragraph/column element while still
  serialising valid page geometry.
- [x] 4.3 Verify task 1.6's round-trip test still passes after pruning, i.e. a
  page with all words deleted round-trips to zero words rather than to empty
  line elements.

## 5. Repaint correctness (design D6)

- [x] 5.1 Remove `Bbox.pango_layout` and move layout reuse into a per-draw map
  on `Canvas`, keyed by bbox. Verify task 1.3 passes and the existing rendering
  and rotation scenarios in `tests/test_7_canvas.py` still pass.
- [x] 5.2 Verify no drawing-time object is stored on a `Bbox` (grep for
  `pango_layout` and confirm `Bbox` holds only data and pure derivation).
- [x] 5.3 Confirm `_draw_bbox` still reuses one layout per box per frame, and
  that redraws triggered by zoom, pan and resize do not regress measurably —
  record the timing before and after on the largest page fixture available.

## 6. Editor cursor semantics (design D4, D7)

- [x] 6.1 Make `LayerEditor.ok` treat empty control text as a delete routed
  through the same delete path as the Delete button, and verify the existing
  empty-OK behaviour is pinned by a test (the user-visible contract is
  unchanged even though the mechanism moved off `update_box`).
- [x] 6.2 Stop `LayerEditor.ok` re-focusing `_current_bbox` after a deletion;
  move the editor cursor instead, and verify task 1.4's empty-OK case shows a
  different slice rather than restoring the deleted text.
- [x] 6.3 Make the editor clear its control and leave navigation inert when no
  slice survives, instead of raising, and verify deleting every slice on a page
  leaves an empty control and a layer with no text slices.
- [x] 6.4 Verify typing and accepting immediately after a deletion applies to
  the slice the editor moved to, and that the deleted slice stays absent.
- [x] 6.5 Verify switching sort order between confidence and position keeps the
  same slice focused and the same text displayed, and that no word is lost or
  duplicated in `hocr()` after switching.
- [x] 6.6 Verify `_current_bbox` is never left pointing at a detached bbox after
  any editor action, by asserting the focused bbox is a member of the scene
  graph after each of add, copy, ok-with-text, ok-empty, and delete.

## 7. Annotation layer parity

- [x] 7.1 Verify add, copy, delete and correct all behave identically for the
  annotation layer through its editor, including that a deleted note is absent
  from `page.annotations`.
- [x] 7.2 Verify the first annotation added to a page with no annotation layer
  establishes the layer and is immediately editable, and that the placeholder
  text is used when the control is empty.
- [x] 7.3 Verify the round-trip of an annotation layer through
  `Bboxtree.from_hocr(canvas.hocr())` preserves note count and texts.

## 8. Documentation and gates

- [x] 8.1 Update `README.md` to state that slice deletions and corrections are
  reflected in the saved PDF's text layer, in the OCR section.
- [x] 8.2 Add a `changelog.md` entry under 3.0.21 (unreleased) covering the
  three user-visible fixes: delete not removing text from saved output,
  corrections not repainting on the page, and emptied slices being rejected.
- [x] 8.3 Run `pytest` and confirm the full suite passes with coverage no worse
  than before the change.
- [x] 8.4 Run `ruff format` and `ruff check` and confirm no lint errors, with
  no new `noqa` or `per-file-ignores`.
- [x] 8.5 Run `ty check .` and confirm no diagnostics, with no additions to
  `[tool.ty.rules]`.
- [x] 8.6 Run `openspec validate fix-ocr-layer-editing --strict` and confirm the
  change and its deltas validate.
- [x] 8.7 Manually verify in the running application: delete a slice and confirm
  the word is neither drawn nor searchable in the saved PDF; correct a slice and
  confirm the page repaints; empty a slice with select-all + Delete + OK and
  confirm it deletes rather than springing back.
