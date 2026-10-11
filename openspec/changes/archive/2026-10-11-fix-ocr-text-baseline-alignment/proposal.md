## Why

The canvas draws OCR text centered vertically in each word's bounding box. Tesseract hOCR reports word/line bboxes as ink unions — when a word has no descenders, the bbox bottom sits at the baseline; when it has descenders, the bbox extends below the baseline. Vertical centering of the rendered Pango ink box inside these ink-based bboxes causes the rendered text to be vertically misaligned relative to the scan's true baseline, producing incorrect y positioning in the GUI text layer display.

## What Changes

- Modify canvas rendering to **align text by baseline** instead of vertically centering it in the bbox.
- Parse and store additional hOCR typographic metrics (`x_ascenders`, `x_descenders`, `x_size`, `x_height` as needed) from hOCR, alongside the existing `baseline` data, so the renderer can compute a consistent baseline position.
- Update canvas Bbox/canvas drawing logic to compute the baseline position in scene coordinates (respecting baseline slope/offset from hOCR and any text rotation) and position the Pango layout so its baseline aligns with that target.

## Capabilities

### New Capabilities

None (behavior change to existing canvas rendering).

### Modified Capabilities

- `canvas-widget`: The canvas rendering SHALL position OCR text by aligning the rendered text's baseline to the bbox's baseline (from hOCR) rather than centering the ink box vertically. This applies to rotated text as well (with baseline taken into account). The change affects how text is drawn in the GUI (the on-screen overlay); it does not change how text is embedded in saved PDFs/DjVu where invisible text is used.

## Impact

- **src/scantpaper/canvas.py**: Bbox class (store baseline-related metrics), `_draw_bbox()` / text positioning logic to use baseline alignment instead of vertical centering. May need helper to resolve baseline y from hOCR baseline coefficients and bbox position.
- **src/scantpaper/bboxtree.py**: `HOCRParser` — capture `x_ascenders`, `x_descenders`, `x_size`, `x_height`, `x_fsize` from hOCR title attributes (Tesseract 5.x emits `x_size`, `x_ascenders`, `x_descenders`, etc. with `hocr_font_info=1`).
- **src/scantpaper/canvas.py / Bbox.to_hocr() / round-tripping**: ensure parsed baseline/metrics are preserved through scene graph and round-trip cleanly (no behavior change to saved hOCR semantics except preserving additional metrics if present).
- **Tests**: Update canvas rendering tests that assert text positioning/centering behavior to reflect baseline-aligned positioning. Update bboxtree tests to expect parsed baseline/font metrics where relevant.
