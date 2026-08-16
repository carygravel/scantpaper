## 1. Skip redundant renumbering on append

- [x] 1.1 In `BaseDocument.add_page` (`basedocument.py:231`), guard the
      `renumber()` call (`:280`) so that on a pure append (`i is None`) the
      global rewrite is skipped when `number == len(self.data)`; middle inserts
      and replaces continue to always call `renumber()`. Keep behavior for
      out-of-order appends correct by falling back to `renumber()` when the
      number does not already match its position.
- [x] 1.2 Add a unit test that an in-order append does not call `renumber()`
      (e.g. spy on `renumber` and assert it is not called when appending a page
      numbered equal to the new length).
- [x] 1.3 Confirm existing tests still pass, especially
      `test_add_page_renumbers` (out-of-order append → `1,2`),
      `test_add_page_insert_before` (insert → renumbered), and
      `test_delete_renumbers`.

## 2. Renumber once at end of a multi-file import

- [x] 2.1 In the multi-file import finish path
      (`_get_file_info_finished_callback2_multiple_files`, `document.py:87`),
      call `renumber()` once after the final `import_file` completes (in the
      existing end-of-batch `finished_callback`), as a safety net for any
      concurrent action during the batch.
- [x] 2.2 Add a unit test that importing multiple files triggers a single
      `renumber()` at the end of the batch (and not per file).
- [x] 2.3 Verify existing import tests (`test_document.py`,
      `test_file_menu_mixins.py`) still pass.

## 3. Verification & quality

- [x] 3.1 Run the full test suite:
      `python3 -m pytest scantpaper/tests -q -p no:cacheprovider` — all pass
      (baseline 1075 passed, 1 xfailed, 3 xpassed; now 1078 passed).
- [x] 3.2 Coverage: `python3 -m coverage json` shows uncovered lines (baseline 2)
      and partial branches (baseline 281) same or better (2 uncovered, 280
      partial, 99.11%).
- [x] 3.3 Format changed files with `black`.
- [x] 3.4 Run `pylint --persistent=no` on `basedocument.py` and changed test
      files — scores same or better (baselines: basedocument 9.15, document
      9.79, test_basedocument 8.69, test_document 9.13; all met).
