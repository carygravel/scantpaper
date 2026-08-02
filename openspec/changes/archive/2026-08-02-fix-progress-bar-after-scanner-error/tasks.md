## 1. Basethread: suppress running callbacks at terminal dispatch

- [x] 1.1 In `scantpaper/basethread.py` `_monitor_response()`, determine the response stage and, for terminal stages (`finished`, `cancelled`, `error`), set `self.callbacks[uid]["started"] = False` *before* invoking `_execute_callbacks_for_stage()`, so the 200 ms tick and `monitor()`/`_drain_one()` cannot re-pulse a request whose terminal callback is being processed (e.g. while a modal dialog blocks inside the callback)
- [x] 1.2 Verify the existing basethread suite still passes (`pytest scantpaper/tests/test_083_basethread.py`)

## 2. Progress bar stays hidden through the error dialog

- [x] 2.1 In `scantpaper/app_window.py` `_process_error_callback()`, call `self._scan_progress.hide()` again after `dialog.run()`/`dialog.destroy()` returns and before dispatching on the response, so every dialog option (ignore/reopen/rescan/restart) leaves the bar hidden; confirm the "ignore" branch still just returns
- [x] 2.2 In `scantpaper/scan_menu_item_mixins.py` `scan_dialog()`, replace the `connect("process-error", self._process_error_callback, signal)` call with a closure that reads the enclosing `signal` variable at event time (set by `started_progress_callback` via `nonlocal`) and forwards it as the `signal` argument
- [x] 2.3 Confirm `_process_error_callback`'s existing `disconnect(signal)` now actually disconnects the progress bar's "clicked" handler on error

## 3. Tests

- [x] 3.1 Add a test in `scantpaper/tests/test_083_basethread.py` that, once a request reaches a terminal state (error/finished/cancelled), invoking the running stage no longer calls its `running_callback` (e.g. enqueue the terminal response, drain it, then call `_execute_callbacks_for_stage("running", None)` and assert no invocation)
- [x] 3.2 Add/extend a test in `scantpaper/tests/test_app_window.py` that the "ignore" path of `_process_error_callback` results in `_scan_progress.hide()` being called after the dialog returns, and that the bar is not re-shown
- [x] 3.3 Add/extend a test in `scantpaper/tests/test_scan_menu_item_mixins.py` that a `process-error` emitted after a `started-process` forwards the real signal id (the `started-progress` handler's `connect` return value) to `_process_error_callback`, and that a `process-error` without a prior `started-process` forwards `None`

## 4. Verification

- [x] 4.1 Run the full test suite with `pytest` and confirm all tests pass with coverage at or above the current threshold
- [x] 4.2 Format changed files with `black`
- [x] 4.3 Run `pylint` on the changed files and confirm the score is the same or better than before the change
