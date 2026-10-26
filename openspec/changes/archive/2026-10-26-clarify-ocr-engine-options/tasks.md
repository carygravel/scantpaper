# Tasks

## 1. Flag guidance in the parser

- [x] 1.1 Add a small command-line flag to engine parameter mapping
  (`--user-words` -> `user_words_file`, `--user-patterns` ->
  `user_patterns_file`, `--dpi` -> `user_defined_dpi`) and make the parser
  reject a line whose first non-whitespace characters are `-` or `--`
  (other than `-c`) with an error that names the flag and, where known, the
  equivalent parameter. Verify with unit tests covering the three mapped
  flags and `--psm 6` (no equivalent suggested).
- [x] 1.2 Accept a leading `-c` token in `parse_variables` so
  `-c tessedit_char_whitelist=0123456789` parses like the un-prefixed form.
  Verify with a unit test asserting the name and value, and a test that a
  `-c` line without `=` still reports a missing `=`.

## 2. File-valued parameter checks

- [x] 2.1 Add a check for `user_words_file` and `user_patterns_file` that
  resolves the path and reports a failure identifying the entry and the
  resolved path when the file is missing or unreadable. Verify with unit tests
  for a missing file, an unreadable file, a valid file, and a `~/...` value
  that is treated literally (no home-directory expansion).

## 3. OCR controls and validation

- [x] 3.1 Reword the advanced field label and hint to say it takes
  `name=value` engine parameters (the `-c` values), that `-c` is optional, and
  that `--flags` belong on the tesseract command line. Verify with a widget
  test asserting the new label and hint text.
- [x] 3.2 Wire the flag and file-check errors into
  `OCRControls.validation_error` so both the scan dialog and the Tools -> OCR
  dialog block OCR with the reported message. Verify with tests asserting
  `validation_error` returns the flag message and the missing-file message,
  and that a rejected scan sets the per-batch OCR skip flag.
- [x] 3.3 Document the accepted syntax and the flag to parameter table in the
  README. Verify each documented example is covered by the parser tests from
  group 1 (or by `tesseract --print-parameters`).

## 4. Diagnostics

- [x] 4.1 Extend the OCR log line in `do_tesseract` to include the resolved
  file-valued parameters. Verify with a `caplog` test asserting the resolved
  `user_words_file` path appears when OCR runs.

## 5. Translations

- [x] 5.1 Regenerate the translation template with
  `PYTHONPATH=src python3 dev/generate_pot.py`, add any new strings to
  `po/scantpaper/*.po` as `#, fuzzy` entries only, and run
  `PYTHONPATH=src python3 dev/check_po.py` until it reports no catalog
  problems.

## 6. Integration verification

- [x] 6.1 Run `ruff format`, `ruff check`, `ty check .`, and the full `pytest`
  suite; confirm they pass and coverage has not regressed.
- [x] 6.2 Run `openspec validate clarify-ocr-engine-options --strict` and fix
  any reported problems.

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
