# Tasks

## 1. Regression tests (TDD)

- [x] 1.1 Add a unit test in `src/scantpaper/tests/test_75_bboxtree.py` for a
      tree shaped `page -> para -> line + bare word`, asserting the exported
      hOCR has one `ocr_par`, two `ocr_line`s, and the bare word inside a
      line. Run the test and confirm it fails before the fix.
- [x] 1.2 Add unit tests for a paragraph containing only bare words and for a
      rotated bare word under a paragraph, asserting synthetic lines are
      created and the rotated word's line carries `textangle 90`. Confirm both
      fail before the fix.
- [x] 1.3 Add an end-to-end test in `src/scantpaper/tests/test_savethread.py`
      that writes hOCR with a paragraph, a line, and a bare word, runs
      `_hocr_to_ocr_pdf()`, and asserts `pdftotext` extracts the bare word.
      Confirm it fails before the fix.

## 2. Export fix

- [x] 2.1 In `src/scantpaper/bboxtree.py`, add a `para` branch to
      `_ensure_hocr_containers()` that wraps consecutive direct `word`
      children in synthetic `line` nodes in place, leaves existing line-like
      children untouched, and never nests a paragraph. Verify the tests from
      1.1 and 1.2 pass.
- [x] 2.2 Confirm the existing flat-tree, mixed-paragraph, and bare-line tests
      still pass and that a well-formed paragraph's output is unchanged. Run
      `pytest src/scantpaper/tests/test_75_bboxtree.py`.
- [x] 2.3 Add a changelog entry under 4.0.3 in `changelog.md` naming the
      manual-word-inside-paragraph fix, and verify the wording matches the
      behavior described in the spec delta.
- [x] 2.4 Check the searchable-text section of `README.md`; if it does not
      already say that manually added words are preserved in saved PDFs, add
      that sentence and verify it reads consistently with the surrounding
      documentation.

## 3. Integration and quality gates

- [x] 3.1 Run the end-to-end save test from 1.3 and confirm `pdftotext`
      extracts the manually added word from the saved PDF.
- [x] 3.2 Run the full `pytest` suite and confirm the coverage gate passes
      with no newly uncovered or partially covered lines beyond the allowed
      `if TYPE_CHECKING:` imports.
- [x] 3.3 Run `python3 dev/check_test_coverage.py` and confirm the
      uncovered/partial counts are at or below the recorded baseline.
- [x] 3.4 Run `ruff format` and `ruff check` on the changed files and confirm
      both are clean.
- [x] 3.5 Run `ty check .` and confirm there are no diagnostics.
- [x] 3.6 Run `openspec validate --specs --strict --no-interactive` and
      `openspec validate --archived --no-interactive` and confirm both pass.

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Verify the archived result.
