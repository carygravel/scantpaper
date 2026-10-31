# Proposal

## Why

scantpaper can export a page's corrected text layer as hOCR, but it cannot read
one back. A user who rebuilds a session from the original images therefore
loses all OCR corrections, even though the corrections were exported. This
matters when an old session's images are unsuitable (for example, stored as
lossy JPEG) and the pages must be reimported from the source TIFFs.

## What Changes

- Add **File → Import hOCR…** to apply an hOCR file to the selected pages or
  all pages.
- Parse a multi-page hOCR file into one page per `ocr_page` element and map
  those pages to the target pages in page order.
- Reject the import, without changing any page, when the number of hOCR pages
  does not match the target page count, when a page box differs from the
  target page's pixel size by more than one pixel, or when the file contains
  no `ocr_page` elements.
- Accept a one-pixel difference between an hOCR page box and the target page
  dimensions, so a harmless rounding difference does not block an otherwise
  valid import.
- Show the actual validation reason in the error dialog instead of an empty
  message when an import is rejected.
- Replace only each target page's text layer. Page images and annotations are
  never changed.
- Treat an hOCR page with no text as an empty text layer, so a page that had no
  OCR round-trips as a page with no OCR.
- Record the whole import as one undoable action, run it in the background with
  progress and cancellation, and leave the document unchanged if it is
  cancelled or fails before completion.
- When saving selected pages as hOCR, emit exactly one `ocr_page` element per
  selected page, in page order, including pages with no text layer. Such a page
  contains an empty page box with the page's pixel dimensions.
- Keep the existing text-layer export for pages that do have OCR, so exporting
  and reimporting a page preserves its words, bounding boxes, confidence,
  baseline, text angle, and ids.

## Capabilities

### New Capabilities

- `hocr-text-layer`: importing and exporting page text layers as hOCR,
  including multi-page mapping, empty pages, geometry validation, and
  round-trip fidelity.

### Modified Capabilities

<!-- None. The existing multi-page-batch, cancellation, and progress specs
     already cover the new operation's cross-cutting behaviour. -->

## Impact

- `src/scantpaper/bboxtree.py`: parse multiple `ocr_page` elements while
  keeping empty page roots available for validation.
- `src/scantpaper/page.py`: export an empty page box for a page with no text
  layer.
- `src/scantpaper/docthread.py`: background batch import, validation, single
  undo snapshot, and atomic text-layer replacement.
- `src/scantpaper/savethread.py`: emit one hOCR page per selected page.
- `src/scantpaper/basedocument.py` and `src/scantpaper/app_window.py`: expose
  the import action and its callbacks.
- `src/scantpaper/app.ui` and a new import dialog: the user-facing entry point
  and page-range selection.
- Tests, translation template, `README.md`, and `changelog.md`.
- No new dependencies.
