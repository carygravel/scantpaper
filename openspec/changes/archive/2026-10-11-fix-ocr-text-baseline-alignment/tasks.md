## Tasks

- [x] 1. Parse hOCR font metrics in HOCRParser (bboxtree.py)
  - [x] 1.1 Extract `x_ascenders`, `x_descenders`, `x_size`, `x_height`, `x_fsize` from span title attributes
  - [x] 1.2 Store extracted metrics on parsed data dict (with keys matching existing style)
  - [x] 1.3 Ensure existing `baseline` parsing remains intact

- [x] 2. Extend Bbox to store baseline/font metrics (canvas.py)
  - [x] 2.1 Add fields to `Bbox.__init__` (e.g., `x_ascenders`, `x_descenders`, `x_size`, `x_height`, `x_fsize`)
  - [x] 2.2 Store values from kwargs when constructing Bbox
  - [x] 2.3 Preserve through copy/round-trip paths (ensure `to_hocr` emits baseline as before; optionally emit metrics if present)

- [x] 3. Update Bbox.to_hocr to preserve font metrics if present (canvas.py)
  - [x] 3.1 Append `; x_ascenders ...`, `; x_descenders ...`, `; x_size ...`, etc. when present (matching Tesseract hOCR format)
  - [x] 3.2 Maintain backward compatibility when metrics missing

- [x] 4. Implement baseline-aligned text rendering (canvas.py _draw_bbox)
  - [x] 4.1 Compute target baseline y in scene coordinates from bbox baseline coefficients
  - [x] 4.2 For non-rotated text, align Pango layout baseline to target baseline instead of centering vertically
  - [x] 4.3 Handle text rotation (`textangle`) when computing baseline alignment
  - [x] 4.4 Fallback to current vertical centering if baseline data is missing or malformed

- [x] 5. Update tests
  - [x] 5.1 Update bboxtree tests to handle parsed font metrics (ensure round-trip works)
  - [x] 5.2 Update canvas rendering tests that assume vertical centering to reflect baseline alignment where appropriate
  - [x] 5.3 Add regression test with known descender/non-descender case verifying baseline alignment

- [x] 6. Verify with existing tests
  - [x] 6.1 Run ruff format/check
  - [x] 6.2 Run ty type checking
  - [x] 6.3 Run pytest to ensure no regressions
