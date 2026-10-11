## Tasks

- [x] 1. Parse hOCR font metrics in HOCRParser (bboxtree.py)
  - [ ] 1.1 Extract `x_ascenders`, `x_descenders`, `x_size`, `x_height`, `x_fsize` from span title attributes
  - [ ] 1.2 Store extracted metrics on parsed data dict (with keys matching existing style)
  - [ ] 1.3 Ensure existing `baseline` parsing remains intact

- [x] 2. Extend Bbox to store baseline/font metrics (canvas.py)
  - [ ] 2.1 Add fields to `Bbox.__init__` (e.g., `x_ascenders`, `x_descenders`, `x_size`, `x_height`, `x_fsize`)
  - [ ] 2.2 Store values from kwargs when constructing Bbox
  - [ ] 2.3 Preserve through copy/round-trip paths (ensure `to_hocr` emits baseline as before; optionally emit metrics if present)

- [x] 3. Update Bbox.to_hocr to preserve font metrics if present (canvas.py)
  - [ ] 3.1 Append `; x_ascenders ...`, `; x_descenders ...`, `; x_size ...`, etc. when present (matching Tesseract hOCR format)
  - [ ] 3.2 Maintain backward compatibility when metrics missing

- [x] 4. Implement baseline-aligned text rendering (canvas.py _draw_bbox)
  - [ ] 4.1 Compute target baseline y in scene coordinates from bbox baseline coefficients
  - [ ] 4.2 For non-rotated text, align Pango layout baseline to target baseline instead of centering vertically
  - [ ] 4.3 Handle text rotation (`textangle`) when computing baseline alignment
  - [ ] 4.4 Fallback to current vertical centering if baseline data is missing or malformed

- [x] 5. Update tests
  - [ ] 5.1 Update bboxtree tests to handle parsed font metrics (ensure round-trip works)
  - [ ] 5.2 Update canvas rendering tests that assume vertical centering to reflect baseline alignment where appropriate
  - [ ] 5.3 Add regression test with known descender/non-descender case verifying baseline alignment

- [x] 6. Verify with existing tests
  - [ ] 6.1 Run ruff format/check
  - [ ] 6.2 Run ty type checking
  - [ ] 6.3 Run pytest to ensure no regressions
