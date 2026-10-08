## Why

Saving a session to a filename that already exists does nothing: no overwrite
confirmation appears, no error appears, and the save only succeeds once the user
invents a fresh name. Two defects combine — the save dialog only enables GTK's
overwrite confirmation for PDF/DjVu (so sessions, TIFF, text, hOCR and PS never
ask), and the session save itself uses SQLite `VACUUM INTO`, which refuses to
write over an existing non-empty database, raising an exception that escapes the
GTK callback uncaught.

## What Changes

- Saving to an existing filename prompts the user to confirm overwriting for
  **every** saveable output type (session `.sdb`, PDF, DjVu, TIFF, text, hOCR,
  Postscript, images), not just PDF/DjVu.
- Declining the confirmation keeps the existing file untouched and leaves the
  user in a state where they can pick another name.
- Confirming the confirmation actually replaces the file: session save becomes
  able to overwrite an existing session file, and does so atomically — a failed
  save never truncates or corrupts the user's previous file.
- A failure during session save is reported to the user (message dialog) instead
  of escaping as an unhandled exception from the file chooser callback; the
  chooser's lifecycle (destroy/close) is honoured on both success and failure.

## Capabilities

### New Capabilities

- `save-overwrite-confirmation`: Behaviour of the save flow when the chosen
  destination already exists — confirmation prompt for all output types,
  safe/atomic replacement of the previous file on confirmation, and user-visible
  error reporting when a session save fails.

### Modified Capabilities

<!-- none: no existing spec covers the save flow's overwrite behaviour -->

## Impact

- `src/scantpaper/file_menu_mixins.py` — `_save_file_chooser` (overwrite
  confirmation currently gated on `image type in ["pdf", "djvu"]`),
  `_file_chooser_response_callback` (exception escapes before
  `dialog.destroy()`), `file_exists` suffix/re-fire helper.
- `src/scantpaper/docthread.py` — `save_as` (`VACUUM INTO '<path>'` cannot
  replace an existing file; also breaks on paths containing `'`).
- `src/scantpaper/basedocument.py` — `save_session` pass-through.
- Tests: `tests/test_file_menu_mixins.py` (session save mocked, so the bug is
  invisible to the suite), `tests/test_docthread.py` (`test_save_as` asserts only
  the SQL string).
- No dependency, schema, or CLI changes. Session files on disk stay SQLite
  databases in the same format.
