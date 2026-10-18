## 1. Tests first (TDD)

- [x] 1.1 Dialog detection tests (`tests/test_0610_dialog_scan_sane.py`
  or a sibling): with `current_scan_options` requesting `("depth", 1)`,
  a delivered "L" frame emits "new-scan" with the mismatch flag set;
  a delivered "1" frame and an absent depth option emit it unset
- [x] 1.2 Post-process tests: an import carrying the flag converts the
  page to mode "1" via the threshold handler with the configured
  "threshold tool" value, and runs before rotate/OCR; imports without
  the flag are unchanged
- [x] 1.3 Notification tests: the mismatch logs a warning and surfaces
  the notice through the progress channel once per page without a
  modal dialog
- [x] 1.4 Signal-arity tests updated for the new "new-scan" argument
  (`tests/test_06199_dialog_scan_sane.py`)

## 2. Implementation

- [x] 2.1 `src/scantpaper/dialog/sane.py`: in `new_page_callback`,
  look up the requested depth in `current_scan_options` and compare it
  with the delivered image mode; emit the flag on "new-scan"
- [x] 2.2 `src/scantpaper/scan_menu_item_mixins.py`: map the flag to
  an import option in `_new_scan_callback`
- [x] 2.3 `src/scantpaper/document.py`: handle the option in
  `_post_process_scan` as the first step, calling the existing
  `threshold` handler with the configured "threshold tool" value
- [x] 2.4 Non-blocking notice: `logger.warning` plus the progress
  channel message when the mismatch is detected
- [x] 2.5 Run `pytest` and confirm the suite passes with coverage at
  or above the configured threshold

## 3. Documentation and gates

- [x] 3.1 Document the behaviour in `README.md` (scanning section) and
  add a `changelog.md` entry under 4.0.0 (unreleased); wrap at 80
  characters
- [x] 3.2 Run `ruff format`, `ruff check` and `ty check .` and resolve
  any diagnostics without suppressions
