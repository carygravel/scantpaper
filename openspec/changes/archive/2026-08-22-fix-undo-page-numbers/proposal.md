# Proposal: fix-undo-page-numbers

## Why

After undo or redo, the page-number column can start at 0 instead of 1.
Undo/redo restore the worker-thread snapshot verbatim, exposing raw 0-based
database `row_id`s to a UI whose convention is 1-based positions enforced by
`renumber()`. This violates the `page-numbering` invariant that displayed
numbers are always consecutive 1..n, and flips the meaning of odd/even page
selection until the next edit. It was reproduced headlessly: scan three pages,
delete one, undo — the restored numbering is `[0, 1, 2]`.

## What Changes

- Convert page numbers to the 1-based UI convention at the snapshot boundary:
  `DocThread._get_snapshot()` returns `row_id + 1` as each row's page number,
  so both undo (`do_undo`) and redo (`do_redo`) restore correctly numbered
  rows through their single shared code path.
- Update existing tests that assert the buggy 0-based snapshot values, and add
  regression coverage: undo after deletion yields numbers exactly 1..n.
- Explicitly out of scope (candidates for a future change): renumbering stored
  `row_id`s themselves (DB-wide 1-based invariant), auditing `clone_pages`
  destination-coordinate semantics, and any session-file migration. Session
  files are unaffected; the database keeps its 0-based internal `row_id`.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `async-undo-redo`: pin down that the snapshot rows delivered by undo/redo
  carry 1-based page numbers consistent with the `page-numbering` invariant,
  rather than internal storage coordinates.

## Impact

- `scantpaper/docthread.py`: `_get_snapshot()` only (used solely by
  `do_undo` and `do_redo`).
- Tests: `test_101_document.py::test_db` snapshot assertions change from 0
  to 1; new undo-after-delete regression test.
- No frontend changes: `Document.undo()`/`unundo()` assign the snapshot
  verbatim, which becomes correct once the boundary converts.
- No schema, storage-format, or dependency changes.
