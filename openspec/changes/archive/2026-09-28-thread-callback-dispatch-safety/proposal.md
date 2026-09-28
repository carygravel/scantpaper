# thread-callback-dispatch-safety

## Why

Debian autopkgtest failed `test_user_cancel_terminates_session` with a safety
timeout on one architecture, and the run also missed the coverage gate. The
timeout was not a SANE problem: `BaseThread` dispatches the `running` callback
stage by iterating `self.callbacks`, and those callbacks are permitted to call
back into the thread — a user cancel issues `send()`, which adds an entry —
so the iteration raises `RuntimeError: dictionary changed size during
iteration`. The thread's response pump is driven by three separate GLib
sources, and the exception's effect depends entirely on which of them happened
to be dispatching. When it is `_on_readable`, PyGObject removes the watch and
the thread can never deliver another response, so the cancelled scan never
reports back and the application hangs indefinitely with no error shown.

The `error_callback` safety net does not cover this: the `running` stage
invokes callbacks with no `Response`, and the failure-reporting path reads
`data.request.process`, so a callback that raises escapes as
`AttributeError: 'NoneType' object has no attribute 'request'` instead of
being routed to `error_callback` — reaching the same permanent hang. This
path is reachable today, because the scan dialog's running callback emits a
GTK signal and any handler may raise.

## What Changes

- Dispatch the `running` stage over a snapshot of the request registry, so a
  callback that registers or cancels a request cannot invalidate the
  iteration. This is the root-cause fix.
- Keep every GLib source owned by the response pump exception-proof: the pipe
  watch, the draining idle, and the periodic progress tick. A failure is
  logged and the pump keeps running, so a callback bug can no longer strand
  queued responses and hang the application.
- Fix error routing for callbacks invoked without a `Response`, so a raising
  `running` callback reaches `error_callback` as the surrounding code
  already intends instead of raising `AttributeError` out of the pump.
- Add deterministic regression tests that reproduce each failure without
  depending on GLib source-dispatch timing.
- No user-visible behaviour changes; this restores documented behaviour that
  the implementation did not reliably deliver.

## Capabilities

### New Capabilities

- `thread-response-dispatch`: guarantees that the background thread's
  response pump survives callback misbehaviour, and that dispatching the
  per-request `running` callbacks tolerates requests being registered or
  retired while those callbacks execute.

### Modified Capabilities

None. `background-job-cancellation` already requires that a cancelled job
request notifies its requester, and `async-callback-coalescing` already fixes
the return contract of `monitor()`. The defects found here are violations of
those existing requirements, not changes to them.

## Impact

- `src/scantpaper/basethread.py`: `_execute_callbacks_for_stage`,
  `_execute_single_callback`, `_on_readable`, `_drain_one`, `_tick`.
- `src/scantpaper/tests/test_083_basethread.py`: new regression tests.
- `src/scantpaper/tests/test_0821_frontend_image_sane.py`: the failing test
  becomes deterministic once the pump is not sensitive to timing; it is
  retained as the end-to-end cancel scenario.
- No dependency, API, packaging, or configuration changes.

## Out of Scope

- The coverage-gate failure reported by the same autopkgtest run. It was
  reproduced locally and is caused by the build chroot lacking the
  `de_DE.utf8` locale, which skips 24 tests and drops coverage from 99.29%
  to 98.64%. It is unrelated to this change and is being handled
  separately.
- Making `test_user_cancel_terminates_session` itself deterministic. It
  exercises a real race between GLib dispatch sources and is left as an
  end-to-end scenario; the new unit tests carry the invariant.
