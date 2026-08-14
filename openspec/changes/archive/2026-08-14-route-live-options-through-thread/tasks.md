## 1. Thread-safe synchronous accessor on SaneThread

- [x] 1.1 In `frontend/image_sane.py`, add worker method `do_get_option_blocking(self, request)` that reads `getattr(self.device_handle, request.args[0].replace("-", "_"))` **in the worker thread**, stores the result in `request.args[1]` (a list holder) and sets `request.args[2]` (a `threading.Event`). Leave the existing async `do_get_option` untouched.
- [x] 1.2 Add main-thread API `SaneThread.get_option_value(self, name, timeout=10)` (named to avoid shadowing the existing async `get_option`) that creates a holder list + `threading.Event`, calls `self.send("get_option_blocking", name, holder, event)`, blocks on `event.wait(timeout)`, re-raises any stored exception, and returns `holder[0]`; on timeout raises `TimeoutError` (fail fast, no hang).
- [x] 1.3 Confirm `do_get_option` / `do_get_option_blocking` use the same `name.replace("-", "_")` convention so callers keep passing hyphenated names.

## 2. Remove `Options.val` and decouple `flatbed_selected`

- [x] 2.1 In `scanner/options.py`, delete the `val` method.
- [x] 2.2 Change `flatbed_selected(self, device_handle)` to `flatbed_selected(self, get_value)` where `get_value` is a callable; replace `self.val(self.source.name, device_handle)` with `get_value(self.source.name)`. Keep all other logic (the `re.search` branches) unchanged.

## 3. Route `dialog/scan.py` live reads through the worker

- [x] 3.1 Replace `options.val("tl-x"|"tl-y"|"tr-x"|"br-x"|"br-y", self.thread.device_handle)` in `get_current_scan_area` (`scan.py:675-679`) and the resolutions loop (`scan.py:1345`) with `self.thread.get_option_value("<name>")`.
- [x] 3.2 Replace bare `self.thread.device_handle.page_height/.page_width/.tl_x/.tl_y/.br_x/.br_y` reads (`scan.py:884-906`) with `self.thread.get_option_value("page-height"|"page-width"|"tl-x"|"tl-y"|"br-x"|"br-y")`.
- [x] 3.3 Replace `getattr(self.thread.device_handle, opt.name.replace("-", "_"))` (`scan.py:751`, `1255`) with `self.thread.get_option_value(opt.name)`.
- [x] 3.4 Update `flatbed_selected` call sites (`scan.py:254`, `291`, `1392`) to pass `self.thread.get_option_value` instead of `self.thread.device_handle`.
- [x] 3.5 Route the remaining `self.thread.device_handle` value reads in `dialog/sane.py:206`/`523` and `dialog/pagecontrols.py:73`/`406` through `get_option_value` (placeholder `Options([])` stays).

## 4. Update tests

- [x] 4.1 Update `flatbed_selected` call sites in `test_0608_dialog_scan.py`, `test_0601_dialog_scan.py`, `test_06093_dialog_scan.py`, `test_06182_dialog_scan_sane.py` to pass `thread.get_option_value` (real `SaneThread`, so the worker-backed method runs) instead of a mock device handle.
- [x] 4.2 Confirmed `test_dialog_scan.py` / `test_06099_dialog_scan.py` mock `flatbed_selected` on the options object (no signature change needed) and `test_0621_dialog_scan_edit_save.py` passes `MockOptions` with its own `flatbed_selected(self, _handle)` override (still accepts the getter). No `Options.val` references remain.
- [x] 4.3 Confirm no test still imports or calls `Options.val` (grep clean).

## 5. Verify

- [x] 5.1 Run `pytest` (full suite) — 1036 passed, 1 xfailed, 3 xpassed; no hardware required.
- [x] 5.2 `black` clean on all changed files; `pylint` 8.64/10 with no new messages on changed lines (all reported items are pre-existing); coverage 99.06% (>= 98%, no regression).
