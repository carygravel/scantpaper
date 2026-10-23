## 1. Language and variable helpers

- [x] 1.1 Add failing unit tests for `split_language_spec` and
  `join_language_spec`: single code, ordered `+` specification, whitespace,
  empty entries, and round-trip behaviour.
- [x] 1.2 Add failing unit tests for `parse_variables`: valid entries, blank
  lines, comments, values containing `=`, missing `=`, duplicate names, and
  surrounding whitespace.
- [x] 1.3 Implement the language-spec and variable-parsing helpers in
  `src/scantpaper/tesseract.py` until the tests pass.
- [x] 1.4 Add tests for a cached `get_tesseract_variables()` that parses
  `tesseract --print-parameters`, including command failure and unexpected
  output failing open.
- [x] 1.5 Implement `get_tesseract_variables()` in
  `src/scantpaper/tesseract.py`.

## 2. OCR controls

- [x] 2.1 Add widget-level tests for the primary language combo and the
  additional-languages popover: adding and removing languages, preserving
  selection order, preventing duplicates, changing the primary language, and
  the resulting `language` specification.
- [x] 2.2 Add tests for stored languages that are no longer installed:
  `(not installed)` rows remain visible, are not silently replaced, and block
  OCR.
- [x] 2.3 Add tests for the advanced options field: loading, editing,
  persistence in the `variables` property, and the expander being disabled
  when OCR is inactive.
- [x] 2.4 Add tests for `OCRControls.validation_error`: missing language,
  missing installed language, malformed variables, unknown variables, and a
  valid configuration.
- [x] 2.5 Implement the shared sensitivity container, the primary combo plus
  additional-languages popover, and the ordered composition of
  `language`.
- [x] 2.6 Implement the advanced options expander and the `variables`
  property.
- [x] 2.7 Implement `validation_error` using the helpers from group 1.

## 3. OCR worker

- [x] 3.1 Update `test_docthread.py` with failing tests that assert
  `PyTessBaseAPI(init=False)` plus
  `InitFull(path=..., lang=..., variables=...)`, including multi-language
  specs and empty variables.
- [x] 3.2 Add worker tests for the post-init unknown-variable check and for a
  failed initialisation leaving the page unmodified.
- [x] 3.3 Update `do_tesseract` to initialise with `InitFull` and apply the
  parsed variables.
- [x] 3.4 Add an integration test that OCRs a page with two installed
  languages when available, skipping when fewer than two are installed.

## 4. Configuration and dispatch

- [x] 4.1 Add `"tesseract variables": ""` to `DEFAULTS` in
  `src/scantpaper/config.py` and cover loading a config without the key and
  loading a saved value.
- [x] 4.2 Update the OCR tools dialog to pass `variables` into
  `OCRControls` and `_run_ocr`, validate before dispatch, and persist both
  settings; extend `test_tool_menu_mixins.py`.
- [x] 4.3 Update the scan callback to persist `"tesseract variables"`,
  validate before dispatching, and set the transient per-batch flag when
  validation fails; extend `test_scan_menu_item_mixins.py`.
- [x] 4.4 Update `_new_scan` to pass `variables` and to omit OCR when the
  per-batch validation flag is set; cover both paths in tests.
- [x] 4.5 Update `Document._post_process_ocr` to forward `variables` and cover
  it in `test_document.py`.

## 5. Documentation and translations

- [x] 5.1 Add a README section covering multi-language selection, language
  order, `tessdata_best` (including the speed and size trade-off), user word
  and pattern lists, absolute paths, and the `TESSDATA_PREFIX` workaround.
- [x] 5.2 Add a `changelog.md` entry describing multi-language OCR and
  additional tesseract variables.
- [x] 5.3 Regenerate the translation template with
  `PYTHONPATH=src python3 dev/generate_pot.py` and add any new translations
  as `#, fuzzy` entries only where a translation is available.
- [x] 5.4 Run `PYTHONPATH=src python3 dev/check_po.py` and fix any catalog
  problems.

## 6. Verification

- [x] 6.1 Run `ruff format`, `ruff check`, `ty check .`, and the full
  `pytest` suite; confirm coverage did not regress.
- [x] 6.2 Run `openspec validate add-tesseract-ocr-options --strict`.
- [x] 6.3 Smoke-test the scan and Tools OCR dialogs with a multi-language
  selection and a `user_words_file` entry, and confirm the settings survive a
  restart.
