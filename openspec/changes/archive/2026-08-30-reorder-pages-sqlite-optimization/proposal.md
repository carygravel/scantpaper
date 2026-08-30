# Reorder pages with a dedicated SQLite operation

## Why

Dragging a page in a large document is noticeably slower than gscan2pdf. Today a
drag is implemented as a **clone + delete**: the worker thread snapshots the whole
document, physically duplicates the dragged page's image blobs, shifts all
`page_order` row ids, then deletes the originals in a second snapshot-and-shift
transaction. That is roughly five O(pages) passes over `page_order` plus an image
copy per drag, which is why large documents crawl. Users report it as a real
problem when reordering frequently in big scans.

## What Changes

- Introduce a dedicated `reorder_pages` worker operation that reorders
  `page_order` rows in place.
- Replace the drag-and-drop path's clone+delete with this single reorder
  operation.
- Reordering SHALL take exactly one undo snapshot (one undo step), matching the
  current undo model.
- Reordering SHALL NOT duplicate stored image data; pages keep their existing
  `image_id`, so no blobs are copied.
- Page numbers SHALL remain consecutive 1..n after reorder, as today.
- No API or storage-format changes; sessions remain compatible.

## Capabilities

### New Capabilities
- `page-reordering`: The dedicated drag-and-drop page reorder operation, its
  single-snapshot undo behaviour, and its guarantee that reordering does not
  duplicate stored image data.

### Modified Capabilities
<!-- No existing spec-level behaviour changes: numbering stays consecutive, undo
     remains a single step, and image storage format is untouched. -->
- None.

## Impact

- `scantpaper/docthread.py`: new `do_reorder_pages` handler on the worker thread;
  `_shift_row_ids` / delete renumbering touched or reused.
- `scantpaper/basedocument.py`: `drag_data_received_callback` reorder path calls
  `send("reorder_pages", ...)` instead of `clone_pages` + `delete_selection`.
- `scantpaper/basedocument.py`: `paste_selection` retains clone behaviour for
  genuine copy/paste; only the drag-reorder path changes.
- Tests in `scantpaper/tests/test_docthread.py` and `test_basedocument.py`
  updated; new tests for reorder semantics (no duplication, single undo).
- No new dependencies.