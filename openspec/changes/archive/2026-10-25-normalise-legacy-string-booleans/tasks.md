# Tasks

## 1. Accept the legacy false spelling

- [x] 1.1 In `src/scantpaper/config.py`, extend `_coerce_bool` so the empty
  string is accepted as false alongside the existing `"true"`, `"false"`,
  `"0"` and `"1"` spellings. Extend `test_coerce_helpers` in
  `src/scantpaper/tests/test_8_config.py` to assert that an empty string
  yields `False` and that whitespace-only and other unknown strings still
  yield `None`; verify that test passes with
  `pytest src/scantpaper/tests/test_8_config.py::test_coerce_helpers`.

## 2. Prove the load-time behaviour

- [x] 2.1 Add a test that a config containing `{"post_save_hook": ""}` loads
  with the setting `False`, an empty `load_warnings`, an INFO record for the
  conversion, and a written-back JSON `false` after `write_config`; verify
  the test passes and the persisted value is not `""`.
- [x] 2.2 Add a test that `{"close_dialog_on_save": ""}` is corrected the same
  way, proving the fix covers every boolean setting rather than one key, and
  that `{"cache options": "1"}` still loads as `True` without a warning;
  verify the test passes.
- [x] 2.3 Add a regression test that `{"post_save_hook": "evince %i"}` keeps
  the raw value and still records a user-visible warning; verify the test
  passes, pinning the boundary of the new coercion.
- [x] 2.4 Add a user-visible bullet to the newest section of `changelog.md`
  describing the corrected start-up warning for legacy empty-string boolean
  settings; verify the bullet names that case and is grouped with the other
  entries of the same release.

## 3. Verification

- [x] 3.1 Run the full `pytest` suite and confirm it passes with coverage at
  or above the configured threshold and no newly uncovered or partially
  covered lines except type-only imports.
- [x] 3.2 Run `ruff format` and `ruff check` on the touched files and confirm
  neither reports a diagnostic.
- [x] 3.3 Run `ty check .` and confirm it reports no diagnostics.
- [x] 3.4 Reproduce the reporter's case end to end: load a settings file
  containing `"post_save_hook": ""` through `read_config`, confirm there is no
  `load_warnings` entry, the INFO conversion is logged, and the next
  `write_config` stores `false`.

## Workflow follow-up

- Run `openspec validate 2026-10-25-normalise-legacy-string-booleans` and
  confirm the change is valid before archiving.
- Archive the change after review with `/opsx-archive`.
