# Proposal

## Why

The advanced OCR field accepts Tesseract *engine parameters* - one `name=value`
per line, with the name checked against `tesseract --print-parameters`. Users
instead reach for `tesseract --help-extra`, which lists *command-line flags*.
Copying a flag such as `--user-words /path` or `--psm 6` is rejected with a
generic "Invalid Tesseract option" message that never explains the
substitution, and the accepted `user_words_file=/path` form gives no
confirmation that the file was loaded: tesserocr silences tesseract's own
"failed to load" warning by pointing `debug_file` at `/dev/null`, so a
mistyped path is a silent no-op.

## What Changes

- Present the field as taking engine parameters (`name=value`, the value part
  of tesseract's `-c`), not command-line flags, in its label, hint and the
  README.
- Recognise a line that starts with a command-line flag and report the
  equivalent parameter where one exists - `--user-words` ->
  `user_words_file=...`, `--user-patterns` -> `user_patterns_file=...`,
  `--dpi` -> `user_defined_dpi=...` - and state plainly that the option is not
  accepted where no parameter exists (`--psm`, `--oem`, `--tessdata-dir`).
- Accept `-c NAME=VALUE` as an alternative spelling of `NAME=VALUE`.
- Check file-valued input parameters (`user_words_file`,
  `user_patterns_file`) before OCR starts: the path is resolved, and an entry
  whose file is missing or unreadable is reported instead of being silently
  ignored.
- Record the resolved options, including any word/pattern file paths, in the
  log when OCR runs so a user can confirm what was applied.

## Capabilities

### New Capabilities

<!-- None: this refines the existing advanced OCR options behaviour. -->

### Modified Capabilities

- `ocr-recognition`: the advanced options field's accepted syntax, its error
  messages, and its treatment of file-valued parameters change.

## Impact

- `src/scantpaper/postprocess_controls.py`: field wording and validation.
- `src/scantpaper/tesseract.py`: flag-to-parameter mapping, `-c` parsing, and
  file-valued parameter checks.
- `README.md`: document the accepted syntax and the flag-to-parameter
  equivalents.
- `po/scantpaper/*.po`: new and reworded UI strings, marked `#, fuzzy`.
- `src/scantpaper/tests/`: cover the corrective messages, `-c` acceptance, and
  missing-file reporting.
- No new dependency and no database schema change.
