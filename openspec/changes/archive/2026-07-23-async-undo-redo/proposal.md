## Why

`undo()` and `redo()` are called synchronously from the main GTK thread, performing
SQLite queries and N pixbuf deserializations (temp file writes + GdkPixbuf loads)
that stall the GUI. These are the most user-visible blocking operations since they
are triggered by menu actions the user expects to be instant.

## What Changes

- Add `do_undo()` and `do_redo()` handler methods to `DocThread` that execute on
  the worker thread, returning both the snapshot data and the current selection in a
  single response (eliminating the extra `get_selection()` round-trip).
- Convert `Document.undo()` and `Document.unundo()` from direct `thread.undo()` /
  `thread.redo()` calls to async `thread.send("undo", ...)` with `finished_callback`.
- Remove the synchronous `DocThread.undo()` and `DocThread.redo()` methods (they
  become `do_undo` / `do_redo` handler methods invoked by the message loop).
- Keep `can_undo()`, `can_redo()`, `get_resolution()`, and `get_selection()` as
  synchronous Tier 1 methods (pure SQLite, ~microseconds).

## Capabilities

### New Capabilities

- `async-undo-redo`: Async dispatch for undo/redo operations via the BaseThread
  message-passing mechanism, including combined snapshot+selection response format.

### Modified Capabilities

_(none — no existing specs)_

## Impact

- **Files changed**: `scantpaper/docthread.py`, `scantpaper/document.py`
- **No API changes**: The public interface (`Document.undo()`, `Document.unundo()`)
  keeps the same signature; only the internal implementation changes from sync to async.
- **No new dependencies**: Uses existing `thread.send()` + callback infrastructure.
- **UX**: Undo/redo become non-blocking. The GUI remains responsive during
  deserialization. Signal blocking (`row_changed_signal`, `selection_changed_signal`)
  moves into the `finished_callback` rather than wrapping the call.
