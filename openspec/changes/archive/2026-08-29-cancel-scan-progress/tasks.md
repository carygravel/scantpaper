## 1. Basethread CANCELLED protocol (D1)

- [x] 1.1 Add `"cancelled"` to `CALLBACKS` in `basethread.py` and a `Request.cancelled()` method that emits a `ResponseType.CANCELLED` response; verify by extending `test_083_basethread.py` with a test that a CANCELLED response fires a `cancelled_callback`, suppresses `finished_callback`, and removes the request from the callback registry
- [x] 1.2 Add `BaseThread.drain_cancelled_requests()` that emits `request.cancelled()` for each queued request it removes; verify with a test in `test_083_basethread.py` that drained requests invoke their `cancelled_callback` and leave no entry in `self.callbacks`
- [x] 1.3 Switch `Document.cancel()` (`basedocument.py`) to drain the response queue first, then the request queue via the new helper, keeping the `thread.cancel = True` flag and PID-kill loop intact; verify `test_basedocument.py` cancel tests (`test_cancel`, `test_cancel_empty_queues`, `test_cancel_with_pid_1`) still pass

## 2. SaneThread direct device cancel (D3 / A)

- [x] 2.1 Add `_scan_active` and `_cancel_requested` booleans to `SaneThread`, set `_scan_active` in `do_scan_page` immediately before `snap()` (cleared in a `finally`) and reset `_cancel_requested` at the start of each page
- [x] 2.2 In `SaneThread.cancel()`, after draining queued requests, call `self.device_handle.cancel()` directly on the caller's thread when `_scan_active` is true, set `_cancel_requested`, then send the `"cancel"` request as today; verify `test_8_cancel_empties_queue` still passes and existing `FakeBrscan5Device.cancel_calls` counts (batch-end / cancel-between-pages) are unchanged
- [x] 2.3 Extend `FakeBrscan5Device` in `test_0821_frontend_image_sane.py` so a `cancel()` while `snap()` is blocked aborts the transfer (raising from `snap()`), and rewrite `test_user_cancel_terminates_session` to cancel while the transfer is genuinely in flight; verify the partial page is not added and the session terminates
- [x] 2.4 Re-enable the FIXME'd test in `test_0821_frontend_image_sane.py:249`: `cancel()` on a queued `get_options` fires `cancelled_callback` and does not run `finished_callback`; verify the W0511 warning is gone (run `pylint` on the test file)

## 3. Cancellation classification (D4 / B)

- [x] 3.1 In `SaneThread.handler_wrapper`, when a `scan_page` handler fails and `_cancel_requested` is set, call `request.cancelled()` instead of `request.error(None, str(err))` and skip the repair `self.cancel()`; verify with a test in `test_0821_frontend_image_sane.py` that a device aborting during `snap()` yields a CANCELLED outcome with no error response
- [x] 3.2 Confirm a cancelled page never runs `new_page_callback`; verify the existing `test_user_cancel_terminates_session` assertion `pages == [1]`-style checks cover the interrupted first page

## 4. Batch termination routing (D5 / B)

- [x] 4.1 Thread a per-page `cancelled_callback` through `scan_pages` and `_scan_pages_finished_callback` (`image_sane.py`) for each queued `scan_page` request
- [x] 4.2 Implement the batch-terminal cancelled path: no page-count increment, terminate the session, and invoke the caller's `finished_callback` so `dialog/sane.py` emits `finished-process` (progress bar hidden, cursor reset) rather than `process-error`; verify in `test_06182_dialog_scan_sane.py` that cancelling mid-batch emits `finished-process` and emits no `process-error`
- [x] 4.3 Verify the device is reusable after a cancel: in `test_06182_dialog_scan_sane.py`, scan a second batch after a cancel and assert pages are acquired; ensure `_cancel_requested` was reset for the new batch

## 5. Full verification

- [x] 5.1 Run the full test suite (`pytest`) and confirm all tests pass with coverage at or above the configured threshold
- [x] 5.2 Run `black` and `pylint`; confirm the code is formatted and the number of `pylint` warnings is no greater than before the change