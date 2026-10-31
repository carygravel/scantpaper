# Tasks

## 1. hOCR parsing and export

- [x] 1.1 Add `Bboxtree.from_hocr_pages()` returning one tree per `ocr_page`
  root, including a page root with no children, and keep `from_hocr()` on its
  existing single-page first-root behaviour. Verify with unit tests for one
  page, several pages, and an empty page.
- [x] 1.2 Make `Page.export_hocr()` emit a single page box at the page's pixel
  size when the page has no text layer. Verify with unit tests for a page with
  text and a page with no text.
- [x] 1.3 Update `do_save_hocr()` so a selected page with no text layer
  contributes an empty `ocr_page` instead of disappearing. Verify with tests
  for a mixed selection, an all-empty selection, and a single page; assert
  exactly one header/body and one `ocr_page` per selected page.
- [x] 1.4 Add a round-trip test using an hOCR fixture with paragraphs,
  baselines, text angles, confidence values, and ids. Assert that importing
  and re-exporting the page is byte-identical and that the word set and
  boxes are unchanged.

## 2. Background import worker

- [x] 2.1 Add a `DocThread` import request that reads the file, parses all
  `ocr_page` roots, and validates the page count and every page box against
  the target pages before any write. Verify with tests for fewer pages, more
  pages, no pages, a geometry mismatch, and an unreadable or malformed file;
  assert no page's text layer changes on each failure.
- [x] 2.2 Apply the validated text layers in one snapshot and one transaction,
  passing `None` for an empty hOCR page and the parsed JSON otherwise. Verify
  with tests that the image id and bytes, annotations, resolution, and page
  order are unchanged, and that an empty hOCR page clears the target text
  layer.
- [x] 2.3 Roll back the write phase if it is cancelled or raises, and report
  the request as cancelled or failed. Verify with a test that cancels after
  validation and asserts that no target page changed.
- [x] 2.4 Expose the import through `BaseDocument` with the queued, started,
  running, finished, cancelled, and error callbacks used by the other tools.
  Verify with tests for the callback flow, one undo step for several pages,
  undo restoring every page, and redo reapplying every page.

## 3. Menu, dialog, and user documentation

- [x] 3.1 Add **File → Import hOCR…** to the menu and action map. Enable it
  whenever the document has at least one page, independently of the
  selection. Verify with tests for the action's sensitivity with pages and
  with an empty document.
- [x] 3.2 Add an import dialog with a read-only path entry, a Browse button,
  the existing page-range frame, and OK/Cancel actions. Verify with tests that
  the selected/all value is read and that the dialog rejects an empty path.
- [x] 3.3 Wire the dialog to the worker with progress and cancellation, and
  remember the chosen directory and page range. Verify with tests for the
  queued/running/finished/error callbacks and for a cancelled import leaving
  the document unchanged.
- [x] 3.4 Document the workflow in `README.md`: export hOCR from the old
  session, rebuild the session from the original images in the same page
  order, import the hOCR, then save. Document that the import is text-layer
  only and that annotations are not transferred. Verify the documented steps
  against the shipped UI labels.
- [x] 3.5 Add the user-visible change to `changelog.md` and regenerate the
  translation template with
  `PYTHONPATH=src python3 dev/generate_pot.py`. Verify with
  `PYTHONPATH=src python3 dev/check_po.py` and confirm every new string is
  marked translatable.

## 4. Integration verification

- [x] 4.1 Add an end-to-end test: create a session with one page that has text
  and one page without text, save both as hOCR, rebuild a session from the
  same images, import the file, and assert the text page and the empty page
  match. Save the rebuilt session as a PDF and verify the text page remains
  searchable.
- [x] 4.2 Run `ruff format`, `ruff check`, `ty check .`, and `pytest`; confirm
  the coverage threshold passes and that no newly uncovered or partially
  covered lines were introduced outside type-only imports.

## 5. Follow-up: real-world hOCR tolerance and error reporting

- [x] 5.1 Allow a one-pixel difference in width and height when validating an
  hOCR page box against its target page, while keeping the origin at `0 0`.
  Verify with tests that a one-pixel height difference imports and that a
  difference of more than one pixel is rejected.
- [x] 5.2 Pass the hOCR validation reason as the error response status so the
  error dialog shows the page count, dimensions, or parse failure instead of
  an empty message. Verify with a test that the error response carries the
  reason and that the dialog receives it.
- [x] 5.3 Update `changelog.md` to mention the one-pixel tolerance and the
  visible hOCR import error message. Verify the entry describes both changes.

## 6. Verification

- [x] 6.1 Run `ruff format`, `ruff check`, `ty check .`, and `pytest`; confirm
  the coverage threshold passes and that no newly uncovered or partially
  covered lines were introduced outside type-only imports.

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Verify the archived specs and change status.
