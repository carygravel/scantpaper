## Context

See proposal.md - Why. The relevant machinery:

- `scantpaper/basethread.py` dispatches worker-thread responses on the GLib main thread. `_tick` (200 ms timeout) and `monitor()`/`_drain_one()` invoke each active request's `running_callback` while `callbacks[uid]["started"]` is True. A request is only removed from `self.callbacks` *after* its terminal callback (error/finished/cancelled) returns — `_monitor_response()` calls `_execute_callbacks_for_stage()` first, then `del self.callbacks[uid]` (basethread.py:307-329).
- `scantpaper/app_window.py:841` `_process_error_callback()` handles `process-error`. For `open_device` it calls `self._scan_progress.hide()`, then blocks in a modal `Gtk.MessageDialog.run()`.
- `dialog.run()` runs a nested GLib main loop in the same main context, so `_tick`/IO-watch keep firing. With the request still flagged `started=True`, each tick emits `changed-progress` → `_changed_progress_callback` (scan_menu_item_mixins.py:370) → `_scan_progress.pulse()` **and `.show()`** — undoing the `hide()`.
- On "ignore" the callback returns without hiding the bar again; the request is then deleted, so the pulse stops but the bar is left visible.
- Secondary: `scan_dialog()` binds the `signal` argument of `_process_error_callback` at connect time while it is still `None` (scan_menu_item_mixins.py:73-86), so the cancel-button disconnect at app_window.py:845 never runs.

## Goals / Non-Goals

**Goals:**
- Stop running callbacks from firing once a request reaches a terminal state, so no modal dialog opened from a terminal callback can re-show or re-pulse the progress bar.
- Ensure the "ignore" path (and every dialog option) leaves the progress bar hidden.
- Fix the always-`None` `signal` so the progress bar's cancel connection is actually disconnected on error.

**Non-Goals:**
- Changing the error dialog's options, wording, or response semantics.
- Reworking the progress bar widget itself (`Progress`), the scan dialog, or the message-dialog system.
- Fixing the adjacent latent bug where `get_devices()` has no `error_callback`, so its in-dialog progress bar is never destroyed if the device list fetch raises. Noted in Risks; deliberately out of scope.

## Decisions

### D1: Suppress running callbacks for terminal-stage requests in `basethread`
In `_monitor_response()`, before dispatching the terminal callback, flip `self.callbacks[uid]["started"] = False` for stages `finished`, `cancelled`, and `error`. The subsequent `del self.callbacks[uid]` is unchanged.

- **Rationale:** Fixes the whole class of bugs at the source. Any modal dialog opened from *any* terminal callback (including `_show_message_dialog`'s `MultipleMessage.run()` and the libusb cache dialog, which is also reached from within a thread callback) can no longer be re-pulsed. Flipping the flag does not affect terminal dispatch because `_execute_stage_callbacks()` for terminal stages is not gated on `started`.
- **Alternative considered:** Hiding the bar in `_process_error_callback` only. Rejected: it patches one symptom; the libusb cache dialog in `_changed_device_list_callback` (reached from `get_devices`'s finished callback) would still pulse its own bar, and any future modal-in-callback would regress.

### D2: Re-hide the progress bar after the error dialog returns
In `_process_error_callback()`, call `self._scan_progress.hide()` again after `dialog.run()`/`dialog.destroy()`, before dispatching on the response. The "ignore" branch keeps the existing `return` (the comment "for ignore, we do nothing" becomes accurate again).

- **Rationale:** Defense in depth against future changes; also covers the reopen/rescan paths where `scan_dialog()` runs while the old request is still being cleaned up. The new dialog re-shows the bar via `started-process` when its own open begins, so hiding here does not produce a flash of wrongness.

### D3: Bind the cancel signal id at call time
Replace the direct `self._windows.connect("process-error", self._process_error_callback, signal)` with a closure that reads the enclosing `signal` variable when the event fires (it is set by `started_progress_callback` via `nonlocal`).

```python
def do_process_error(_widget, process, msg):
    self._process_error_callback(_widget, process, msg, signal)

self._windows.connect("process-error", do_process_error)
```

- **Rationale:** The `nonlocal` rebind cannot retroactively change `connect()`'s bound data; a closure over the same cell can. `disconnect()` is a no-op when the signal is still `None` (error before any `started-process`), which is correct.

## Risks / Trade-offs

- **Behavioral change in `basethread` affects all threads** (document, scan, import, save). Suppressing running callbacks at terminal dispatch could theoretically starve a UI element that expects running updates right up to completion. → Mitigation: the final `changed-progress`/DATA response still fires before the terminal callback; only the 200 ms tick between terminal-dispatch and cleanup is skipped, which is exactly the desired fix. Covered by the existing basethread test suite.
- **Nested-loop timing is hard to unit-test deterministically.** → Mitigation: test the observable invariant — after a request reaches a terminal state, invoking the running stage no longer calls its `running_callback`; plus an app_window-level test that the ignore path leaves the bar hidden.
- **`get_devices()` missing `error_callback`** is adjacent and remains: if `sane.get_devices()` raises, the in-dialog "Fetching list of devices" bar is never destroyed. → Out of scope for this change; D1 improves, but does not fully fix, that path.

## Migration Plan

No data or config migration. Both fixes are internal; behavior at the UI surface is the intended state (bar hidden after error). Rollback is a revert of the three touched files.

## Open Questions

None.
