# Proposal

## Why

The test suite expresses the same environment requirements in many places:
three locale probes (two identical `LC_NUMERIC` copies and one divergent
`LC_CTYPE` copy), and more than thirty repeated `shutil.which(...) is None`
skip guards for `cjb2`, `tesseract`, `unpaper`, `qpdf` and `pdfunite`. The
copies have already drifted in locale category and in reason wording, and
every new test repeats the same guard. The strict-mode behaviour added in
`fail-on-skipped-tests` is unchanged; this is a test-infrastructure refactor.

## What Changes

- Add `src/scantpaper/tests/environment.py` with one locale probe, a
  `requires_locale` marker, a `requires_tool` marker, and shared markers for
  the JBIG2 encoder and Pillow features.
- Replace the duplicated locale probes and skip declarations in
  `conftest.py`, `test_helpers.py`, `test_1111_save_pdf.py`,
  `test_conftest_helpers.py` and `test_0610_dialog_scan_sane.py`.
- Replace the repeated tool guards in the DjVu, unpaper, tesseract,
  process-chain, PDF import and PDF save tests with the shared markers.
- Keep every skip condition and the canonical-environment documentation
  unchanged; standardize the reasons on `requires <tool>` and
  `<locale> locale not available`.

## Capabilities

None. This is a pure test-infrastructure refactor with no spec-level
behaviour change, so `.openspec.yaml` sets `skip_specs: true`.

## Impact

- New: `src/scantpaper/tests/environment.py` and
  `src/scantpaper/tests/test_environment.py`.
- Changed: `src/scantpaper/conftest.py`,
  `src/scantpaper/tests/test_helpers.py`,
  `src/scantpaper/tests/test_1111_save_pdf.py`,
  `src/scantpaper/tests/test_conftest_helpers.py`,
  `src/scantpaper/tests/test_0610_dialog_scan_sane.py`,
  `src/scantpaper/tests/test_51_process_chain.py`,
  `src/scantpaper/tests/test_411_tesseract.py`,
  `src/scantpaper/tests/test_34_unpaper.py`,
  `src/scantpaper/tests/test_121_save_djvu.py`,
  `src/scantpaper/tests/test_1601_import_djvu.py`,
  `src/scantpaper/tests/test_101_document.py`,
  `src/scantpaper/tests/test_1622_import_multipage_pdf.py`.
- No application code, runtime dependencies, or user-visible behaviour
  changes.
