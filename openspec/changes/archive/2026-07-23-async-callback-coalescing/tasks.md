## 1. Core implementation

- [x] 1.1 Modify `BaseThread.monitor()` in `scantpaper/basethread.py` to process
  one response per call and chain via `GLib.idle_add(self.monitor)` when more
  responses remain

## 2. Tests

- [x] 2.1 Add test verifying `monitor()` processes exactly one response when the
  queue contains multiple responses
- [x] 2.2 Add test verifying `GLib.idle_add` is called when responses remain after
  processing one
- [x] 2.3 Add test verifying `monitor()` returns `GLib.SOURCE_CONTINUE` and fires
  running callbacks when the queue is empty (existing test — confirm it still passes)

## 3. Verification

- [x] 3.1 Run full test suite (`pytest`) and confirm all tests pass
- [x] 3.2 Run `black` formatter and `pylint` linter, confirm no regressions
