## 1. Core fix in hOCR export

- [ ] 1.1 Add container synthesis to `Bboxtree.to_hocr()` (bboxtree.py) so a
      flat `page > word` tree emits `ocr_par`/`ocr_line` wrappers, and verify
      `Bboxtree` unit tests in `test_75_bboxtree.py` reflect the new structure
- [ ] 1.2 Ensure synthesized line grouping uses each word's own bbox so emitted
      geometry is preserved, and verify with a focused unit test that the
      output hOCR contains `ocr_par` and `ocr_line` around the words
- [ ] 1.3 Update any existing string-equality assertions that the container
      change breaks, and verify the full `test_75_bboxtree.py` suite passes

## 2. Regression test through the real pipeline

- [ ] 2.1 Add a test that builds a flat tree (as `from_pdftotext` does), calls
      `to_hocr()`, and asserts the output contains `ocr_par`/`ocr_line`
      containers
- [ ] 2.2 Add a test that runs the real `ocrmypdf.api._hocr_to_ocr_pdf` on the
      exported hOCR with a small image-only origin PDF, and assert the output
      has a non-empty, extractable text layer (via pikepdf content inspection),
      reproducing the reported bug as a regression guard

## 3. Verification

- [ ] 3.1 Run `pytest` and confirm the full suite passes with no new coverage
      loss (uncovered/partial line counts unchanged or improved)
- [ ] 3.2 Run `ruff format`, `ruff check`, and `ty check --python venv .` and
      confirm they are clean
- [ ] 3.3 Update README.md if any user-visible change results, and confirm
      `openspec validate` passes for this change
