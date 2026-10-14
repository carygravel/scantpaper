## 1. Regression test first (TDD)

- [x] 1.1 Add a test in `src/scantpaper/tests/test_75_bboxtree.py` that builds a
      text-layer tree containing OCR paragraphs **and** a manually added bare
      word nested under the page (depth 1), then asserts that
      `Bboxtree.to_hocr()` nests that word inside an `ocr_par`/`ocr_line`.
- [x] 1.2 Add a second test for a manually added word nested under a `carea`
      (and a bare `line` with no `para` ancestor), asserting the emitted hOCR
      wraps it in a `para`. Run `pytest src/scantpaper/tests/test_75_bboxtree.py`
      and confirm the new tests fail against the current code.

## 2. Fix the export

- [x] 2.1 Rewrite `_hocr_with_containers` in `src/scantpaper/bboxtree.py` so the
      synthetic `para`/`line` wrapping runs for any word/line not already under
      a `para`, even when the tree already contains paragraphs, reusing the
      existing `_ensure_hocr_containers`/`_group_words_into_lines` helpers.
- [x] 2.2 Keep the existing flat-tree test (`test_to_hocr_flat_tree_wrapped_in_containers`)
      passing and confirm the new regression tests now pass.

## 3. Verification

- [x] 3.1 Run the full suite: `pytest` (no new uncovered/partially covered lines
      beyond the `if TYPE_CHECKING:` imports).
- [x] 3.2 Run `ruff format` and `ruff check` on the changed files.
- [x] 3.3 Run `ty check .` (via the Zed-installed binary) and confirm no new
      diagnostics.
- [x] 3.4 If any user-visible behaviour changed, update `README.md`.
