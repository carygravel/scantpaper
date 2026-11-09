# Tasks

## 1. Regression tests (TDD)

- [x] 1.1 Add tests in `src/scantpaper/tests/test_savethread.py` for a 1-bit
      Flate XObject and a 1-bit inline Flate image, asserting the saved PDF
      uses CCITT Group 4 with `/K -1` and the same 1-bit bitmap.
- [x] 1.2 Add tests for the skip cases: 8-bit images, non-gray images,
      already-Group 4 and already-JBIG2 streams, a PDF with no images, and a
      page with no resources or an existing `/ScantpaperIm0` name.
- [x] 1.3 Assert the pass runs after a successful text-layer embed and is
      best-effort: a failure logs a warning and the save still completes.
- [x] 1.4 Confirm the bilevel save tests fail on Ubuntu 26.04 before the fix.

## 2. Restoration pass

- [x] 2.1 Add `_group4_stream()`, `_group4_filter_and_parms()`,
      `_is_unconverted_bilevel_image()`, `_page_xobjects()`,
      `_restore_inline_bilevel_g4()` and `_restore_bilevel_g4()` to
      `src/scantpaper/savethread.py`.
- [x] 2.2 Call `_restore_bilevel_g4()` in `do_save_pdf` after a successful
      `_embed_text_layer()` and before `_maybe_convert_to_jbig2()`, wrapped so
      a failure logs a warning instead of failing the save.
- [x] 2.3 Confirm the Group 4 tests pass on Ubuntu 26.04 with the packaged
      OCRmyPDF and Ghostscript 10.06.

## 3. Documentation

- [x] 3.1 Add a changelog entry under 4.0.4 describing the preserved Group 4
      encoding on every supported Ghostscript version.
- [x] 3.2 Update the compression section of `README.md` to say that Group 4
      is restored when the PDF/A converter rewrites the image.

## 4. Integration and quality gates

- [x] 4.1 Run the full `pytest` suite and confirm the coverage gate passes
      with no newly uncovered or partially covered lines beyond the allowed
      `if TYPE_CHECKING:` imports.
- [x] 4.2 Run `python3 dev/check_test_coverage.py` and confirm the
      uncovered/partial counts are at or below the recorded baseline.
- [x] 4.3 Run `ruff format` and `ruff check` on the changed files and confirm
      both are clean.
- [x] 4.4 Run `ty check .` and confirm there are no diagnostics.
- [x] 4.5 Run `openspec validate --specs --strict --no-interactive` and
      `openspec validate --archived --no-interactive` and confirm both pass.

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Verify the archived result.
