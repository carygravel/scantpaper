# cancel-scan-progress

## Why

The scan progress bar's Cancel button is connected — `cancel_scan` → `SaneThread.cancel()` (`scan_menu_item_mixins.py:74`) — but it cannot stop an in-flight page transfer. `SaneThread.cancel()` drains the request queue and then queues a `"cancel"` request, which the single worker thread can only process *after* its blocking `snap()` returns. On real hardware the current page runs to completion and is added to the document, violating the existing `sane-page-acquisition` requirement that a user cancel terminate the session promptly without importing the partial page. Yesterday's cancel-progress-jobs change explicitly scoped SANE cancellation out as a non-goal under the assumption that it was "already implemented via the device handle"; that assumption is wrong for a transfer already in progress.

The adjacent W0511 FIXME at `test_0821_frontend_image_sane.py:249` points at a second, related gap: `ResponseType.CANCELLED` is declared (`basethread.py:30`) but never emitted, so queued jobs dropped by a cancel are orphaned — no `finished`, no `cancelled`, no `error`, and their callback entries leak in `self.callbacks`.

## What Changes

- **Interrupt an in-flight SANE transfer (A):** `SaneThread.cancel()` calls `device_handle.cancel()` directly on the caller's (UI) thread while a page transfer is running — guarded by an in-scan state flag — so the worker's blocked `snap()` aborts promptly, instead of only sending a `"cancel"` request that the busy worker cannot process.
- **Treat cancellation as cancellation, not error (B):** when `snap()` returns a SANE_STATUS_CANCELLED outcome after a deliberate cancel, the request is completed as cancelled rather than failed: the partial page is not imported, no generic error dialog is shown, and the scan batch/session terminates with the device left usable for the next batch.
- **Implement the CANCELLED response protocol (C):** `Request.cancelled()`, a `cancelled` stage in the callback machinery (`CALLBACKS`, `send()`), and firing `cancelled_callback` for requests dropped by a cancel, removing them from the thread's callback registry. This resolves the W0511 FIXME and ends the silent orphan/leak for cancelled queued work.

## Capabilities

### New Capabilities
- *(none)*

### Modified Capabilities
- `sane-page-acquisition`: the user-cancel behavior is brought into conformance — an in-flight transfer is interrupted promptly, the partial page is not added, pages queued behind the running scan are dropped, and a deliberate cancel does not surface a generic error dialog; the device session ends in a reusable state.
- `background-job-cancellation`: a job dropped by a cancel notifies its requester via a cancelled response instead of being silently discarded, and cancelled jobs are cleaned out of the background thread's callback registry.

## Impact

- `scantpaper/frontend/image_sane.py` — `cancel()`, `do_scan_page`/`do_cancel`, a scanning state flag, and CANCELLED handling in `handler_wrapper` decode the SANE_STATUS_CANCELLED outcome.
- `scantpaper/basethread.py` — `Request.cancelled()`, `cancelled` added to `CALLBACKS`/`send()`, CANCELLED responses processed as terminal in `monitor`/`_monitor_response` (the `cancelled` terminal branch already exists). Shared with DocThread/SaveThread/ImportThread: behavior for non-scan threads is unchanged (they use the "cancel request + `finished_callback`" pattern).
- `scantpaper/dialog/scan.py`, `scantpaper/dialog/sane.py` — scan-dialog error/cancel routing (no error dialog on deliberate cancel); `cancel_scan` unchanged externally.
- `scantpaper/scan_menu_item_mixins.py`, `scantpaper/session_mixins.py`, `scantpaper/app_window.py` — how a cancelled scan batch is signalled (`finished-process` vs `process-error`) and the scan progress bar's cancel connection lifecycle.
- Tests: `tests/test_0821_frontend_image_sane.py` (re-enable the FIXME'd test; extend `FakeBrscan5Device` to model an interrupted transfer), `tests/test_083_basethread.py` (terminal-state matrix extended with CANCELLED), `tests/test_06182_dialog_scan_sane.py` (cancel_scan now terminates the in-flight page), `tests/test_06098_dialog_scan.py`.
- No new dependencies; python-sane's `cancel()` maps to SANE's `sane_cancel`, which is specified to be callable from a thread other than the one blocked in a transfer.