## Why

When a user manually adds text to a page's text layer (drawing a rectangle in
the picture layer and typing in the text layer), the text displays and is
persisted to session data correctly, but it silently disappears from the saved
PDF. Only the automatically OCR-recognised text survives. The manual word is
dropped because it is never wrapped in the `ocr_par` container that the PDF
text-layer renderer walks.

## What Changes

- Fix `_hocr_with_containers` in `src/scantpaper/bboxtree.py` so that any word
  or line that is not already nested under a paragraph is wrapped in a
  synthetic `para` (and, for bare words, `line`) container, **even when the
  tree already contains paragraphs** from automatic OCR. Currently the whole
  wrapping pass is skipped whenever *any* `para` is present.
- Add a regression test covering the mixed case: a tree containing OCR
  paragraphs **and** a manually added bare word, asserting that the exported
  hOCR nests the manual word inside an `ocr_par`/`ocr_line`.
- No change to user-facing behaviour other than restoring the already-visible
  manual text to the saved PDF. No new dependencies.

## Capabilities

### New Capabilities

- none

### Modified Capabilities

- `save-searchable-text-layer`: the requirement that the emitted hOCR includes
  the container levels the renderer walks currently only rescues pages with no
  paragraph structure at all. It must also guarantee that individually added
  words on an otherwise structured (OCR) page are nested under a paragraph, so
  they are not dropped on save.

## Impact

- `src/scantpaper/bboxtree.py`: `_hocr_with_containers` and its helpers.
- `src/scantpaper/tests/test_75_bboxtree.py`: new regression test.
- The PDF save path (`src/scantpaper/savethread.py`) and ocrmypdf's hOCR
  renderer are unchanged; the fix is at the hOCR-export boundary where the
  defect originates.
