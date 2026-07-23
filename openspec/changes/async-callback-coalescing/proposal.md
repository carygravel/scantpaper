## Why

`BaseThread.monitor()` drains the entire response queue in a single main-loop
iteration (`while not self.responses.empty()`). When a burst of responses
arrives (e.g., multi-page import), all callbacks fire synchronously, causing a
sustained GUI stall. The pipe-based dispatch eliminated polling overhead, but
the callback drain still blocks the main thread for the cumulative duration of
all queued callbacks.

## What Changes

- Modify `BaseThread.monitor()` to process **one response per call** instead of
  draining the queue in a loop
- Chain subsequent responses via `GLib.idle_add`, yielding to the GLib main loop
  between each callback so UI events (repaints, button presses, animations) are
  processed
- No changes to the pipe notification mechanism, request queue, or callback
  registration API

## Capabilities

### New Capabilities

- `async-callback-coalescing`: One-at-a-time response processing with
  `GLib.idle_add` chaining to prevent GUI stalls during response bursts

### Modified Capabilities

(none — this is an internal performance improvement, not a spec-level behavior
change)

## Impact

- **Code**: `scantpaper/basethread.py` — `monitor()` method
- **Tests**: `scantpaper/tests/test_083_basethread.py` — existing tests should
  continue to pass; may need a new test for the one-at-a-time behavior
- **Dependencies**: None — uses existing `GLib.idle_add` from PyGObject
- **Performance**: Slight throughput reduction for background work (responses
  processed one per main-loop iteration instead of all-at-once), but GUI
  responsiveness is maintained. The practical impact is negligible since
  callbacks are fast and the main loop runs at ~60fps
