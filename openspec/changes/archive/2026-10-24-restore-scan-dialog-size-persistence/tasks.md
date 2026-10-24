# Tasks

## 1. Capture the size when the scan dialog closes

- [x] 1.1 Add a `hide()` override to `Scan` in
      `src/scantpaper/dialog/scan.py` that records
      `self._last_window_size = (self.get_width(), self.get_height())` before
      calling `super().hide()`, and declare the attribute (e.g.
      `_last_window_size: tuple[int, int] | None = None`) so the type checker
      accepts it. Verify `ty check .` reports no new diagnostics.
- [x] 1.2 Add a dialog test in `tests/test_dialog_scan.py` (using the
      `sane_scan_dialog` fixture) that mocks `get_width`/`get_height` on the
      dialog and asserts `hide()` records the mocked size on the dialog and
      still hides it. Verify the new test passes with `pytest`.

## 2. Persist the recorded size on quit

- [x] 2.1 Rework the scan-dialog branch of `_can_quit()` in
      `src/scantpaper/file_menu_mixins.py` to write
      `self._windows._last_window_size` when present, fall back to a live
      `get_width()/get_height()` read when absent, skip the write when either
      dimension is zero, and correct the stale GTK4 migration comment. Verify
      the existing `test_can_quit` still passes.
- [x] 2.2 Extend `tests/test_file_menu_mixins.py` with cases where (a) the
      mock window carries `_last_window_size = (200, 150)` and the settings
      take on those values, and (b) both the snapshot and the live read are
      zero and the previously saved value is kept. Verify both pass with
      `pytest`.

## 3. Restore-path coverage

- [x] 3.1 Add a test in `tests/test_scan_menu_item_mixins.py` asserting that
      `scan_dialog()` passes a saved `scan_window_width`/`scan_window_height`
      to `SaneScanDialog` as `default_width`/`default_height`, and omits both
      kwargs when the settings are unset. Verify the test passes with `pytest`.

## 4. Integration verification

- [x] 4.1 Run the full `pytest` suite plus `ruff format --check`, `ruff
      check`, and `ty check .`, and confirm the coverage line counts are
      unchanged and every command is clean.
