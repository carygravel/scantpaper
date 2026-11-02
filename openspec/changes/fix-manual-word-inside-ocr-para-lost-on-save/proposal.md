# Proposal

## Why

A word added manually in an area that is inside an OCR paragraph's bounding box
but outside any of its lines is stored correctly yet disappears from the saved
PDF. The hOCR exporter emits it as a bare `ocrx_word` directly under
`ocr_par`, and ocrmypdf's text-layer renderer only walks line-class children of
a paragraph, so the word is silently dropped. This now affects the hOCR-import
workflow directly: a user imports an old corrected text layer, adds a missed
word, and the new word is missing from the output even though the rest of the
imported text is searchable.

## What Changes

- Fix hOCR export so every word ends up inside an `ocr_line` that is itself
  inside an `ocr_par`, including a word that is a direct child of an existing
  paragraph.
- Preserve existing line structure and wrap only the bare words in synthetic
  lines; never nest a paragraph inside another paragraph.
- Keep the existing page/`carea`/`column` wrapping behaviour unchanged, so
  flat text layers and words added outside every paragraph still export as
  before.
- Apply the same fix to rotated words: a word under a paragraph that carries a
  `textangle` currently loses the angle on export, and the synthetic line will
  carry it instead.
- Add regression tests at both the hOCR-export boundary and the real
  ocrmypdf/`pdftotext` save boundary.
- Extend the `save-searchable-text-layer` capability contract to cover words
  added inside an existing paragraph's bounding box but outside its lines, and
  rotated words under a paragraph.

No data migration is needed: the fix is at export time, so existing sessions
and previously imported hOCR files save correctly without re-importing or
re-editing.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `save-searchable-text-layer`: the guarantee that every word is nested under
  `ocr_par`/`ocr_line` must also cover a word whose parent is an existing
  paragraph but which is not inside any of that paragraph's lines. The rotated
  text requirement must also cover such a word.

## Impact

- `src/scantpaper/bboxtree.py`: `_ensure_hocr_containers` and its line-grouping
  helpers.
- `src/scantpaper/tests/test_75_bboxtree.py`: unit regressions for a bare word
  under a paragraph and for a rotated bare word under a paragraph.
- `src/scantpaper/tests/test_savethread.py`: end-to-end regression asserting
  that a paragraph plus a bare word survives the real ocrmypdf and `pdftotext`
  path.
- `openspec/specs/save-searchable-text-layer/spec.md`: spec delta for the two
  modified requirements.
- No changes to the canvas editor, hOCR import format, PDF save pipeline,
  session schema, or dependencies.
