## Context

`BaseDocument.open_session()` (`basedocument.py:559`) currently:

1. Copies the session DB file to a temp location (`shutil.copy` — main thread, fast)
2. Calls `thread.close()` to close the main thread's SQLite connection
3. Blocks `row_changed_signal`
4. Calls `thread.open(db)` — **direct SQLite on the main thread** (PRAGMA checks,
   migrations via `DocThread.open()` at `docthread.py:207`)
5. Calls `thread.page_number_table()` — SQLite query + N `_bytes_to_pixbuf()` calls
6. Sets `self.data` from the result
7. Unblocks signals
8. Calls `self.select(0)`

Step 4 is an architectural violation: it opens a SQLite connection on the main
thread using `threading.get_native_id()`, while the worker thread has its own
connection. Steps 5-6 are the main GUI stall (N pixbuf deserializations).

## Goals / Non-Goals

**Goals:**
- Route both `open` and `page_number_table` through the worker thread via `send()`
- Chain the two async operations so `page_number_table` runs after `open` completes
- Keep `thread.close()` synchronous (it closes the main thread's own connection)

**Non-Goals:**
- Changing the session file format or copy logic
- Modifying `thread.close()` behavior
- Touching `thread.open()` in contexts other than `open_session()`

## Decisions

### D1: Chained async with nested callbacks

**Choice:** Send `"open"`, then in its `finished_callback` send `"page_number_table"`,
then in that callback populate `self.data`.

**Alternative considered:** A compound `do_open_and_get_table()` handler that does
both in one worker-thread call.

**Rationale:** Chaining is more composable — each `do_` handler is a single
responsibility. A compound handler would duplicate the `do_page_number_table` logic
or require calling it internally. The nesting is one level deep and readable.

### D2: Signal blocking in outer scope, unblocking in final callback

**Choice:** Block `row_changed_signal` before the first `send()`, unblock in the
`page_number_table` finished callback.

**Rationale:** The signal must be blocked for the entire async sequence, not just
during the `open` step. Blocking in the outer scope and unblocking in the final
callback is cleaner than passing the block state through callbacks.

### D3: keep thread.close() synchronous

**Choice:** `thread.close()` stays as a direct call from the main thread.

**Rationale:** It closes the main thread's own SQLite connection (keyed by the
main thread's `get_native_id()`). This is safe — it's cleaning up a resource the
main thread owns. Making it async would add complexity with no benefit.

### D4: Error forwarding

**Choice:** Pass `kwargs.get("error_callback")` to both `send()` calls.

**Rationale:** The caller already provides an error callback. If `open` fails,
the error callback fires and `page_number_table` is never sent. If
`page_number_table` fails, the error callback fires. No new error handling needed.

## Risks / Trade-offs

- **[Open failure leaves stale state]** → If `send("open")` fails, the old
  database connection was already closed by `thread.close()`. The error callback
  fires, but the session may be in an inconsistent state. Mitigation: this is
  the same behavior as the current synchronous version — `open_session()` already
  doesn't recover gracefully from `thread.open()` failures.

- **[Callback nesting depth]** → Two levels of nested callbacks. Mitigation: this
  is the maximum depth (open → table), and each callback is short.
