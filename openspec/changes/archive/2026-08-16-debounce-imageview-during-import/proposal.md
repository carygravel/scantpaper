## Why

Importing a large batch of pages (e.g. 250 TIFFs) is fast on the worker thread,
but each imported page triggers a `_display_image` call that enqueues a
`get_page` request and synchronously decodes the full-resolution image on the
main thread. Because the import is worker-bound, pages arrive at the main loop
one at a time over the whole import, so the GUI spends minutes decoding and
displaying every intermediate page — even though the user only ever sees the
final one. The thumbnail, which is cheap and shown synchronously, already keeps
up.

## What Changes

- **Suppress full-resolution loads during a bulk import.** Add a
  `_suppress_full_display` flag. `_import_files` sets it before starting the
  import; `_import_files_finished_callback` clears it on completion and triggers
  one `_display_image` for the final page.
- In `_display_image` (`session_mixins.py:237`), always show the thumbnail
  synchronously, but only send the `get_page` request when the flag is clear.
- The thumbnail-first UX is preserved: the thumbnail updates instantly for every
  page, and the full-resolution image appears once when the import finishes.
- Scanning and manual single-page navigation are unaffected (they never set the
  flag and continue to load each page full-res immediately).

This eliminates the full-res load for every intermediate page during a large
import: only the final page is requested and decoded.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `async-display-image`: the "Thumbnail-first display" requirement changes so
  that during a bulk import, intermediate pages show only the thumbnail and a
  full-resolution load is deferred until the import completes.

## Impact

- `scantpaper/session_mixins.py` — `_display_image` gates the `get_page` send on
  the new `_suppress_full_display` flag.
- `scantpaper/file_menu_mixins.py` — `_import_files` sets the flag;
  `_import_files_finished_callback` clears it and triggers the final display.
- `scantpaper/app_window.py` — the selection-changed handler is unchanged (still
  fires per page; `_display_image` decides whether to load full-res).
- Tests in `scantpaper/tests/` covering `_display_image`, `_import_files`, and
  page display.
- No new dependencies. No DB schema change.
