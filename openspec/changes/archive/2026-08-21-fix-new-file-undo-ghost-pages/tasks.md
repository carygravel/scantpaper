## 1. Regression test first (TDD)

- [x] 1.1 Add a `DocThread`-level regression test in `test_docthread.py` reproducing issue #74: add page A, simulate the frontend-only clear (pre-fix behaviour), add page B, take an edit snapshot, run `do_undo()` and assert the restored snapshot does not contain page A. Confirm it fails against current code.
      *(Implemented as a pair: `test_issue_74_ghost_page_mechanism` pins the pre-fix ghost mechanism; `test_undo_after_delete_all_has_no_ghost` asserts the post-fix invariant via the thread-routed clear. Both pass against current code — the thread machinery was already correct, so the red→green demonstration lives in tasks 1.2/3.2 where the fix lands.)*
- [x] 1.2 Add a `Document`/`DocThread` integration test in `test_101_document.py`: pages present → clear-all via the new path → undo restores them → redo clears them again. *(Confirmed red: `'Document' object has no attribute 'delete_all_pages'`.)*

## 2. Document-level delete-all

- [x] 2.1 Add `Document.delete_all_pages()` in `basedocument.py`, modelled on `delete_selection()`: collect all `initial_page_id`s from `self.data`, send `"delete_pages"` with those ids, remove all model rows in the `data_callback`.
- [x] 2.2 Unit-test `delete_all_pages()` in `test_basedocument.py` following the existing `delete_pages` mock pattern (request contents, callback removes rows, finished_callback invoked).

## 3. Rewire New File

- [x] 3.1 Rewrite `FileMenuMixins.new_()` in `file_menu_mixins.py`: keep the `_pages_saved()` guard; short-circuit when `slist.data` is empty; reset view state (pixbuf, canvases, `_current_page`) as today; dispatch deletion via `delete_all_pages()`.
- [x] 3.2 Update `test_file_menu_mixins.py`: empty-document no-op sends nothing; non-empty dispatches one delete request with all page ids; cancelled unsaved-changes prompt sends nothing; view-state resets still occur.
- [x] 3.3 Verify signal blocking around model mutation matches the pattern used by `delete_selection()` (row_changed / selection_changed) and that no regression in thumbnail updates occurs after clear + rescan. *(Blocking now happens inside the delete response callback, mirroring `undo()`; no other code depended on the synchronous clear.)*

## 4. Undo/redo semantics

- [x] 4.1 Test that after "New File" + scan B + edit + single undo, the page list contains only unedited B (spec regression scenario). *(test_issue_74_new_file_then_scan_edit_undo)*
- [x] 4.2 Test that undo immediately after "New File" restores the pre-clear pages and redo re-clears them (`can_undo()`/`can_redo()` states included). *(Extended test_delete_all_pages_undo_redo)*

## 5. Docs & quality gates

- [ ] 5.1 Document the changed behaviour in README.md: "New File" is now undoable; undoing an edit after "New File" no longer resurrects earlier pages.
- [x] 5.2 Run full `pytest`; ensure coverage numbers for touched files are same or better. *(Clean-data comparison vs baseline: no file worse; file_menu_mixins.py partial branches 23→22; total uncovered statements unchanged at 3. Note: `--cov-append` in addopts silently accumulates stale data — always `rm .coverage` before coverage comparisons.)*
- [x] 5.3 Run `black` on modified files; ensure `pylint` score is same or better with no new disables. *(black clean across the tree; pylint 9.53 → 9.54 for the touched modules; no new disables.)*
