## Context

See proposal.md for motivation. The relevant flow today:

- File → Open hands every filename (including `.sdb`) to
  `_import_files()` (file_menu_mixins.py), which sets
  `self._suppress_full_display = True` and registers
  `_import_files_finished_callback` as the import `finished_callback`.
- `import_files()` → `get_file_info` → for a single session file,
  `_get_file_info_finished_callback2()` (document.py) calls
  `self.open_session(db=..., **options)`, forwarding `finished_callback`.
- `BaseDocument.open_session()` (basedocument.py) chases
  `open` → `page_number_table` → `on_table` (sets `self.data`,
  `self.renumber()`, `self.select(0)`) but **never invokes the forwarded
  `finished_callback`**. Only that callback resets `_suppress_full_display`
  and requests the full-resolution load
  (`_display_image` in session_mixins.py bails while the flag is set).

`slist` is the `Document` instance itself (app_window.py:360), so
`self.slist.data` in the finished callback is the same list that `on_table`
populates; `self.select(0)` leaves row 0 selected. All callbacks run on the
main thread via the thread-response dispatch, so invoking the import's
finished callback from `on_table` needs no new threading.

## Goals / Non-Goals

**Goals:**
- Opening a `.sdb` session through File → Open ends the surrounding import
  job, releasing `_suppress_full_display`, so the selected page loads at full
  resolution and the text/annotation layers render (dispatch
  `async-open-session` and `async-display-image` deltas).
- Reuse the existing `_import_files_finished_callback` finalisation rather
  than inventing a parallel code path.

**Non-Goals:**
- Changing the crash-restore / "Open session" path
  (`_open_session` → `open_session(db=..., delete=False, ...)`); it passes no
  `finished_callback` and is unaffected.
- Reworking how `.sdb` files are filtered or chosen in `open_dialog`.
- Fixing the pre-existing error-path inconsistencies in `open_session`
  (see Open Questions).

## Decisions

### D1: `open_session` signals import completion on the success path
At the end of `on_table`, after `self.select(0)`, invoke
`kwargs.get("finished_callback")` when present:
`cast("Callable[[Response], None] | None", kwargs.get("finished_callback"))`.
The File → Open route forwards it; the crash-restore route does not, so that
path keeps today's behaviour. Invoked on the main thread from an already
callback-dispatched closure — same thread, no new async plumbing.

Alternatives considered:
- **Clear the flag window-side in document.py's session branch.** Leaks
  window state into the model layer and only patches a single caller.
- **Do not enter `_suppress_full_display` for session files.** Cannot be
  decided until `get_file_info` reports the format, by which point the flag is
  already set; would require restructuring `_import_files`.
- **Synthesise a real `Response` to pass to the finished callback.** Adds a
  fake request/response for no gain; the callback only needs
  `progress.finish(response)`.

### D2: The finished callback accepts `Response | None`
`_import_files_finished_callback` and the progress finaliser already tolerate
`None` (`progress.finish(Response | None)` hides the bar when there is nothing
pending). Passing `None` from `open_session` is type-clean after widening
`_import_files_finished_callback`'s parameter to `Response | None`. The rest
of the callback — clear `_suppress_full_display`, display the selected page —
is exactly what a completed import must do.

### D3: Single-file session opens only
The session branch of `_get_file_info_finished_callback2` runs only when
exactly one file is selected and it is a session file; multi-selection takes
`_get_file_info_finished_callback2_multiple_files`. The fix is therefore
naturally scoped to the single `.sdb` open.

## Risks / Trade-offs

- [Slight double render: `select(0)` shows the thumbnail while suppressed,
  then `_import_files_finished_callback` re-requests the same page at full
  resolution.] → Harmless and identical to the existing "import completes,
  show the final page" behaviour on bulk imports; no thrashing since one
  extra call happens only once per open.
- [The fix depends on `finished_callback` being forwarded with `**options`
  into `open_session`; a future caller that passes a `finished_callback`
  expecting a real `Response` would break on `None`.] → The only current
  caller (`_import_files_finished_callback`) is `None`-tolerant after D2;
  the contract is documented on the new invocation site.
- [Error paths still leave the window in a partially-initialised state.] →
  Pre-existing; deferred, tracked as an open question below.

## Open Questions

- **Error-path finalisation / `_error_callback` contract:** on `"open"` or
  `"page_number_table"` failure, `open_session.on_error` calls the error
  callback as `(None, "Open file", status)` while the window's
  `_error_callback(response)` consumes a `Response`; and the import flow is
  not finalised (suppression stays set, progress stays up). This affects both
  the File → Open and crash-restore routes and deserves its own change rather
  than being tangled into this fix.
- **Mixed selection:** a dialog selection containing a `.sdb` plus image files
  takes a separate batch path that handles the session file as an ordinary
  import; out of scope here.