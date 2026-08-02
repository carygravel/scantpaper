## 1. Dependencies

- [x] 1.1 Add `pikepdf` to `dependencies` in `pyproject.toml`

## 2. Save-side implementation

- [x] 2.1 Add module-level `_remove_pdf_title(path)` helper in
      `scantpaper/savethread.py` that removes `/Title` from docinfo and
      `dc:title` from XMP metadata using pikepdf
      (`pdf.open_metadata()` context + `md.pop("dc:title", None)`) and
      re-saves with `preserve_pdfa=True, linearize=True`
- [x] 2.2 Call `_remove_pdf_title(filename)` from `do_save_pdf` after
      `_hocr_to_ocr_pdf` returns (line 193) and before `_append_pdf` (line 198),
      only when `"title" not in metadata`

## 3. Import-side implementation

- [x] 3.1 Add module-level `_is_placeholder_title(value)` helper in
      `scantpaper/document.py` that returns True when the value is a
      placeholder: `value.strip().strip("'").strip().lower() == "untitled"`
- [x] 3.2 Update `_extract_metadata` (`scantpaper/document.py:438`) to exclude
      a placeholder title from the returned metadata (checked on the unescaped
      value)

## 4. Tests

- [x] 4.1 Add save-side test in `scantpaper/tests/test_1111_save_pdf.py`: save
      a PDF with no title, open the output with pikepdf, assert no `/Title` in
      docinfo and no `dc:title` in XMP; assert `pdfinfo` reports no `Title:`
- [x] 4.2 Add save-side test: saving a PDF with a title retains exactly that
      title in docinfo and XMP
- [x] 4.3 Add import-side unit tests for `_extract_metadata`: title of
      `Untitled`, `'Untitled'`, and `UNTITLED` yields no title; real title
      `La Voz de Galicia` is preserved
- [x] 4.4 Extend `test_import_pdf_with_metadata`
      (`scantpaper/tests/test_1622_import_multipage_pdf.py:276`) with a
      placeholder-title PDF, asserting the imported session metadata has an
      empty title
- [x] 4.5 Integration: run a full save (no title) of a real document through
      the pipeline, re-import the output, and assert the session title is empty

## 5. Quality checks

- [x] 5.1 Run `pytest` and confirm all tests pass with coverage not lower than
      before
- [x] 5.2 Run `black` formatting on changed files
- [x] 5.3 Run `pylint` and confirm the score is not lower than before
