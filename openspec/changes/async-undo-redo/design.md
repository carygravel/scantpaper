## Context

The `BaseThread` message-passing architecture (`basethread.py`) provides a clean
async dispatch mechanism: `thread.send("process", args, callbacks={...})` enqueues
a request on the worker thread, which dispatches to `do_process()` methods and
returns results via the responses queue. The GTK main loop is woken via `os.pipe()`
+ `GLib.io_add_watch()`.

However, `DocThread.undo()` and `DocThread.redo()` are called directly from the
main thread (`document.py:358,378`), bypassing this mechanism. They perform:

1. `self._action_id -= 1` (or `+= 1`)
2. SQLite query for snapshot rows
3. `_bytes_to_pixbuf()` per row (temp file write + GdkPixbuf load)
4. Return list of `[page_number, pixbuf, initial_page_id]`

After the call, the main thread also calls `thread.get_selection()` synchronously
to get the selection state for the new action_id.

The synchronous `undo()` in `document.py` then:
- Blocks `row_changed_signal` and `selection_changed_signal`
- Sets `self.data` from the returned snapshot
- Unblocks signals
- Calls `self.select(self.thread.get_selection())` to reselect pages

## Goals / Non-Goals

**Goals:**
- Route undo/redo through the existing `send()` + callback mechanism
- Eliminate GUI stalls during undo/redo
- Bundle snapshot + selection into a single worker-thread response

**Non-Goals:**
- Changing `can_undo()` / `can_redo()` (Tier 1 — pure SQLite, stays synchronous)
- Changing `get_resolution()`, `get_selection()` (Tier 1)
- Modifying the undo step limit (out of scope)
- Touching print, `_display_image`, or other synchronous calls (later phases)

## Decisions

### D1: Bundle snapshot + selection in do_undo/do_redo response

**Choice:** `do_undo()` returns `{"snapshot": [...], "selection": [...]}`.

**Alternative considered:** Return only the snapshot, then call `get_selection()`
as a separate async request from the finished callback.

**Rationale:** Eliminates an extra round-trip. Both `snapshot` and `selection`
depend on the same `_action_id` value, so they must be computed atomically in the
worker thread anyway. A single response avoids a race where another request could
modify `_action_id` between the two calls.

### D2: Remove synchronous undo()/redo() methods from DocThread

**Choice:** Delete `DocThread.undo()` and `DocThread.redo()` entirely. They become
`do_undo()` and `do_redo()` handler methods invoked by `BaseThread.run()`.

**Alternative considered:** Keep the synchronous methods alongside the async handlers.

**Rationale:** The synchronous methods are no longer called from anywhere after
the conversion. Keeping them would be dead code. The `do_` prefix convention is
already established for all other async operations.

### D3: Signal blocking moves into the callback

**Choice:** Block/unblock `row_changed_signal` and `selection_changed_signal`
inside the `finished_callback`, not around the `send()` call.

**Alternative considered:** Block signals before `send()`, unblock in callback.

**Rationale:** Blocking signals before `send()` and unblocking in the callback is
functionally equivalent but spreads the logic across two scopes. Keeping it all in
the callback is more self-contained and matches the pattern used by other async
operations (e.g., `_display_callback`).

### D4: Error handling via existing _error_callback

**Choice:** Use `self._error_callback` from `session_mixins.py` for the
`error_callback` parameter.

**Rationale:** Already handles `StopIteration` (no more undo steps), logs errors,
and displays error dialogs. No new error handling needed.

## Risks / Trade-offs

- **[Race on rapid undo]** → User could trigger undo while a previous undo is
  still in flight. Mitigation: disable the undo menu item immediately when undo
  is triggered, re-enable in `_update_uimanager()` which runs after the callback.
  The existing `_update_uimanager()` already checks `can_undo()` / `can_redo()`.

- **[Signal blocking timing]** → Signals are now blocked inside the callback rather
  than around the call. If any code between `send()` and the callback triggers
  signal handlers, they could fire with stale data. Mitigation: the only code
  between send and callback is `_update_uimanager()` which doesn't modify page
  data.
