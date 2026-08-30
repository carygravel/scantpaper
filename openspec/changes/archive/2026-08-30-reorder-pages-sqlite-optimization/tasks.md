# Reorder pages with a dedicated SQLite operation — Tasks

## 1. Worker-thread reorder operation

- [x] 1.1 Add a `reorder_pages` request type and `do_reorder_pages` handler in `scantpaper/docthread.py` that calls `_check_write_tid()` then `_take_snapshot()` exactly once, and verify the unit test for it in `scantpaper/tests/test_docthread.py` passes
- [x] 1.2 Implement the reorder logic (select ordered `page_order`, splice moved ids at `dest` honouring `how`, rewrite all row ids with one `executemany`) and verify it reorders a block move and preserves relative order
- [x] 1.3 Make `do_reorder_pages` return the moved pages' thumbnails + new positions and verify the response shape matches the clone response so the UI model can update

## 2. No-duplication guarantee

- [x] 2.1 Ensure `do_reorder_pages` never touches the `image` table and verify a test asserts the image row count is unchanged after a reorder

## 3. UI drag path

- [x] 3.1 In `drag_data_received_callback` (`scantpaper/basedocument.py`), compute moved ids + `dest`/`how` from `get_dest_row_at_pos` and send `reorder_pages` for the `ID_PAGE` branch, and verify a drag updates `self.data` with the page at its new position
- [x] 3.2 Add a suppress-delete flag set by the drop handler and honoured by `delete_selection` (basedocument.py:405) so the post-drop `drag-data-delete` does not also delete the moved page, and verify a drag does not delete the page
- [x] 3.3 Reselect the moved pages from the response after the reorder, and verify a multi-page drag leaves the moved pages selected

## 4. Undo / numbering semantics

- [x] 4.1 Verify a single undo after a reorder restores the original order (one snapshot → one undo step) via an `async-undo-redo`-style test
- [x] 4.2 Verify page numbers are consecutive 1..n after reordering, reusing the `page-numbering` reorder scenario

## 5. Regression checks

- [x] 5.1 Confirm the Edit-menu copy/paste path still uses `clone_pages` and its tests pass unchanged
- [x] 5.2 Run the full `pytest` suite and confirm no new failures and no new `pylint` warnings
- [x] 5.3 Format changed files with `black`