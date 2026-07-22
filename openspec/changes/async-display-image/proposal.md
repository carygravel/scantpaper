## Why

`_display_image()` calls `thread.get_page()` synchronously from the main GTK
thread, fetching a full image blob from SQLite, deserializing it via PIL, and
constructing a `Page` object. For large scans (300 DPI A4 = ~25MB uncompressed)
this can take 100-300ms, stalling the GUI every time the user selects a different
page. This is the most frequently triggered blocking call since it fires on every
thumbnail click.

## What Changes

- Add `do_get_page()` handler to `DocThread` that performs the full image fetch
  and `Page.from_bytes()` on the worker thread.
- Convert `_display_image()` to a two-phase display:
  1. **Immediate**: show the thumbnail pixbuf already in `self.data[i][1]` (sync,
     instant — the pixbuf was loaded during `page_number_table()`)
  2. **Deferred**: send `"get_page"` async, and in the `finished_callback` replace
     the thumbnail with the full-resolution image, update crop dialog, text canvas,
     and annotations.
- Provide a `get_page_sync()` test helper that wraps the async `send()` in a nested
  `GLib.MainLoop` for test convenience.
- Update ~15 test files that call `thread.get_page()` directly to use the helper.

## Capabilities

### New Capabilities

- `async-display-image`: Two-phase page display with thumbnail-first feedback and
  async full-resolution loading via the BaseThread message-passing mechanism.
- `get-page-test-helper`: A synchronous test wrapper for `send("get_page", ...)`
  using nested `GLib.MainLoop`.

### Modified Capabilities

_(none)_

## Impact

- **Files changed**: `scantpaper/docthread.py`, `scantpaper/session_mixins.py`,
  `scantpaper/app_window.py` (minor), ~15 test files, new test helper
- **No API changes**: `_display_image()` keeps the same signature.
- **UX**: Page selection shows thumbnail instantly, then swaps to full-res.
  Crop dialog, text canvas, and annotations are deferred until full-res loads.
- **Print operation**: `print_operation.py:46` calls `thread.get_page()` synchronously
  inside GTK's `draw_page_callback` — deferred to a follow-up change (prefetch
  approach).
