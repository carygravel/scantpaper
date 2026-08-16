## 1. In-memory OCR input (D)

- [x] 1.1 In `do_tesseract` (docthread.py:1295-1306), replace the temp-PNG `page.image_object.save(file.name)` + `api.ProcessPages(output, file.name)` + hocr file read/unlink block with: convert `page.image_object` to 8-bit `"L"`, then `api.SetImageBytes(image.tobytes(), image.width, image.height, 1, image.width)`, `api.Recognize()`, `hocr = api.GetHOCRText(0)`; keep the `tessedit_create_hocr`/`hocr_font_info` `SetVariable` calls and the `page.import_hocr(hocr)` / `ocr_flag` / `ocr_time` updates; remove the `output = "image_out"` and `pathlib.Path` hocr read.
- [x] 1.2 Add a unit test asserting the tesseract API receives the page's in-memory pixels: mock `PyTessBaseAPI` and assert `SetImageBytes` is called with the `"L"`-mode bytes, `width`, `height`, `bytes_per_pixel=1`, `bytes_per_line=width`, followed by `Recognize()`, and that `GetHOCRText(0)` output is passed to `page.import_hocr`.
- [x] 1.3 Update `test_do_tesseract_path_fallback` and `test_do_tesseract_path_fallback_symlink`: remove the `ProcessPages` and `pathlib.Path` mocks; set up `SetImageBytes`/`Recognize`/`GetHOCRText` on the mock API and keep the tessdata-path assertions.

## 2. Reuse stored image on OCR (E)

- [x] 2.1 Add a `_reuse_image_thumb(image_id)` helper on `DocThread`: `SELECT thumb FROM image WHERE id = ?`, decode via `_bytes_to_pixbuf`, raise `ValueError` when the image id does not exist.
- [x] 2.2 Add a `reuse_image=False` keyword to `replace_page` (docthread.py:399); when true use `page.image_id` + `self._reuse_image_thumb(page.image_id)` instead of `_insert_image(page, if_different_from=...)`, keeping the snapshot, `_insert_page`, `page_order` update, commit and `(position, thumb, initial_page_id)` return unchanged.
- [x] 2.3 In `do_tesseract`, call `self.replace_page(page, page.id, reuse_image=True)`.
- [x] 2.4 Add unit tests for the reuse path: `replace_page(page, id, reuse_image=True)` returns the same `image_id`, does not call `_insert_image`, and decodes the existing thumbnail; the default `reuse_image=False` path still calls `_insert_image` (existing behavior unchanged).
- [x] 2.5 Update `test_do_tesseract_path_fallback_not_found`: remove the `pathlib.Path` mock and mock `_bytes_to_pixbuf` (or `_reuse_image_thumb`) so the reuse path completes after the tessdata error.
- [x] 2.6 Add a test that OCR text-layer changes are undoable/redoable: after `do_tesseract`, `undo` restores the pre-OCR text layer and `redo` restores the recognized text, with the stored image id/bytes unchanged throughout.

## 3. Verification & quality

- [x] 3.1 Confirm the real-OCR test `test_411_tesseract.py::test_tesseract_in_thread` still recognizes "The quick brown fox" (quality equivalence); extend it to assert the page's `image_id` is unchanged after OCR.
- [x] 3.2 Run the full test suite: `python3 -m pytest scantpaper/tests -q -p no:cacheprovider` — all pass (baseline 1071).
- [x] 3.3 Coverage: `python3 -m coverage json` shows uncovered lines (baseline 2) and partial branches (baseline 281) same or better.
- [x] 3.4 Format changed files with `black`.
- [x] 3.5 Run `pylint --persistent=no` on `docthread.py` and changed test files — scores same or better (docthread baseline 9.60, test_docthread baseline 8.71).
- [x] 3.6 Update README.md if the change is user-visible (faster OCR).
