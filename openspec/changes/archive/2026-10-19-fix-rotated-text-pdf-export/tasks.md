## 1. Transform-level regression tests

- [x] 1.1 In `src/scantpaper/tests/test_75_bboxtree.py`, add a test that a
  bare word with `textangle 90` exports inside an `ocr_line` carrying
  `textangle 90` (and no `textangle` on the word).
- [x] 1.2 Add a test that a line containing a 0-degree word and a 90-degree
  word is split into two `ocr_line` elements, each with the correct angle,
  bbox, and word.
- [x] 1.3 Add a test that an ancestor rotation (page/carea/para) lands on the
  line exactly once and is absent from the ancestors and words.
- [x] 1.4 Add a test that a word whose own angle matches its line's angle does
  not produce an extra line or a doubled angle.
- [x] 1.5 Confirm the new tests fail against the current export, then leave
  them failing for the implementation task.

## 2. Export normalisation

- [x] 2.1 In `src/scantpaper/bboxtree.py`, add the line-like type set and a
  recursive normalisation pass that computes each word's effective angle,
  writes it to the enclosing line-like node, clears angles from words and
  non-line ancestors, and splits mixed-angle nodes into one line per angle
  (union bbox; original `id`/`baseline` kept on the group matching the
  original effective angle).
- [x] 2.2 Call the pass from `_hocr_with_containers()` after
  `_ensure_hocr_containers()` and before `_flatten_nested()`.
- [x] 2.3 Update the existing hOCR export expectations in
  `src/scantpaper/tests/test_75_bboxtree.py` to the line-level angle output.
- [x] 2.4 Run `pytest src/scantpaper/tests/test_75_bboxtree.py` and fix any
  regressions.

## 3. Saved-PDF integration test

- [x] 3.1 In `src/scantpaper/tests/test_1111_save_pdf.py`, add a test that
  stores a text layer with one horizontal and one vertical word, saves a PDF,
  and asserts the decoded page content stream contains a rotated `Tm` matrix
  and that `pdftotext` still extracts both words.
- [x] 3.2 Add a horizontal-only control assertion that no rotated `Tm`
  appears for an unrotated text layer.
- [x] 3.3 Run the new test; confirm it fails before task 2 and passes after
  it.

## 4. OCRmyPDF floor

- [x] 4.1 Raise the dependency in `pyproject.toml` to
  `ocrmypdf>=16.10.0`.
- [x] 4.2 Raise both `ocrmypdf (>= 15.4.3)` entries in
  `.github/workflows/deb.yml` to `>= 16.10.0`.
- [x] 4.3 Check the openSUSE/Fedora packaging specs still satisfy the new
  floor and update them if needed (openSUSE builds 16.11.1 today).

## 5. Documentation

- [x] 5.1 Update the text-layer section of `README.md` to state that rotated
  slices are embedded at their angle in saved PDFs and that re-imported PDFs
  cannot recover rotation.
- [x] 5.2 Add a `changelog.md` entry describing the fix.

## 6. Quality gates

- [x] 6.1 Run `ruff format` and `ruff check .` clean.
- [x] 6.2 Run `ty check .` clean.
- [x] 6.3 Run the full `pytest` suite and keep coverage at or above the
  configured threshold, with no new uncovered or partially covered lines
  outside `if TYPE_CHECKING:` imports.
