## 1. Fix Save dialog signal wiring

- [x] 1.1 In `src/scantpaper/dialog/save.py`, change the "Specify" check button connection from `connect("activate", ...)` to `connect("toggled", self._clicked_specify_date_button, hboxe)` (line ~413). Optionally rename `_clicked_specify_date_button` to `_toggled_specify_date_button` and update its docstring to reflect toggled behavior; if renaming, update all call sites/tests.
- [x] 1.2 Verify that constructing `Save(select_datetime=True)` now shows the date entry field (entry widget becomes visible). The handler fires on `set_active(True)` when connected to `toggled`.
- [x] 1.3 Verify mouse clicks on "Specify" reveal the date entry; clicking "Now" hides it when "Specify" was active (group deactivation emits `toggled` on "Specify").

## 2. Fix Page Controls dialog signal wiring

- [x] 2.1 In `src/scantpaper/dialog/pagecontrols.py`, change `bscanall.connect("activate", self._do_clicked_scan_all, bscanall)` to connect to `"toggled"` instead of `"activate"`.
- [x] 2.2 In `src/scantpaper/dialog/pagecontrols.py`, change `self._bscannum.connect("activate", self._do_clicked_scan_number, spin_buttonn)` to connect to `"toggled"`.
- [x] 2.3 In `src/scantpaper/dialog/pagecontrols.py`, change `self.buttons.connect("activate", self._do_buttons_clicked)` to connect to `"toggled"`.

## 3. Update tests

- [x] 3.1 Update `src/scantpaper/tests/test_dialog_save.py::test_specify_widget_does_not_fire_on_programmatic_change` to match corrected semantics (programmatic state changes via `set_active()` when connected to `toggled` will fire the handler; the test should reflect the intended contract that the property/visibility track widget state).
- [x] 3.2 Add a regression test in `src/scantpaper/tests/test_dialog_save.py` verifying that constructing `Save(select_datetime=True)` makes the date entry visible (`_meta_datetime_widget.is_visible()` or equivalent). Also test that clicking "Specify" (emitting `toggled` or calling handler appropriately) reveals the entry.
- [x] 3.3 Run tests related to save dialog and page controls: `pytest src/scantpaper/tests/test_dialog_save.py src/scantpaper/tests/test_052_dialog_save.py -v`.
- [x] 3.4 Optionally run all tests to catch regressions: `pytest` (or the full test suite). Ensure all pass.

## 4. Verification

- [x] 4.1 Run `ruff format . && ruff check .` — no linting errors.
- [x] 4.2 Run `ty check .` — no type errors.
- [x] 4.3 Manually verify the Save dialog in the app context if desired (date entry appears when clicking "Specify").
