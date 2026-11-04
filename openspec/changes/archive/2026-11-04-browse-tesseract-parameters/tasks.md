# Tasks

## 1. Parameter source

- [x] 1.1 Add `TesseractParameter` and a cached `get_tesseract_parameters()`
  parser in `src/scantpaper/tesseract.py`, and derive
  `get_tesseract_variables()` from it; verify
  `pytest src/scantpaper/tests/test_411_tesseract.py -k tesseract_variables`
  still passes.
- [x] 1.2 Extend `test_411_tesseract.py` with parser cases: three
  tab-separated fields preserved in order, extra tabs kept in the description,
  a missing header, malformed rows and a failed command return `None`, and both
  functions share one cached shell-out; verify the new tests pass.

## 2. Parameter dialog

- [x] 2.1 Create `src/scantpaper/dialog/tesseractparams.py` with
  `TesseractParametersDialog(Dialog)`: name, default and description columns,
  name sorting, monospace names, and the unavailable-list label; verify a new
  `src/scantpaper/tests/test_tesseractparams.py` builds the dialog from sample
  rows and asserts the columns and contents.
- [x] 2.2 Add the `Gtk.SearchEntry` filter that repopulates the list
  case-insensitively over name, default and description, plus the no-match
  label; verify tests cover a name match, a description-only match, a
  case-different match, and no match at all.
- [x] 2.3 Annotate managed parameters with the control that owns them, keep
  them non-insertable, and gate the Insert button and `row-activated` on the
  selection; verify tests assert the note text, a disabled Insert button, a
  `selected_name` that stays `None`, and that activating a managed row writes
  nothing.
- [x] 2.4 Make Escape and the window close action emit
  `Gtk.ResponseType.CLOSE`, and focus the filter entry when the dialog is
  mapped; verify tests assert the CLOSE response and that `selected_name`
  defaults to `None`.
- [x] 2.5 Add the `_Available parameters` button below the variables view in
  `OCRControls._add_advanced_options()`, open the dialog with the cached rows
  and `MANAGED_VARIABLES`, and destroy it in a `finally`; verify a
  `test_postprocess_controls.py` test asserts the button exists only for
  Tesseract and that opening the dialog after a validation adds no second
  `exec_command` call.
- [x] 2.6 Add `OCRControls.insert_variable(name)` implementing the newline rule
  and cursor placement, and focus the field after the dialog closes; verify
  tests for an empty field, insertion after text with no trailing newline, and
  the cursor landing after `=`.
- [x] 2.7 Extend `test_tesseractparams.py` with the keyboard path: select a
  row, emit `row-activated`, and assert the selected name is returned and the
  dialog settles on OK; verify the tests pass.

## 3. Documentation and translations

- [x] 3.1 Document the browser in the README OCR options section: the button,
  filtering, insertion, managed parameters, and that the list comes from the
  installed engine; verify the text matches the UI labels and the section's
  lines stay within 80 characters.
- [x] 3.2 Regenerate `po/scantpaper/scantpaper.pot` with
  `PYTHONPATH=src python3 dev/generate_pot.py`, add no catalog translations,
  and run `PYTHONPATH=src python3 dev/check_po.py`; verify it reports no new
  source advisories.

## 4. Integration checks

- [x] 4.1 Run `ruff format --check .`, `ruff check .`, `ty check .` and the full
  `pytest`; verify no diagnostics, all tests pass, and the coverage gate holds
  with no new uncovered or partial lines beyond the documented type-only
  imports.
- [x] 4.2 Manually smoke test Tools -> OCR: expand the options, open the list,
  filter for `dpi`, insert after an existing entry, and confirm the focus and
  cursor position; verify OK applies the parameter and the log records it.
- [x] 4.3 Run `openspec validate browse-tesseract-parameters --strict
  --no-interactive`; verify it reports the change as valid.

## Workflow follow-up

- Archive the change with `/opsx-archive` after review, then run
  `openspec validate --archived --no-interactive`.
