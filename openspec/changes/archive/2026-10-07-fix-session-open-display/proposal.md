## Why

Opening a saved session file through File → Open (e.g. a `.sdb` produced by
"Saving a session") leaves the viewer stuck on thumbnails: the full-resolution
page image never loads and the OCR text layer stays empty, no matter how many
times the user switches pages. The DB and thread load correctly, so the failure
is entirely in the File → Open flow, which leaves the "bulk import" thumbnail
suppression flag enabled forever.

## What Changes

- Opening a `.sdb` session via the File → Open import flow now completes the
  surrounding import job once the page table is loaded, so the thumbnail-only
  `_suppress_full_display` state is released.
- The selected page is then loaded at full resolution and its text and
  annotation layers are rendered, matching the behaviour of the "Open
  session"/crash-restore paths.
- No change to the session file format, database schema, or storage layout.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `async-open-session`: `open_session` must report completion of the import
  job that opened it (File → Open route), not just when opened via the
  dedicated "Open session" action.
- `async-display-image`: opening a saved session must resume full-resolution
  display; the thumbnail-only suppression used during bulk imports must not
  persist past a session open.

## Impact

- `src/scantpaper/basedocument.py` — `BaseDocument.open_session()` must signal
  completion when its page table is ready.
- `src/scantpaper/file_menu_mixins.py` — the `_import_files` /
  `_import_files_finished_callback` bookkeeping around `_suppress_full_display`.
- `src/scantpaper/session_mixins.py` — `_display_image()` suppression check;
  `_on_page_loaded()` is the path that must run.
- `src/scantpaper/document.py` — session-file branch routing (likely unchanged,
  only context).
- Tests: a regression test that opens a saved session through the File → Open
  flow and asserts the full-resolution image is displayed and the text layer is
  rendered.