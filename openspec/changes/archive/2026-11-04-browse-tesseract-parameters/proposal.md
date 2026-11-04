# Proposal

## Why

The OCR interface's advanced field accepts the engine parameters the installed
Tesseract reports, but the application never shows them. The field explains the
syntax and warns against command-line options, yet a user who wants a parameter
without a dedicated control has to guess a name, receive an "Unknown Tesseract
option" error, and then work out that `tesseract --print-parameters` exists and
must be run in a terminal.

Presenting the installed engine's own list inside the dialog removes that
guesswork and keeps the field's vocabulary aligned with the Tesseract version
that will actually run, instead of a bundled list or documentation that can
drift.

## What Changes

- In the OCR options, the **Advanced Tesseract engine parameters** expander
  gains an **Available parameters** button, shown only for the Tesseract
  engine.
- The button opens a modal dialog listing the parameters the installed engine
  reports: name, default value, and description, sorted by name.
- A search field filters the list as the user types, matching the text
  anywhere in a parameter's name or description, case-insensitively.
- Selecting a row and choosing **Insert name**, or double-clicking the row,
  writes `name=` into the advanced field at the cursor, closes the dialog, and
  returns focus to the field with the cursor after the `=`. On a non-empty
  field whose text does not end with a newline, the inserted entry starts on a
  new line.
- Parameters owned by dedicated controls (`tessedit_pageseg_mode` and
  `tessedit_ocr_engine_mode`) remain visible, are annotated with the control
  that owns them, and cannot be inserted.
- The list is read from `tesseract --print-parameters`, the same source the
  dialog already uses to validate names; it is fetched once and cached for the
  session.
- If the list cannot be read, the dialog says so instead of showing an empty
  list, and OCR remains runnable as before.
- The README documents the browser next to the existing advanced-parameter
  section.

## Out of Scope

- No change to how engine variables are parsed, validated, applied, or stored;
  the existing `Unknown Tesseract option` error text stays as it is.
- No completion or autocompletion while typing in the field.
- No editing of a parameter's value in the list: insertion provides the name
  and the user types the value.
- No bundled parameter list in the source tree.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ocr-recognition`: the advanced field's vocabulary SHALL be discoverable
  from the application: a parameter list read from the engine, searchable,
  with each entry's default and description; selecting an entry SHALL insert
  its name into the field; names owned by dedicated controls SHALL be shown as
  such and SHALL NOT be insertable; an unreadable list SHALL be reported
  without blocking OCR.
- `keyboard-focus-traversal`: the parameter list SHALL be reachable and
  operable from the keyboard, and focus SHALL return to the advanced field
  after an insertion.

## Impact

Affected code (expected):

- `src/scantpaper/postprocess_controls.py`: the button, the insertion into the
  variables text view, and the hand-off of the current buffer and cursor.
- A new dialog module under `src/scantpaper/dialog/` for the list, its filter,
  and the insert action, following the existing `Dialog` and padded-area
  helpers.
- `src/scantpaper/tesseract.py`: one cached parser returning
  `(name, default, description)` rows; `get_tesseract_variables()` derives its
  name set from it so both consumers share one shell-out and one format check.
- Tests: `test_411_tesseract.py` for the parser (valid, malformed, and failed
  output), `test_postprocess_controls.py` for the button, insertion, and
  managed names, a new dialog test for population, filtering, and the insert
  callback, and keyboard traversal coverage.
- `README.md`: a short addition to the OCR options section.

Not affected:

- No new dependency; the browser uses the already-required `tesseract` binary.
- No session-database, configuration, or CLI changes: the browser only writes
  text into the existing field, which the existing persistence path already
  stores.
- `list-typeahead` needs no requirement change: its existing "any list widget"
  requirement already covers the new list.
- `dialog-layout` and `dialog-buttons` need no requirement change: the new
  dialog follows their existing conventions.

## Risks

- The parameter set comes from the installed engine, so a different Tesseract
  build shows a different list. That is intended, but tests must not assert a
  fixed catalog.
- The list has hundreds of rows, so filtering is required for it to be usable.
  GTK's list typeahead is disabled app-wide (`list-typeahead`), which makes the
  search field the only viable way to find a name.
- The `--print-parameters` call is synchronous and has no timeout. It takes
  about 10 ms in practice and the same call already runs when OCR is
  confirmed, so the exposure is inherited; the dialog must still handle a
  failed or empty result explicitly.
- `get_tesseract_variables()` caches `None` on failure, so a failed list stays
  unavailable for the session; the dialog must explain that rather than show a
  blank window.
