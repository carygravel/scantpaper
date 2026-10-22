## Context

See `proposal.md` for the user-visible failure and evidence. The relevant
request flow is:

- `BaseDocument` builds a per-request options dict, creates a PID file with
  `tempfile.TemporaryFile()`, and registers it in
  `Importhread.running_pids`.
- Generated methods (`tesseract`, `rotate`, `threshold`, ...) build their
  options in `_modify_method_generator`, while `Document.import_file`,
  `split_page`, `unpaper`, and `user_defined` build theirs directly.
- `BaseThread.send()` stores callbacks in `self.callbacks[uuid]` and the
  request args in the `Request`; `_monitor_response()` deletes the registry
  entry on the terminal response.
- `Importhread._request_completed()` runs in the worker after the handler and
  removes the pidfile from `running_pids`, but does not close it.

The current construction stores the data callback inside the same dict that
the callback captures:

```python
kwargs["data_callback"] = partial(self.data_callback, options=kwargs)
```

`Document.import_file` does the equivalent with a closure. The dict therefore
references itself through the callback, and the dict also holds the PID file.
Refcounting can never release either, so a full cyclic-GC pass is required.
The probe in the proposal showed one open `#<inode> (deleted)` descriptor per
completed OCR page with `running_pids == 0` and `callbacks == 0`; an explicit
`gc.collect()` closed all of them. Long OCR batches promote these graphs to
older generations, where collections are rare enough that 598 pages left 598
descriptors open; the following `TemporaryFile()` failed with `EMFILE`.

## Goals / Non-Goals

**Goals:**

- Make PID-file release deterministic when a request terminates, without
  relying on cyclic GC or on changing GC thresholds.
- Release the request's options and callback graph by reference counting
  once the worker and dispatcher no longer need them.
- Keep the PID file readable for the whole active lifetime so cancellation
  can still read the spawned process ID.
- Keep the existing `data_callback` and post-processing semantics intact.
- Report a PID-file creation failure through the same error-callback contract
  used by the rest of the application, preserving the original OS error.

**Non-Goals:**

- Changing cancellation scope, progress reporting, or terminal callback
  ordering.
- Reworking `BaseThread`'s queue, registry, or response-dispatch design.
- Changing temporary-file handling inside OCRmyPDF, tesseract, PIL, or save
  backends; the measured leak is the application's own PID file.
- Adding automatic GC tuning or periodic `gc.collect()` calls.

## Decisions

### Pass callbacks to the thread instead of storing them in their own options

`functools.partial(self.data_callback, options=kwargs)` is only needed so the
data callback can see the request options. The thread's own callback helper
(`_note_callbacks` in `importthread.py`) already pops callback entries from
the options dict into the send callbacks. Construct the callback after the
options are complete and pass it as a separate keyword argument:

```python
self._note_callbacks(kwargs)
data_callback = partial(self.data_callback, options=dict(kwargs))
method(**kwargs, data_callback=data_callback)
```

The copy is made after `_note_callbacks` has added `pidfile` and `dir`, so
the callback still sees the full option set. The copy does not contain the
callback, and the request args dict does not contain it either, so there is
no cycle. Post-processing callbacks still mutate their own captured copy,
which is the same object for the whole chain.

`Document.import_file` uses a closure rather than a partial. Build it over
the outer `kwargs` but pass it separately:

```python
data_callback = _import_file_data_callback
self.thread.import_file(data_callback=data_callback, **kwargs)
```

The thread's `**kwargs` copy is the request args; the closure captures the
outer dict, not the request args, so neither points back to the other. Apply
the same pattern to `split_page`, `unpaper`, and `user_defined`, which
currently store their partials in the captured dict. `import_scan` already
captures the original options in a partial stored in a separate copy; keep
that shape and add a test so it does not regress.

Alternative considered: leave the cycle in place and call `gc.collect()` after
each terminal response. Rejected because it is expensive on the GUI thread,
still leaves the options graph alive between requests, and masks the design
error rather than fixing it.

### Close the PID file when the request terminates

Break the cycle for memory, and also release the descriptor explicitly for
determinism. `Importhread._request_completed()` already runs after a handler
finishes and finds the pidfile through `_request_pidfile()`. After removing
it from `running_pids` under the existing lock, close it there. A request
that is drained before it starts never runs a handler, so override the drain
hook or call the same cleanup for each drained request; otherwise a queued
cancelled request would still retain its pidfile.

Run the cleanup before the terminal response is queued, so the descriptor
is already closed when the terminal callback returns, as required by the
specification. This does not change the order in which callbacks run.

Closing at completion is safe because `create_pidfile()` always returns a
fresh file object for one request. The import flow creates one PID file for
file information and a new one for the import request; it never shares a
live PID file between two active requests. The file remains readable until
the handler returns, which is exactly the interval in which `cancel()` can
need its process ID. Closing is done under the same lock that protects
`running_pids`, with close errors logged rather than raised.

Alternative considered: rely only on refcount release after breaking the
cycle. Rejected as the sole mechanism because a queued request that is
cancelled before starting never reaches `_request_completed()`, and because
an explicit close documents and tests the intended lifetime.

### Report PID-file failure through a synthetic terminal response

The real error callbacks in the application take a single `Response`, while
`create_pidfile()` currently calls a three-argument
`(page, process, message)` callback intended for the old GTK3 rewrite. That
mismatch is the source of the logged
`TypeError: _error_callback() takes 2 positional arguments but 4 were given`.

Pass the process name to `create_pidfile()` from each call site and, on
failure, build a minimal `Request` with the options as its first argument and
a `Response` of type `ERROR`. Invoke the configured error callback with that
single response, exactly as the worker does for other errors. The response
status keeps the temporary directory and the original `OSError` text.
`create_pidfile()` still returns `None` so the caller can continue without
cancellation support, which is the current fallback.

Alternative considered: keep the three-argument contract and adapt the UI
callbacks to accept both shapes. Rejected because it would leave two error
contracts in the codebase and the existing UI callback is the one that
actually runs.

## Risks / Trade-offs

- **Snapshot semantics of the options copy** → Make the copy after
  `_note_callbacks()` and test the OCR post-processing chain, where callbacks
  mutate the captured options. If a future caller mutates the request options
  after sending, it must not expect the data callback to observe that
  mutation; document this in the helper.
- **Closing a PID file too early** → Close only after the handler returns
  (`_request_completed`) or before a drained request starts. Add a test that
  cancellation can still read the PID while the request is active.
- **Close/cancel race** → Perform the pop and close under `self.lock`, and
  make the cancellation reader tolerate a file that has just been closed
  (`OSError`/`ValueError` while reading) without killing the wrong process.
- **Synthetic request shape** → The error callback reads `request.args` and
  `request.process`. Build the synthetic request with the real options dict
  and process name, and cover it with a unit test that asserts the callback
  receives one `Response` and the message contains the original error.
- **Coverage** → The new branches (drained cleanup, close failure, synthetic
  response) need direct tests; the project fails below its coverage
  threshold.

## Migration Plan

No data or format migration. The fix ships in the next 4.0.0 build; users who
hit the error must restart the running instance to reclaim its already-leaked
descriptors. Add a `changelog.md` entry under 4.0.0.

`README.md` has no section documenting the old PID-file failure or descriptor
exhaustion, so only the changelog needs a user-visible entry.

## Open Questions

None.
