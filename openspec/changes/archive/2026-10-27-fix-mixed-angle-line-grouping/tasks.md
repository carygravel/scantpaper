# Tasks

## 1. Grouping fix and unit coverage

- [x] 1.1 In `src/scantpaper/bboxtree.py`, change `_group_words_into_lines`
  so a candidate joins the current line only when the vertical distance
  between centres is within `min(previous height, candidate height) * 0.6`
  instead of the global maximum height. Verify with a unit test in
  `src/scantpaper/tests/test_75_bboxtree.py` that a flat layer of several
  upright rows plus one taller rotated word exports to one synthetic line
  per upright row.
- [x] 1.2 Add grouping unit tests that equal-height words on one row still
  share a single line and that spaced rotated words each become their own
  line carrying the word's angle. Verify the exported `ocr_line` count,
  bounding boxes, and `textangle` values.
- [x] 1.3 Add a grouping unit test where upright words on one row have
  noticeably different heights, and verify they no longer collapse into a
  single line whose box spans the larger word.

## 2. Save-level coverage and documentation

- [x] 2.1 Add a save test in `src/scantpaper/tests/test_1111_save_pdf.py`
  for a flat text layer mixing upright rows with tall rotated words. Save
  to PDF and verify with `pdftotext -bbox` that each upright word's reported
  height stays within a small multiple of its source bounding box (not the
  rotated word's), and that the rotated word is still rendered rotated.
- [x] 2.2 Update the text-layer section of `README.md` to state that
  upright and rotated slices can be mixed on one page and each word is
  saved at its own size and angle. Verify the wording matches the shipped
  behaviour.

## 3. Integration verification

- [x] 3.1 Run `pytest`, `ruff format --check`, `ruff check`, and `ty check .`
  and verify all pass with no new uncovered or partially covered lines.

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
