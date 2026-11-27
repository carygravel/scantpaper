# Design

## Context

`Document.cancel(cancel_callback, process_callback)` is cooperative. It
drains the response queue, drains queued-not-started requests (each reported
`CANCELLED`), sets `thread.cancel = True`, kills pidfile-registered
subprocesses, and finally queues a `"cancel"` request whose
`finished_callback` is the caller's cancel callback. The worker checks the
flag only where `check_cancelled()` is called; `do_cancel()` resets it when
the queued `"cancel"` request is finally processed.

In `SaveThread.do_save_pdf()` the only `check_cancelled()` is inside
`_assemble_pdf()`'s per-page loop. The phases after it — the in-process
ocrmypdf text-layer embed (`_embed_text_layer()`), the best-effort JBIG2 pass
(`_maybe_convert_to_jbig2()`), and `_finalize_pdf()` (metadata, encryption,
PS conversion, post-save hook) — run to completion no matter the flag. So a
cancel that lands once the worker is past page assembly is ignored: the PDF
is written and the request reports `FINISHED`. This is the armhf
`test_cancel_save_pdf` failure: there the worker is scheduled through
`_assemble_pdf()` (whose per-page check still sees `cancel == False`) before
`cancel()` sets the flag.

A second gap: `BaseThread.handler_wrapper()` turns *any* handler exception —
including the deliberate `CancelledError` from `check_cancelled()` — into
`request.error()`, so an interrupted running job currently reports `ERROR`
(and the GUI's `_error_callback` would show a message dialog on cancel). The
`background-job-cancellation` spec requires `CANCELLED` instead.

## Goals / Non-Goals

**Goals:**

- A PDF save stopped by a cancel that lands at any phase, reported as
  `CANCELLED`, never as `FINISHED` or `ERROR`.
- Deterministic `test_cancel_save_pdf` that no longer depends on which thread
  wins a race with a single-page save.
- No behaviour change to queued-request cancellation or to the cancel/pidfile
  machinery itself.

**Non-Goals:**

- Making ocrmypdf's in-process children killable (they are spawned by
  ocrmypdf, not pidfile-registered; out of scope, unchanged).
- Cancellation breakpoints in the DjVu/TIFF save paths (same cooperative gap,
  but their cancel tests do not currently fail on armhf).
- A visible "Cancelling…" progress state.
- Cross-thread locking around `thread.cancel` (reads/writes of a Python
  bool are atomic; the existing code already relies on this).

## Decisions

### D1: Move `CancelledError` to `basethread.py`; re-export from
`importthread.py`

`handler_wrapper()` needs to recognise `CancelledError`, but
`importthread.py` already imports `BaseThread` from `basethread.py`, so
`basethread` cannot import the exception from `importthread` without a cycle.
Define the class in `basethread.py` and re-export the same object from
`importthread.py` (`from scantpaper.basethread import CancelledError, ...`),
so existing imports (`from scantpaper.importthread import CancelledError`)
and `check_cancelled()` continue to name one identical class.

### D2: Sample `check_cancelled()` at every PDF phase boundary

Insert `self.check_cancelled()` after `_assemble_pdf()`, after
`_embed_text_layer()`, after `_maybe_convert_to_jbig2()`, and before
`do_set_saved()`. Each phase is the longest stretch of pure-CPU/child work
between checks; a cancel can then stall at most one phase. Raising
`CancelledError` propagates through `handler_wrapper()` (see D3); the
`TemporaryDirectory` context in `do_save_pdf()` cleans up scratch files, and
the worker stays alive to process the queued `"cancel"` request, which resets
the flag — so the thread remains usable.

### D3: `handler_wrapper()` reports `CancelledError` as `CANCELLED`

Catches `CancelledError` before the generic `except Exception`, still runs
`_request_completed(request)` (to release pidfiles), sends
`request.cancelled()`, and returns `True` so the worker loop
continues. It is logged at info level, not as a traceback, because an
interrupted job is expected, not a failure. The request is then removed from
the registry by `_monitor_response()` exactly like any other terminal
`CANCELLED` response (already covered by
`test_cancelled_response_dispatches_cancelled_callback`).

### D4: Keep the end-to-end cancel test unchanged

With D2/D3 the only way the save's `finished_callback` can fire is if the
entire multi-second save completes before `cancel()` runs — impossible in the
microseconds between `save_pdf()` and `cancel()` in the test. So
`test_cancel_save_pdf` keeps asserting `finished_callback.assert_not_called()`
and, per the spec's "Application remains usable after cancel", still verifies
that a follow-up `save_image()` produces a valid JPEG.

## Risks / Trade-offs

- **Partial output left on disk after a cancel**: same as today; the output
  file may already be written when the post-finalize breakpoint fires. The
  spec only forbids *presenting* partial output as completed, which the
  `CANCELLED` report satisfies.
- **`request.data()` emitted by a cancelled request's `finally`** (e.g. the
  embed's `request.data(1.0)`): harmless; a `data_callback` runs but the
  request is still reported `CANCELLED` and its `finished_callback` never
  fires.
- **Job with no registered cancelled callback** (the GUI does not pass one to
  `save_pdf`): the `CANCELLED` response simply removes the request from the
  registry; the GUI's progress bar is dismissed by the explicit cancel
  request's callback, unchanged.
- **Coverage**: the new branch in `handler_wrapper` and the new breakpoints
  must be exercised by the added unit tests so the 99% gate holds.

## Migration Plan

Internal-only change; no data, config, or dependency changes. Rollback is
reverting the change. Order: move `CancelledError` (D1) → breakpoints (D2) →
`handler_wrapper` (D3) → tests.
