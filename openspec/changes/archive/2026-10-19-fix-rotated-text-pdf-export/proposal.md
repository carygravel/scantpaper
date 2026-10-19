## Why

A text slice rotated in the layer editor is drawn rotated on the canvas but
saved PDFs render it horizontally, often with an oversized font that spills
down the page. The text angle is written on the word in the exported hOCR,
while OCRmyPDF only reads `textangle` from the enclosing line. The existing
"rotation survives saving" requirement is therefore not met, and the same
fault affects manually added words nested inside an unrotated OCR line.

## What Changes

- Normalise text angles during hOCR export: compute each word's effective
  angle (its own angle plus every ancestor's) and write that angle to the
  `ocr_line` that OCRmyPDF reads.
- Give synthetic lines, created for words that have no line container, the
  angle of their words instead of defaulting to horizontal.
- Split a line whose words have different effective angles into one line per
  angle, so a manually added vertical word inside an existing horizontal OCR
  line is not forced upright.
- Leave the stored layer format unchanged: `textangle` stays on the slice in
  the page's text-layer JSON, so the editor, undo/redo and copy/paste keep
  working as they do now.
- Raise the OCRmyPDF minimum to the first release that honours the hOCR
  `textangle` attribute (`>=16.10.0`). The PPA already ships 16.13.0 for jammy
  and noble, so both supported Ubuntu releases can satisfy the new floor.
- Add regression coverage at two levels: hOCR transform tests for angle
  propagation and line splitting, and a saved-PDF integration test that
  checks the text is actually rotated. Document the behaviour and the
  dependency floor.

Out of scope: rotation-aware PDF re-import. The current import path uses
`pdftotext -bbox`, which does not expose text direction; re-imported rotated
text will remain horizontal until a separate change replaces or augments that
extractor. This change also does not attempt to work around the separate
OCRmyPDF 17.10 issue where rotated word lengths are squeezed to the short side
of their AABB.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `save-searchable-text-layer`: the saved PDF must render each slice at its
  effective text angle, including manually rotated slices, slices nested
  under a differently rotated ancestor, and mixed-angle lines.

## Impact

- `src/scantpaper/bboxtree.py`: hOCR export normalisation and line splitting.
- `src/scantpaper/tests/test_75_bboxtree.py`: transform-level regression tests.
- `src/scantpaper/tests/test_1111_save_pdf.py`: saved-PDF rotation test.
- `pyproject.toml` and `.github/workflows/deb.yml`: OCRmyPDF floor
  `>=16.10.0`.
- `README.md` and `changelog.md`: user-visible behaviour and dependency note.
- No database schema change and no change to the layer JSON stored in
  SQLite.
