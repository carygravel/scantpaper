## Why

`open_session()` calls `thread.open()` directly from the main thread, performing
SQLite operations (PRAGMA checks, migrations) on the main thread's connection while
the worker thread uses its own connection. It then calls `thread.page_number_table()`
synchronously, deserializing N thumbnail pixbufs (temp file writes + GdkPixbuf loads)
that stall the GUI during file open.

## What Changes

- Add `do_open()` handler to `DocThread` that performs the database open on the
  worker thread.
- Convert `page_number_table()` from a synchronous method to a `do_page_number_table()`
  handler invoked via `send()`.
- Rewrite `BaseDocument.open_session()` as a two-step async chain: send `"open"`,
  then in its `finished_callback` send `"page_number_table"`, then in that callback
  populate `self.data` and select the first page.
- `thread.close()` remains synchronous (Tier 1 — it closes the main thread's own
  SQLite connection, which is safe).

## Capabilities

### New Capabilities

- `async-open-session`: Async dispatch for session open, combining `open` and
  `page_number_table` into a chained async sequence.

### Modified Capabilities

_(none)_

## Impact

- **Files changed**: `scantpaper/docthread.py`, `scantpaper/basedocument.py`
- **No API changes**: `BaseDocument.open_session(**kwargs)` keeps the same signature.
- **No new dependencies**: Uses existing `send()` + callback chaining.
- **UX**: Opening a session file becomes non-blocking. The GUI remains responsive
  during database open and thumbnail deserialization.
