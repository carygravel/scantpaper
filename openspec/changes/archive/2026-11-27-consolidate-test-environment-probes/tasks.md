# Tasks

## 1. Shared environment module

- [x] 1.1 Add `src/scantpaper/tests/environment.py` with `DE_LOCALE`,
  `has_locale`, `requires_locale`, `requires_tool`, `has_jbig2`,
  `requires_jbig2`, `has_pillow_feature` and `requires_pillow_feature`;
  verify the module passes `ruff check`, `ruff format --check` and
  `ty check`.
- [x] 1.2 Add `src/scantpaper/tests/test_environment.py` covering both
  branches of each probe and marker by monkeypatching `has_locale`,
  `shutil.which`, `jbig2_available` and `features.check`; verify the
  module passes and every helper line is executed.

## 2. Locale consolidation

- [x] 2.1 Update `src/scantpaper/conftest.py` and
  `src/scantpaper/tests/test_helpers.py` to use `DE_LOCALE`,
  `has_locale` and `requires_locale`; remove the duplicate probe,
  `_HAS_DE_DE` and the repeated locale literals. Verify
  `test_helpers.py`, `test_conftest_helpers.py` and the
  `comma_locale`/`dot_locale` tests pass.
- [x] 2.2 Update `src/scantpaper/tests/test_1111_save_pdf.py` and
  `src/scantpaper/tests/test_0610_dialog_scan_sane.py` to use the shared
  helpers and constant; remove the local `has_locale` and its test.
  Verify the PDF locale test and the scan-dialog locale tests pass.

## 3. Tool-guard consolidation

- [x] 3.1 Replace the `cjb2` guards in
  `test_121_save_djvu.py`, `test_1601_import_djvu.py` and
  `test_101_document.py` with `requires_tool("cjb2")`; verify those
  modules pass and the skip reasons are the shared `requires cjb2`.
- [x] 3.2 Replace the `tesseract`, `unpaper` and combined process-chain
  guards in `test_411_tesseract.py`, `test_34_unpaper.py` and
  `test_51_process_chain.py` with `requires_tool(...)` markers; verify
  those modules pass.
- [x] 3.3 Replace the `qpdf`, `pdfunite`, JBIG2 and JPEG 2000 guards in
  `test_1111_save_pdf.py` and `test_1622_import_multipage_pdf.py` with
  `requires_tool`, `requires_jbig2` and `requires_pillow_feature`;
  verify those modules pass and no duplicate probe remains.

## 4. Integration verification

- [x] 4.1 Run the full suite without a switch and with
  `--fail-on-skip`; verify both pass with the same skips as before.
- [x] 4.2 Run `ruff check .`, `ruff format --check .`, `ty check .` and
  `python3 dev/check_test_coverage.py`; verify none reports an error and
  the audit keeps zero unexecuted statements.
- [x] 4.3 Run
  `openspec validate "consolidate-test-environment-probes" --strict
  --no-interactive`, `openspec validate --specs --strict
  --no-interactive` and `openspec validate --archived
  --no-interactive`; verify all pass.

## Workflow follow-up

- Archive the change after the project's review requirements are
  satisfied.
- Verify the archived result.
