## 1. Worker-side handler

- [x] 1.1 Add `do_get_page()` method to `DocThread` in `docthread.py` — moves existing `get_page()` logic (SQLite query + `Page.from_bytes()`) into a handler that returns the `Page` object
- [x] 1.2 Remove synchronous `get_page()` method from `DocThread`

## 2. Test helper

- [x] 2.1 Create `get_page_sync(thread, **kwargs)` helper in a shared test utilities location (e.g., `scantpaper/tests/helpers.py` or `conftest.py`)
- [x] 2.2 Update `test_34_unpaper.py` — replace `thread.get_page()` calls with `get_page_sync()`
- [x] 2.3 Update `test_411_tesseract.py` — same replacement
- [x] 2.4 Update `test_211_tools.py` — same replacement
- [x] 2.5 Update `test_1601_import_djvu.py` — same replacement
- [x] 2.6 Update `test_1611_import_tiff.py` — same replacement
- [x] 2.7 Update `test_1622_import_multipage_pdf.py` — same replacement
- [x] 2.8 Update `test_1631_import_images.py` — same replacement
- [x] 2.9 Update `test_1111_save_pdf.py` — same replacement
- [x] 2.10 Update `test_121_save_djvu.py` — same replacement
- [x] 2.11 Update `test_151_save_text.py` — same replacement
- [x] 2.12 Update `test_371_user_defined.py` — same replacement
- [x] 2.13 Update `test_51_process_chain.py` — same replacement
- [x] 2.14 Update `test_print_operation.py` — same replacement (mock calls, no change needed)
- [x] 2.15 Update `test_docthread.py` — same replacement (mock/error tests, no change needed)
- [x] 2.16 Update any remaining test files that call `thread.get_page()`

## 3. Display image conversion

- [x] 3.1 Convert `_display_image()` in `session_mixins.py` to thumbnail-first: sync set thumbnail from `self.data[i][1]`, then async `send("get_page", ...)` with callback for full-res
- [x] 3.2 Move crop dialog update, text canvas, and annotation canvas creation into the async `finished_callback`
- [x] 3.3 Handle the case where `_display_image()` is called for a page that hasn't been loaded yet (pageid not in `self.data`)

## 4. Integration

- [x] 4.1 Update `undo()` and `redo()` finished callbacks in `document.py` (from Phase 1) to work with the new async `_display_image()` — ensure `self.select()` triggers the async display correctly
- [x] 4.2 Verify `_display_callback()` in `session_mixins.py` works with async `_display_image()`
- [x] 4.3 Verify `_page_selection_changed_callback` in `app_window.py` works with async `_display_image()`

## 5. Verification

- [x] 5.1 Run `pytest` and verify all tests pass
- [x] 5.2 Run `black` formatter
- [x] 5.3 Run `pylint` and ensure score is same or better
