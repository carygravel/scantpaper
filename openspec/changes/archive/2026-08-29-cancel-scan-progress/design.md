# Design — cancel-scan-progress

## Context

Motivation: see `proposal.md — Why`. Requirements: see the delta specs for
`sane-page-acquisition` and `background-job-cancellation`.

Current state that shapes the approach:

- `BaseThread` runs every request in a single worker thread
  (`basethread.py:219-232`). For SANE, `do_scan_page` blocks the worker inside
  `device_handle.snap()` (`image_sane.py:208`).
- `SaneThread.cancel()` (`image_sane.py:320-333`) drains the request queue by
  silent discard and sends a `"cancel"` request. The worker can only process
  that request *after* the current `snap()` returns, so an in-flight transfer
  is never interrupted.
- `ResponseType.CANCELLED` is declared but never emitted (`basethread.py:30`);
  `CALLBACKS` has no `cancelled` stage; `Request` has no `.cancelled()`
  method. The terminal branch in `_monitor_response` (`basethread.py:355-358`)
  already treats `cancelled` as terminal (entry removed, job counted).
- The scan batch is serial: one `scan_page` request in flight, the next queued
  only after the previous one finishes (`image_sane.py:263-310`). User clicks
  are delivered on the GLib main thread, which is also where `monitor()`
  dispatches responses.
- SANE's `sane_cancel` (python-sane's `cancel()`) is specified to be callable
  from a thread other than the one blocked in a transfer.

## Goals / Non-Goals

**Goals:**
- A user cancel interrupts an in-flight page transfer promptly (not "after it
  finishes").
- A deliberate cancel is not surfaced as an error dialog, and the partial page
  is not imported.
- Queued-but-unstarted requests dropped by a cancel notify their requester and
  are removed from the callback registry (resolves the W0511 FIXME).
- The non-scan threads (import/save/post-process) keep their existing cancel
  contract (the "cancel request + finished callback" pattern) while gaining
  correct notification for jobs they drop.

**Non-Goals:**
- Changing the import/save/post-process kill-pid machinery (`Document.cancel`,
  pidfiles, `check_cancelled`) — already handled by cancel-progress-jobs.
- A visible "Cancelling…" UI state or progress-bar redesign.
- Changing `cancel-between-pages` semantics.

## Decisions

### D1 (C): Make CANCELLED a real terminal response in basethread

Add `"cancelled"` to `CALLBACKS` and add `Request.cancelled()` which emits a
`ResponseType.CANCELLED` response via the existing `put()` path.

- `send()` already copies every `CALLBACKS` entry from kwargs, so
  `cancelled_callback` stops being stashed as a request attribute
  (`basethread.py:199-208`) and becomes a real per-request callback. Its
  default is `None`, so every request's callback dict gains one null entry —
  additive, no behavior change for callers that never pass it.
- `_monitor_response`'s terminal `else` branch already deletes the entry and
  counts the job, and `_execute_callbacks_for_stage`/`_execute_stage_callbacks`
  already dispatch any stage generically, so a `CANCELLED` response flows
  through the existing machinery with no new dispatch code.
- `before`/`after` stage sets are initialized from `CALLBACKS`
  (`basethread.py:109-111`), so `cancelled` is registered there automatically.

*Alternative considered:* a SaneThread-local hack that calls a stashed
`cancelled_callback` directly from `cancel()`. Cheaper but duplicates the
callback machinery, bypasses response plumbing (progress/job counts), and
leaves the shared CANCELLED enum dead. Rejected.

### D2 (C): Fire cancelled for queued requests when a cancel drains them

Add `BaseThread.drain_cancelled_requests()`: remove every queued request, emit
`request.cancelled()` for each (so the requester is notified and the registry
entry is cleaned up by the normal monitor path), replacing the silent discard
in both `SaneThread.cancel()` and `Document.cancel()`.

- Ordering in `Document.cancel()` matters: drain the response queue first, then
  collect the request queue, then emit the cancelled responses — otherwise the
  pre-existing response drain `basedocument.py:166-170` would swallow the
  cancelled notifications we just queued.
- The drain can never double-terminal a request: a request the worker has
  already dequeued is no longer in the queue, so only never-started requests
  get a CANCELLED response; a request reaching `monitor` at the same moment
  simply completes as finished, which is not a conflict.
- Non-scan request owners (import/save) don't pass `cancelled_callback`, so the
  notification is a harmless no-op for them today but the leak is fixed.

*Alternative considered:* leaving `Document.cancel()` untouched. The
`background-job-cancellation` delta scenario "queued job reports cancelled"
would then be unmet for import/save. Rejected; adopting the helper is uniform.

### D3 (A): Cancel the device directly from the UI thread during a transfer

Give `SaneThread` two boolean flags, `_scan_active` and `_cancel_requested`,
both set/cleared by the worker in `do_scan_page` around the `snap()` call
(`_scan_active = True` immediately before, cleared in a `finally`; 
`_cancel_requested` reset at the start of each page). In
`SaneThread.cancel()`:

1. Drain queued requests (D2).
2. If `_scan_active` is true, call `self.device_handle.cancel()` **directly on
   the caller's thread** — this is the standard cross-thread SANE abort and is
   what unblocks the worker's `snap()`.
3. Set `_cancel_requested = True`.
4. Send the `"cancel"` request as today (its `do_cancel` re-issues
   `device_handle.cancel()` for backends that buffer/prefetch; harmless if the
   direct call already ran).

The direct call is *gated* on `_scan_active` so the batch-end and
cancel-between-pages cancels keep their current single-`do_cancel` behavior
and existing tests' `cancel_calls` counts (`FakeBrscan5Device`) stay valid.

*Alternative considered:* cooperative cancel from within the `snap()`
progress callback (mirrors the DocThread `check_cancelled` pattern). Only fires
while the backend delivers per-line progress; a backend that blocks in a single
`sane_read` would never reach the callback. Kept as a fallback note only; the
cross-thread call is the primary mechanism.

*Safety note:* the flags are plain CPython booleans written by the worker and
read by the UI thread; no lock required. A cancel arriving just as `snap()`
completes may find `_scan_active` still true and re-issue `cancel()` on an
already-finished transfer — a SANE no-op, and the page was effectively complete
anyway.

### D4 (B): Route an aborted transfer to CANCELLED, not ERROR

`SaneThread.handler_wrapper` already catches handler exceptions
(`image_sane.py:43-68`). Extend it: when the failing request is a `scan_page`
and `_cancel_requested` is set, call `request.cancelled()` instead of
`request.error(None, str(err))`, and skip the existing repair `self.cancel()`
(the device is already being cancelled).

- Classification by the `_cancel_requested` flag, not by string-matching the
  exception, so we don't depend on exactly how python-sane surfaces a
  cancelled read (raise vs return; message text varies across versions).
- After this, the interrupted page produces no `new_page_callback` (the image
  was never handed to the batch), no error dialog, and the batch's
  `cancelled_callback` (D5) terminates the session.

### D5 (B): The scan batch ends cleanly on a cancelled page

`scan_pages` currently threads only `finished_callback` into each `scan_page`
(`image_sane.py:263-310`). Add a `cancelled_callback` to each per-page request
that, when invoked, mirrors the batch-terminal branch of
`_scan_pages_finished_callback`: terminate the session (the queued `"cancel"`
request does this via `do_cancel`), do not increment page count, and invoke the
caller's `finished_callback` so the dialog emits `finished-process` (hiding the
progress bar and resetting the cursor) rather than `process-error`.

