## Why

When a user imports a PDF page and saves it, the resulting PDF has no
searchable text layer: `pdftotext` extracts nothing and the embedded `/OCR-*`
form XObject is empty. The page image is fine, but any copy/paste or search in
the saved PDF finds nothing. This makes imported-and-resaved documents useless
for the app's core purpose of producing OCR'd PDFs.

## What Changes

- Ensure every page that has a text layer emits an hOCR structure that the PDF
  renderer (ocrmypdf) actually renders, i.e. an `ocr_par`/`ocr_line` container
  hierarchy rather than a flat `ocr_page > ocrx_word` list.
- Make the PDF import path (`from_pdftotext`) build `line` (and enclosing
  `para`) nodes so imported pages carry a non-degenerate text layer from the
  start.
- Make `Bboxtree.to_hocr()` synthesize `ocr_par`/`ocr_line` containers when the
  tree lacks them, so a degenerate tree can never silently produce an empty
  text layer again.
- Add a regression test that runs the real `_hocr_to_ocr_pdf` pipeline on a
  page's exported hOCR and asserts the output contains a non-empty, extractable
  text layer. (Existing tests only inspect the hOCR string, which is why this
  slipped through.)

## Capabilities

### New Capabilities
- `save-searchable-text-layer`: the saved PDF contains a searchable text layer
  for every page that has one, matching the geometry of the text layer being
  saved.

### Modified Capabilities
- `ocr-recognition`: OCR-recognized pages already carry `para`/`line` structure;
  this capability's requirements do not change. No delta.

## Impact

- `src/scantpaper/bboxtree.py`: `_pdftotext2boxes`, `to_hocr`, and the
  hOCR/import box construction so containers are always present.
- `src/scantpaper/canvas.py`: `Canvas.hocr()` emits `ocrx_word`/`ocr_par`/
  `ocr_line` classes consistent with the save pipeline.
- `src/scantpaper/tests`: new regression test driving the real
  `_hocr_to_ocr_pdf` path.
- No new dependencies; relies on the already-pinned ocrmypdf (16.13) renderer
  behavior.
