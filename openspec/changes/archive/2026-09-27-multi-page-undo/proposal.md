## Why

Multi-page operations (rotate, crop, and any op that replaces pages) are
dispatched as a loop of single-page operations, so each page modification
records its own undo step. Undoing an operation applied to several pages
therefore requires one Undo press per page, and each press reverts only a
single page, instead of undoing the whole operation in one step.

## What Changes

- Multi-page operations (rotate 90/180/270, crop selection, and other
  page-replacing operations applied to a page range or selection) become a
  single atomic undo step: one Undo reverts the entire batch.
- Add a batch mode to the worker thread so that a run of page operations
  within a batch records one snapshot/action instead of one per page.
- Existing single-page operations keep their current behaviour unchanged.

## Capabilities

### New Capabilities

- `multi-page-batch-operations`: operations applied to several pages are
  recorded as one undoable action and can be reverted together.

### Modified Capabilities

- `async-undo-redo`: extend undo/redo semantics so that a batch of page
  operations (multi-page rotate, crop, etc.) is undone and redone as a single
  atomic step rather than one step per page.

## Impact

- `src/scantpaper/docthread.py`: batch mode on the worker thread (a gate
  around `_take_snapshot`) and `begin_batch` / `end_batch` thread requests.
- `src/scantpaper/document.py` / `src/scantpaper/basedocument.py`: expose a
  batch API (e.g. `begin_undo_batch()` / `end_undo_batch()`) so callers can
  wrap a multi-page loop.
- `src/scantpaper/tools_menu_mixins.py`: wrap `_rotate` and `crop_selection`
  page loops in the batch API.
- Tests: extend `test_docthread.py` and `test_tool_menu_mixins.py` to cover
  batching; verify undo/redo of a multi-page batch reverts all pages.
