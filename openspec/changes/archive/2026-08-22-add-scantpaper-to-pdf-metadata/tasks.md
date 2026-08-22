## 1. Implementation

- [x] 1.1 Generalise `_remove_pdf_title` in `scantpaper/savethread.py` into a
  metadata fixup pass that (a) removes the placeholder title when no user
  title was supplied and (b) reads the existing `/Creator`, prepends
  `scantpaper v<version> / `, and writes the result to `/Creator` and XMP
  `xmp:CreatorTool` via `open_metadata(set_pikepdf_as_editor=False)`,
  saving with `preserve_pdfa=True, linearize=True`
- [x] 1.2 Call the fixup pass unconditionally after successful embed,
  passing whether placeholder-title removal is needed
  (`"title" not in metadata`)
- [x] 1.3 Wrap the fixup call so a failure logs a warning and leaves a
  usable unbranded PDF instead of failing the save

## 2. Tests

- [x] 2.1 Update existing `test_savethread.py` patches of
  `_remove_pdf_title` to the renamed/merged function; assert it is called
  on every successful embed, with title removal only when no user title
- [x] 2.2 Add integration assertions to `test_1111_save_pdf.py`: saved PDF's
  `/Creator` starts with `scantpaper v` and retains the OCR toolchain
  suffix; XMP `xmp:CreatorTool` equals `/Creator`; producer fields unchanged
- [x] 2.3 Assert branding also applies when a user title was provided, and
  that PDF/A identification is preserved

## 3. Wrap-up

- [x] 3.1 Document the new Creator metadata behaviour in README.md
- [x] 3.2 Run `pytest`, `black`, and `pylint`; confirm coverage of uncovered
  lines is unchanged or better
