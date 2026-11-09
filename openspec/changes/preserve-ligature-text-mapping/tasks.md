# Tasks

## 1. Regression tests (TDD)

- [x] 1.1 Add tests in `src/scantpaper/tests/test_savethread.py` asserting the
      default shaping request receives `features={"liga": False}` and that
      the original method is restored afterwards.
- [x] 1.2 Add tests for explicit positional and keyword feature sets, and for
      a request that disables shaping.
- [x] 1.3 Cover the absent-renderer path and the loader returning `None` when
      fpdf2 is not installed.
- [x] 1.4 Confirm the mixed-angle searchable-text test fails on Ubuntu 26.04
      before the fix.

## 2. Ligature-disabling save path

- [x] 2.1 Add `_load_fpdf()` and the module-level `_fpdf` in
      `src/scantpaper/savethread.py`.
- [x] 2.2 Add `_without_ligature_shaping()` and wrap the
      `ocrmypdf.api._hocr_to_ocr_pdf()` call in `_embed_text_layer()`.
- [x] 2.3 Confirm the reproducer extracts `ff` on Ubuntu 26.04 with Ghostscript
      10.06 and that the emitted `ToUnicode` maps the glyph to `<0066>`.

## 3. Documentation

- [x] 3.1 Add a changelog entry under 4.0.4 describing the restored
      searchability of ligature words on 26.04.

## 4. Integration and quality gates

- [x] 4.1 Run the full `pytest` suite and confirm the coverage gate passes.
- [x] 4.2 Run `python3 dev/check_test_coverage.py` and confirm the
      uncovered/partial counts are at or below the recorded baseline.
- [x] 4.3 Run `ruff format` and `ruff check` and confirm both are clean.
- [x] 4.4 Run `ty check .` and confirm there are no diagnostics.
- [x] 4.5 Run `openspec validate --specs --strict --no-interactive` and
      `openspec validate --archived --no-interactive` and confirm both pass.

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Verify the archived result.
