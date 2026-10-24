# Tasks

## 1. Restore the device selector position

- [x] 1.1 In `Scan._add_device_combobox()` (`src/scantpaper/dialog/scan.py`),
  place the device row `hboxd` as the first child of the dialog content
  area (replace `self.get_content_area().append(self.hboxd)` with
  `self.get_content_area().prepend(self.hboxd)`), and verify by launching
  the app (`PYTHONPATH=src python3 -m scantpaper.app`) that the Device
  selector appears above the scan-options notebook.

## 2. Regression test and changelog

- [x] 2.1 Add a test to `src/scantpaper/tests/test_dialog_scan.py` that
  builds a `Scan` dialog and asserts the first child of its content area is
  the device row (`list(dialog.get_content_area().observe_children())[0]
  is dialog.hboxd`), and verify it passes with `pytest`.
- [x] 2.2 Add a changelog entry to the unreleased section of
  `changelog.md` describing the restored device selector position, and
  verify each line of the entry is wrapped at 80 columns.

## 3. Integration verification

- [x] 3.1 Run the full project gates — `pytest`, `ruff check`,
  `ruff format --check`, and `ty check .` — and verify they all pass with
  no new uncovered or partially covered lines.
