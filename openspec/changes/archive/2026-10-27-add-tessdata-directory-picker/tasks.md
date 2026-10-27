# Tasks

## 1. Shared tessdata directory resolution

- [x] 1.1 Add `validate_tessdata_dir(path)` to `tesseract.py`: expand `~`,
  normalise, and reject a path that is missing, not a directory, unreadable,
  or without a direct `*.traineddata` file, returning a user-facing message.
  Verify with unit tests covering each rejection and a valid directory.
- [x] 1.2 Add `resolve_tessdata_dir(explicit)` with the precedence explicit
  selection -> `TESSDATA_PREFIX` -> system default, returning the normalised
  path (trailing separator) and an error instead of falling back. Verify with
  tests for each precedence step and for no fallback from an invalid source.
- [x] 1.3 Move `_find_tessdata_path()` from `docthread.py` to `tesseract.py`
  as `find_system_tessdata_dir()` and use it for the `./` system-default
  case; verify the existing docthread fallback tests now pass against the
  moved helper.
- [x] 1.4 Give `get_tesseract_codes()` an optional `path` argument that adds
  `--tessdata-dir` to the `tesseract --list-langs` call, and resolve or
  return an empty list without calling Tesseract when the environment guard
  fails. Verify with tests for the flag and the guarded case.

## 2. Tessdata directory control

- [x] 2.1 Add the **Tessdata directory** row to `OCRControls` above the
  language controls: entry with a `Default (system tessdata)` placeholder,
  `Browse...` folder chooser, and `Default` reset. Verify through
  `test_postprocess_controls.py` widget tests.
- [x] 2.2 Resolve on construction and store a directory error; on error use
  an empty language list and do not call Tesseract. Verify a broad
  `TESSDATA_PREFIX` produces an error and no subprocess call in tests.
- [x] 2.3 Rebuild the language list on entry activate, focus-out, Browse, and
  Default; keep the current primary and additional languages and render
  missing ones as "(not installed)". Verify with tests for changed
  directories and preserved selections.
- [x] 2.4 Expose the setting as `tessdata_dir` and include the stored
  directory error in `validation_error` before the language checks. Verify
  tests for the error ordering and for a clean value returning `None`.

## 3. OCR worker

- [x] 3.1 In `do_tesseract()`, resolve the directory from the new
  `tessdata_dir` option instead of calling `get_languages()` and the local
  fallback, report a resolver error through `request.error()`, and pass the
  resolved path to `InitFull(path=...)`. Verify worker tests for an explicit
  directory, the default path, and a rejected path that leaves the page
  untouched.

## 4. Settings and wiring

- [x] 4.1 Add `"tessdata directory": ""` to the configuration defaults and
  verify a config without the key still loads with the empty default.
- [x] 4.2 Pass the stored directory into `OCRControls` and write it back on
  OK in `ToolsMenuMixins` and `ScanMenuItemMixins`, alongside the other OCR
  options. Verify with the existing mixin tests that the value round-trips
  and reaches the worker.
- [x] 4.3 Use the guarded resolution for the startup locale language check
  in `app_window.py` so a broad `TESSDATA_PREFIX` cannot hang startup; log
  the invalid environment instead of showing a dialog. Verify with an
  app-window test.

## 5. Documentation and translations

- [x] 5.1 Document the picker, precedence, validation, the broad
  `TESSDATA_PREFIX` restriction, and that `m_data_sub_dir` is obsolete in
  the OCR section of `README.md`; verify every documented statement against
  the implementation.
- [x] 5.2 Regenerate the translation template and mark new strings in
  `po/scantpaper/*.po` as `#, fuzzy`; verify with
  `PYTHONPATH=src python3 dev/check_po.py` and `dev/generate_pot.py`.

## 6. Integration verification

- [x] 6.1 Run the full `pytest` suite, `ruff format --check`, `ruff check`,
  and `ty check .`; verify all pass and that uncovered or partially covered
  lines did not increase.
- [x] 6.2 Exercise both entry points manually with a real `tessdata_best`
  directory: verify the language list changes, OCR runs against it, and
  Legacy/Combined still report the existing engine-mode error.
  *(Accepted automated coverage in place of a manual GUI pass: the shared
  resolver, language-list rebuild, worker path selection, and engine-mode
  error are all unit-tested; no display or `tessdata_best` data is available
  in the build environment.)*

## Workflow follow-up

- Archive the change after review and after the translation review rules in
  `AGENTS.md` are satisfied.
