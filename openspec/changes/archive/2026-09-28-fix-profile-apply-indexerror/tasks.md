## 1. Red failing test

- [x] 1.1 Write a regression test that applies a Brother-style scan profile
      via `set_profile` and drives the completion of `changed-current-scan-options`
      after `setting_profile` has been cleared, asserting no `IndexError` is
      raised and the apply leaves the dialog responsive.
- [x] 1.2 Run the new test and confirm it fails with the current code
      (`IndexError: list index out of range`), capturing the failing state.

## 2. Fix the crash

- [x] 2.1 Make `do_changed_current_scan_options` in
      `src/scantpaper/dialog/scan.py` guard against an empty `setting_profile`
      and consume the entry with `pop(0)` instead of indexing `[0]`.
- [x] 2.2 Run the new regression test and confirm it now passes.

## 3. Regression and quality gates

- [x] 3.1 Run the full `pytest` suite (including existing profile/scan-dialog
      tests) and confirm no regressions and no newly-uncovered lines.
- [x] 3.2 Run `ruff format` / `ruff check` and `ty check .` and confirm clean.
- [x] 3.3 Update README.md only if any user-visible behaviour changed (none
      expected — this is a crash fix).
