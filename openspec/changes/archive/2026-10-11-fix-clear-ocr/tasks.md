# fix-clear-ocr Tasks

## 1. Implementation

- [x] 1.1 Rewrite `clear_ocr()` in `src/scantpaper/edit_menu_mixins.py` to
      iterate `self.slist.get_selected_indices()` and dispatch a
      `set_text(page_id, "[]")` worker request for each selected page via
      `self.slist.thread.send("set_text", self.slist.data[i][2], "[]")`,
      instead of mutating `self.slist.data[i][2].text_layer`.
- [x] 1.2 Wrap the per-page loop in `begin_undo_batch()` / `end_undo_batch()`
      (balanced in a `try/finally`) so a multi-page clear forms a single undo
      step, matching the pattern in `properties_apply_callback`.
- [x] 1.3 Keep the `self.t_canvas.clear_text()` call so the on-screen OCR
      overlay clears immediately. Clear OCR does NOT reset `ocr_flag`/
      `ocr_time` (Option A): those are transient, non-persisted in-memory
      values, so clearing the text layer is sufficient.

## 2. Tests

- [x] 2.1 Rewrite `tests/test_edit_menu_mixins.py::test_clear_ocr` to model
      `slist.data[i]` as `[number, thumb, page_id]` (page id, not a `Page`)
      and assert `thread.send("set_text", page_id, "[]")` is dispatched for
      each selected page.
- [x] 2.2 Add a test that a multi-page clear calls `begin_undo_batch` before
      and `end_undo_batch` after the `set_text` sends, and that no pages
      selected is a no-op.

## 3. Verification

- [x] 3.1 Run `pytest` and confirm the full suite passes with no drop in
      covered-line counts.
- [x] 3.2 Run `ruff format` and `ruff check` on the changed files with no new
      diagnostics.
- [x] 3.3 Run `ty check .` and confirm no new type diagnostics.
