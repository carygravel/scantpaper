# Proposal

## Why

The Debian autopkgtest `test-suite` fails on armhf after the
`python3-hypothesis` 6.170.15 update triggered a rerun: only
`test_1111_save_pdf.py::test_cancel_save_pdf` fails, with
`finished_callback` invoked on a `FINISHED` response even though `cancel()`
was called. The cause is a scheduling race, not hypothesis itself: `cancel()`
is cooperative and `do_save_pdf()` only samples the flag inside
`_assemble_pdf()`'s per-page loop. A save that has moved past page assembly
into the ocrmypdf text-layer embed, JBIG2, or finalize phases never checks the
flag again, so it silently runs to completion and reports `FINISHED`. On armhf
the worker is scheduled past `_assemble_pdf()` before `cancel()` sets the
flag, so the cancel is ignored; amd64 wins the race and the test passes.

This violates the `background-job-cancellation` contract: a running save must
be stopped as soon as practical, must not be presented as completed, and an
interrupted job must report `CANCELLED`-not `FINISHED` or `ERROR`.

## What Changes

- Add `check_cancelled()` breakpoints to `SaveThread.do_save_pdf()` at each
  phase boundary: after page assembly, after the ocrmypdf text-layer embed,
  after the best-effort JBIG2 pass, and before finalization/committing the
  saved state. A cancel that lands at any point now stops the save at the next
  breakpoint instead of letting it finish.
- Have `BaseThread.handler_wrapper()` report a handler that raised
  `CancelledError` as `CANCELLED` (the request's cancelled callback) instead
  of `ERROR`, matching the existing `background-job-cancellation` requirement
  that a cancelled request SHALL NOT also complete as finished or error, and
  avoiding a spurious error dialog in the GUI on cancel.
- Keep the existing end-to-end `test_cancel_save_pdf` as-is; with the
  breakpoints in place the race window shrinks to "the whole multi-second
  save completes before `cancel()` runs", which cannot happen, so the test
  passes deterministically.
- Add unit tests: `handler_wrapper` maps `CancelledError` to a `CANCELLED`
  response, and `do_save_pdf()` raises `CancelledError` when `cancel` lands
  during the text-layer embed. Move `CancelledError` into `basethread.py`
  (re-exported from `importthread.py`) so `handler_wrapper` can catch it
  without a circular import.

## Capabilities

### Modified Capabilities

- `background-job-cancellation`: A PDF save is stopped at whichever phase the
  cancel lands, not only while pages are being assembled, and an interrupted
  running job notifies its requester with `CANCELLED` rather than `ERROR`.

## Impact

- `scantpaper/basethread.py` — `CancelledError` defined here;
  `handler_wrapper()` reports it as `CANCELLED`.
- `scantpaper/importthread.py` — re-exports `CancelledError`; no behaviour
  change.
- `scantpaper/savethread.py` — `do_save_pdf()` cancellation breakpoints.
- Tests: `tests/test_083_basethread.py`,
  `tests/test_savethread.py`; existing
  `tests/test_1111_save_pdf.py::test_cancel_save_pdf` kept.
