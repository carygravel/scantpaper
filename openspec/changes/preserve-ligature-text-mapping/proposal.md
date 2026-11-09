# Proposal

## Why

On Ubuntu 26.04, which ships Ghostscript 10.06, a saved PDF can lose words
that contain a typographic ligature. OCRmyPDF's text-layer renderer shapes the
invisible text, so `ff` becomes one glyph with a multi-character `ToUnicode`
mapping. Ghostscript 10.06 drops those multi-character mappings during the
PDF/A conversion, leaving the character with no Unicode value. `pdftotext`
then omits the whole word, so a PDF that should be searchable is not. Later
Ghostscript releases keep the mapping, so the same document is searchable on
every other supported series.

## What Changes

- Render the OCR text layer without ligature substitutions while OCRmyPDF
  grafts it onto the page, so every character keeps its own Unicode mapping.
- Load the optional fpdf2 renderer once when the save module is imported,
  rather than on first use, so a later import cannot observe a patched
  `pathlib.Path`.
- Keep any shaping features the caller specifies explicitly, and leave the
  save untouched on OCRmyPDF releases that do not use the fpdf2 renderer.
- Document the behaviour in the changelog.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `save-searchable-text-layer`: the saved text layer SHALL keep per-character
  Unicode mappings even when the PDF/A converter drops multi-character
  mappings, so a word containing a ligature remains searchable.

## Impact

- `src/scantpaper/savethread.py`: a ligature-disabling context manager around
  the OCRmyPDF hOCR-to-PDF call, and the eager fpdf2 load.
- `src/scantpaper/tests/test_savethread.py`: unit coverage for disabling
  ligatures, explicit features, a renderer that is absent, and the loader.
- `openspec/specs/save-searchable-text-layer/spec.md`: spec delta for
  per-character Unicode mappings.
- `changelog.md`: note that ligature words stay searchable on 26.04.
- No change to the stored text layer, the emitted hOCR, the visible page
  rendering (the text layer is invisible), or dependencies.
