## Why

A user's 3.0.24 session with 598 OCR pages and 915 imported pages ended with
`OSError: [Errno 24] Too many open files` in `create_pidfile` and repeated
`Gdk-CRITICAL ... memfd_create ... Too many open files` warnings. The cause is
not GTK or OCRmyPDF: every generated background request stores a
`data_callback` partial (or closure) inside the same options dict that the
callback captures, and that dict also holds the request's PID file. When the
request terminates, the dict and callback keep each other alive, so
`Importhread._request_completed` can remove the pidfile from `running_pids`
but cannot close it. One file descriptor per OCR/processing request stays open
until a full cyclic-GC pass; long batches exhaust the 1024-fd limit before
that happens.

The same session also hit a second error path bug: `create_pidfile` calls the
error callback with four positional arguments, but `_error_callback` accepts
two, so the original "Too many open files" failure was replaced by
`TypeError: _error_callback() takes 2 positional arguments but 4 were given`.

## What Changes

- Remove the self-retaining callback graph from per-request options. Generated
  methods (`tesseract`, `rotate`, `threshold`, ...) and `Document.import_file`
  SHALL pass the data callback separately or capture an options copy, so the
  options dict does not reference the callback that references it.
- Release each request's PID file deterministically when the request reaches
  a terminal state, without depending on cyclic GC. Preserve the PID file for
  as long as the request is active so `cancel()` can still read the spawned
  process ID.
- Keep the existing callback lifecycle contract: data callbacks still receive
  the original options they need for post-processing, and terminal callbacks
  still run in the registry-deletion order.
- Fix the `create_pidfile` error path so a PID-file failure invokes the
  configured error callback with the signature it declares and reports the
  original OS error.
- Add regression coverage that sends many requests without forcing a GC and
  asserts that no PID-file descriptors remain open after their terminal
  callbacks, and that the old options graph is not retained.
- Add a user-visible note to `changelog.md` for the 4.0.0 release.

## Capabilities

### New Capabilities

- `background-request-lifecycle`: Background requests (OCR, import, and
  post-processing) release their per-request PID file and callback options
  when they terminate, so long sessions stay within the process's
  file-descriptor limit and do not accumulate request state.

### Modified Capabilities

## Impact

- `src/scantpaper/basedocument.py`: `_modify_method_generator` and
  `_note_callbacks`; the generated request options must no longer form a
  cycle.
- `src/scantpaper/document.py`: `import_file`, `split_page`, `unpaper`, and
  `user_defined` callback construction; `import_scan` must stay cycle-free.
- `src/scantpaper/importthread.py`: `_request_completed` is the place to
  release terminal request resources, if closing there is chosen rather than
  relying on the broken cycle.
- `src/scantpaper/basedocument.py` / `tools_menu_mixins.py`: the
  `create_pidfile` error-callback call and its declared signature.
- `src/scantpaper/tests/`: new regression tests for request cleanup, long
  batches, and the error-callback arity.
- `changelog.md`: 4.0.0 entry describing the fix.
- No dependency, database-schema, or saved-format changes.
