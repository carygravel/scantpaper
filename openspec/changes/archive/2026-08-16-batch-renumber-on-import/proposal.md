## Why

Importing a large batch of pages (e.g. 250 TIFFs) is fast on the worker thread,
but `renumber()` runs once per imported page on the GUI thread
(`basedocument.py:280`), rewriting the number column for every row each time.
This is O(n^2) model writes on the main thread, so the GUI becomes progressively
unusable as the import grows. When pages are simply appended in order, the
numbers are already correct, so most of that renumbering is redundant work.

## What Changes

- **Skip `renumber()` on pure appends.** In `BaseDocument.add_page`
  (`basedocument.py:231`), when a page is appended at the end
  (`insert-after`/`replace` absent), its number is already correct and the
  preceding rows are unchanged, so `renumber()` is unnecessary. Only perform
  `renumber()` when a page is inserted in the middle or replaces an existing
  row, where positions actually shift.
- **Renumber once at the end of a multi-file import.** Add a single `renumber()`
  call in the import batch's finish path so that, in the unlikely event the user
  performs a concurrent action, numbers are guaranteed consecutive. This is a
  safety net rather than a per-page cost.

This is a pure performance refactor: the observable guarantee that page numbers
are always consecutive 1..n is unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. No spec-level behavior changes (page numbering behavior is unchanged; only
the internal timing of `renumber()` is optimized). This change opts out of specs
via `skip_specs: true`.

## Impact

- `scantpaper/basedocument.py` — `add_page` (`~:231`) and its `renumber()` call
  (`:280`); import finish path in `scantpaper/document.py`.
- Existing tests in `scantpaper/tests/test_basedocument.py` that assert page
  numbers after append/insert/replace; import tests in `scantpaper/tests/`.
- No new dependencies. No DB schema change.
