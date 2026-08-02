## Why

When the default scanner is powered off at application start, the scan progress bar pulses and stays visible even after the user dismisses the "Error opening the last device used." dialog (e.g. selecting "Just ignore the error"). The bar is left stuck on screen showing "Opening device", which is confusing and makes the app look hung.

The root cause is a re-entrancy bug: the error dialog's modal loop keeps the device-open request registered as "running", so the thread's periodic tick keeps firing progress callbacks that re-show and re-pulse the bar that was just hidden. The "ignore" path then never hides it again.

## What Changes

- **Progress bar is hidden on scanner errors and stays hidden**: selecting "ignore" in the device-open error dialog leaves the progress bar hidden; it is not re-shown or re-pulsed while the modal dialog is displayed
- **Running callbacks are suppressed once a process reaches a terminal state**: the background thread stops invoking the `running_callback` of a request as soon as its error/finished/cancelled response is dispatched, so a modal dialog opened from within a terminal callback cannot keep the progress bar pulsing
- **Cancel-button signal on the progress bar is cleaned up**: the `_scan_progress` "clicked" connection is correctly disconnected on error, fixing the `signal=None` bug that leaked the handler across scan dialog opens
- **No changes to dialog options or messaging** — the radio choices ("Try again", "Rescan", "Restart", "Ignore") behave exactly as before

## Capabilities

### New Capabilities
- `progress-bar-lifecycle`: The main window's scan progress bar lifecycle — shown when a scan/device process starts, hidden when a process finishes, and hidden-and-stays-hidden when a process errors, including while a modal error dialog is open and after it is dismissed

### Modified Capabilities
- None

## Impact

- **`scantpaper/basethread.py`**: `_monitor_response()` will mark a request as no-longer-running before dispatching its terminal (error/finished/cancelled) callback, so the 200 ms tick cannot re-pulse during a nested modal loop
- **`scantpaper/app_window.py`**: `_process_error_callback()` will re-hide the progress bar after the modal dialog returns and correctly disconnect the cancel handler; the `signal` binding bug in the connect call is fixed
- **`scantpaper/scan_menu_item_mixins.py`**: the `signal` passed to `_process_error_callback` is bound correctly (the currently-passed value is always `None`)
- **`scantpaper/tests/test_083_basethread.py`**: new test that a running callback is not invoked after a request reaches a terminal state
- **`scantpaper/tests/test_app_window.py`**, **`scantpaper/tests/test_scan_menu_item_mixins.py`**: tests for the progress bar staying hidden through the error dialog and for the cancel signal disconnect
