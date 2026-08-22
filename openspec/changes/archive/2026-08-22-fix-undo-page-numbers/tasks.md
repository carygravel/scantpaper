## 1. Regression tests first

- [x] 1.1 In `scantpaper/tests/test_101_document.py`, add a regression test:
  build a thread, add three pages, delete the first via
  `do_delete_pages(page_ids=...)`, run `do_undo`, and assert the snapshot's
  page numbers are exactly `[1, 2, 3]`; run `do_redo` and assert the
  remaining numbers are `[1, 2]`
- [x] 1.2 Confirm the new test fails against current code (snapshot starts at 0)

## 2. Boundary conversion

- [x] 2.1 In `scantpaper/docthread.py`, change `_get_snapshot()` to return
  `row_id + 1` as each row's page number (element 0), leaving thumbnail and
  `initial_page_id` untouched

## 3. Contract updates

- [x] 3.1 Update the undo/redo assertions in
  `scantpaper/tests/test_101_document.py::test_db` from expecting `0` to
  expecting position-consistent numbering (`1`)
- [x] 3.2 Run the full test suite (`pytest`) and fix any other assertions that
  encoded raw 0-based snapshot numbering

## 4. Verification

- [x] 4.1 Verify the reproduction from exploration now reports "no bug":
  scan three pages, delete one, undo — restored numbers are `1, 2, 3`
- [x] 4.2 Check coverage numbers are unchanged or better; run `black`;
  confirm `pylint` score is not degraded
