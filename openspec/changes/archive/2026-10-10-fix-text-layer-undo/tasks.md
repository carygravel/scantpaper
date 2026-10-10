## 1. Version page content in the document thread

- [x] 1.1 Add a private page-row versioning helper in `docthread.py`
      (`_version_page(initial_page_id, **overrides)`): SELECT the current
      `page_order.page_id` for `(initial_page_id, action_id)`, no-op with
      a warning when no row exists, INSERT a copy of that row with the
      overrides and `saved = FALSE`, repoint the action's
      `page_order.page_id`
- [x] 1.2 `do_set_text`: after `_take_snapshot()`, call the helper with
      `text=` instead of `UPDATE page SET text = ?`
- [x] 1.3 `do_set_annotations`: same, with `annotations=`
- [x] 1.4 `do_set_resolution`: add `_take_snapshot()` and call the helper
      with `x_res=`/`y_res=`
- [x] 1.5 `do_set_mean_std_dev`: add `_take_snapshot()` and call the
      helper with `mean=`/`std_dev=`
- [x] 1.6 Rewrite `test_do_set_text`, `test_do_set_annotations`,
      `test_do_set_resolution`, `test_do_set_mean_std_dev` as round-trip
      behaviour tests on a real in-memory DB: set -> undo -> previous
      value, then redo -> new value; assert the stored image id is
      unchanged
- [x] 1.7 Add tests for the dirty flag: after a content edit on a saved
      page (a) `pages_saved()` is false, (b) undoing the edit restores
      `pages_saved()` to true, (c) `set_saved` after the edit marks the
      current state saved again

## 2. Layer editor focus after a rebuild

- [x] 2.1 `LayerEditor.create()`: clear the focused slice and the control
      text at the start (before parsing the rebuilt layer)
- [x] 2.2 Add an editor-level clear that resets focus and empties the
      canvas, and use it for the "no layer" branches in `_on_page_loaded`
      (`session_mixins.py:327,334`) in place of `t_canvas/a_canvas
      .clear_text()`
- [x] 2.3 Extend `test_layer.py`: a rebuild while a slice is focused drops
      focus, and a following `ok`/`delete` acts only on slices in the
      rebuilt tree; update `test_session_mixins.py` for the new clear path

## 3. Properties dialog applies as one undo step

- [x] 3.1 Wrap the per-page `set_resolution` sends in
      `begin_undo_batch()`/`end_undo_batch()` in
      `edit_menu_mixins.properties` (guard with try/finally)
- [x] 3.2 Update `test_edit_menu_mixins` so the apply asserts the batch
      begin/end around the `set_resolution` send
- [x] 3.3 Add a thread-level test: batched resolution changes to several
      pages undo in one step, restoring every page's previous resolution

## 4. Regression coverage for the reported bug

- [x] 4.1 Add a docthread regression test mirroring the OCR undo test:
      `set_text` -> `do_undo` restores the previous text layer, `do_redo`
      re-applies it, no image row is created
- [x] 4.2 Add a session_mixins/editor test: after a layer edit is undone,
      loading the page rebuilds the layer canvas from the restored layer

## 5. README and quality gates

- [x] 5.1 Update README.md if it documents undo/redo or the layer editor,
      noting text/annotation corrections are now undoable
- [x] 5.2 `pytest` full suite passes; uncovered/partially covered line
      counts are not worse than before
- [x] 5.3 `ruff format` and `ruff check` pass
- [x] 5.4 `ty check .` reports no diagnostics