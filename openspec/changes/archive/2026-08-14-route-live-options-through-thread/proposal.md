## Why

`Options.val` is a redundant re-implementation of `SaneThread.do_get_option`
(`frontend/image_sane.py:107-110`) and `SaneDev.__getattr__`: its entire body is
`getattr(device_handle, name.replace("-", "_"))`. Worse, `dialog/scan.py` reaches
**directly into `self.thread.device_handle` from the GTK main thread** (e.g.
`options.val("tl-x", self.thread.device_handle)` at `dialog/scan.py:675-679`, and
bare `self.thread.device_handle.page_height` at `dialog/scan.py:884-906`). The
`SaneDev` lives in the `SaneThread` worker thread, so this bypasses the
request/response queue that exists precisely to keep device access off the main
thread — a latent SANE thread-safety bug. The `Options` descriptor snapshot is
sound; only the *live-value reads* are wired incorrectly.

## What Changes

- Add a **thread-safe synchronous `get_option` accessor** on `SaneThread` that
  sends a `get_option` request to the worker thread and blocks for the response,
  so the GTK thread never touches `SaneDev` directly.
- Replace every direct `self.thread.device_handle.*` / `getattr(self.thread.device_handle, ...)`
  read in `dialog/scan.py` with that accessor.
- **Delete `Options.val`.** Update `Options.flatbed_selected` to receive a value
  getter (callable) instead of a raw `device_handle`, and have callers pass the
  thread-safe accessor.
- Keep `Options` as the descriptor snapshot (its testability, thread-boundary,
  and stability roles are unchanged).

## Capabilities

This is a pure refactor: the values returned for every option are identical, only
the routing changes (main thread → worker via the existing queue instead of a
direct, unsafe `getattr`). No spec-level behavior changes.

## Impact

- `scantpaper/scanner/options.py` — remove `val`; `flatbed_selected` signature change.
- `scantpaper/dialog/scan.py` — live reads routed through the new accessor.
- `scantpaper/frontend/image_sane.py` — `SaneThread` gains the synchronous
  `get_option` helper (built on the existing `do_get_option`/`send`).
- Tests: `test_scanner_options.py`, `test_0608_dialog_scan.py` and the
  `test_06*/test_0610*` scan-dialog suites mock `device_handle` heavily; they must
  keep passing (call sites switch to the accessor / a getter callable).