- The dialog's `error_callback` (`dialog/sane.py:513-515`) is unchanged but is
  no longer reached for deliberate cancels, satisfying "deliberate cancel is
  not an error".
- `_cancel_requested` is reset by the next `do_scan_page`, so the subsequent
  batch is unaffected ("device reusable after cancel").

## Risks / Trade-offs

- **python-sane surfaces a cancelled `snap()` in an unexpected way itself**
  → Classification is by our own `_cancel_requested` flag (D4), so exception
  shape/message never matters; only that `snap()` returns or raises.
- **Cross-thread `device_handle.cancel()` while the worker is blocked in a
  backend that buffers prefetched frames** → SANE's `sane_cancel` is specified
  for exactly this; the trailing `do_cancel` re-cancels for frame-dropping
  backends (brscan5), matching the existing `FakeBrscan5Device` semantics.
- **Adding `cancelled` to `CALLBACKS` ripples through shared basethread**
  → The change is additive (null default); full `pytest` run, and
  `test_083_basethread.py`'s terminal-state matrix is extended with CANCELLED.
- **Double-terminal (cancelled then finished) for the same request** → The
  drain only fires never-started queued requests (D2); the in-flight abort
  path emits CANCELLED as the single terminal event and the existing else
  branch deletes the registry entry; the per-page batch chain stops after one
  terminal outcome.
- **Cancel lands exactly at the end of a page** → The page was effectively
  transferred; it may be imported. Accepted: cancellation is best-effort at the
  frame boundary, consistent with the rest of the app.
- **`Document.cancel()` reordering (drain responses before emitting
  cancelled)** → Ordering is explicit in D2; the import/save integration tests
  (`test_1111_save_pdf`, `test_121_save_djvu`, `test_131_save_tiff`,
  `test_1611_import_tiff`) guard this path.

## Migration Plan

Internal-only, no data/config/dependencies. Deploy order:
1. D1+D2 basethread protocol and drain helper (C), with
   `test_083_basethread.py` and the re-enabled FIXME test.
2. D3 flags + direct device cancel (A), with the fake extended to model an
   interruptible transfer (blocking `snap()` that aborts on `cancel()`).
3. D4+D5 cancellation classification and batch termination (B), with
   `test_06182_dialog_scan_sane.py` / `test_06098_dialog_scan.py` updates.
4. Full `pytest`; verify no new `pylint` warnings.

Rollback is reverting the change.

## Open Questions

- Should the can progress bar briefly show "Cancelling…" after the click?
  Deferrable UI nicety; not required by the specs. Default: hide immediately.
- Whether `SaneThread.cancel()` should also clear a prefetched-frame buffer
  directly on the client thread (in addition to the trailing `do_cancel`), or
  keep that strictly in the worker for ordering. Deferred to implementation of
  D3; the current ordering (drain → send "cancel") already guarantees the
  worker-side cancel precedes any further scan of the same batch.