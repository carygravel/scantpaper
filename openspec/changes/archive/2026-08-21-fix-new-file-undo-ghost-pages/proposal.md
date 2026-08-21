## Why

Issue #74: after scanning page A, saving, choosing "New File", scanning page B and
editing it, a single Undo resurrects page A in addition to reverting the edit to B.
Root cause: `FileMenuMixins.new_()` clears only the frontend GTK list
(`slist.data = []`) and never informs `DocThread`, whose SQLite snapshot chain still
contains page A. The next operation (`add_page` for page B) snapshots that stale
state forward, so page A silently rejoins every subsequent undo step. Deleting
pages via the Edit menu does not exhibit the bug because it routes through
`DocThread.do_delete_pages()`, which keeps frontend and database in sync.

## What Changes

- Route the "New File" action through `DocThread` as an ordinary (undoable)
  delete-all-pages operation instead of clearing only the frontend list.
- Reuse the existing `delete_pages` message path (`DocThread.do_delete_pages` +
  `Document.delete_selection()` callback pattern) so the SQLite snapshot chain and
  the thumbnail list can no longer diverge.
- Make "New File" a no-op (no thread request, no snapshot) when the document is
  already empty.
- User-visible consequence: Undo immediately after "New File" now restores the
  pages that were cleared (and Redo re-clears them); Undo after "New File" plus
  further edits affects only those later edits, never resurrecting pre-clear
  pages mid-history.

## Capabilities

### New Capabilities
- `new-file-reset`: behaviour of the "New File" action - consistent, undoable
  clearing of the document across the frontend list and the `DocThread` snapshot
  chain.

### Modified Capabilities

(none - `async-undo-redo` dispatch mechanics are unchanged)

## Impact

- `scantpaper/file_menu_mixins.py` - `new_()` rewritten to dispatch deletion via
  the document/thread instead of directly assigning `slist.data`.
- `scantpaper/basedocument.py` - small addition alongside `delete_selection()`
  for deleting every page (or reuse of the same machinery).
- Tests: `test_file_menu_mixins.py`, plus a regression test reproducing the
  issue #74 sequence (scan A, new file, scan B, edit, undo) at the
  `DocThread`/`Document` level (`test_101_document.py` / `test_docthread.py`).
- `README.md` - document the changed Undo behaviour after "New File".
- No dependency changes; no database schema changes.
