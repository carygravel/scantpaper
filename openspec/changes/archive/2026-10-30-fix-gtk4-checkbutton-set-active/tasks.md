# Tasks

## 1. Scan dialog postprocessing controls

- [x] 1.1 Replace the five `set_active(is_active=...)` calls in
  `scan_menu_item_mixins.py` (alternate rotation, image clean-up enabled,
  clean-up tool missing, user-defined tool enabled, empty tool list) with
  positional `set_active(...)`; verify new real-widget cases in
  `test_scan_menu_item_mixins.py` cover each state, fail with `TypeError`
  before the change, and pass after it.
- [x] 1.2 Replace the `set_active(is_active=False)` call in
  `edit_menu_mixins.py:_set_scan_udt_sensitivity` with a positional call;
  verify a new real-widget case in `test_edit_menu_mixins.py` applies
  Preferences with an empty tool list and leaves the control insensitive and
  inactive.

## 2. Shared scan-option setter

- [x] 2.1 Replace the `set_active(is_active=val)` call in
  `dialog/scan.py:_set_checkbutton_active` with a positional call; verify new
  real-widget cases in `test_dialog_scan.py` set both a `Gtk.CheckButton` and
  a `Gtk.Switch` without error.

## 3. Existing assertions and documentation

- [x] 3.1 Update the existing mock assertions that expect `is_active=` to
  expect the positional call in `test_scan_menu_item_mixins.py`,
  `test_edit_menu_mixins.py`, `test_dialog_scan.py` and
  `test_06099_dialog_scan.py`; verify those four modules pass.
- [x] 3.2 Add a `changelog.md` entry stating that the scan dialog opens with
  saved postprocessing settings (alternate rotation, image clean-up,
  user-defined tool, and an empty tool list), and that applying Preferences
  with no tools no longer breaks it; verify the entry names the affected
  states. No `README.md` change is needed because no feature or setting is
  added or changed.

## 4. Integration checks

- [x] 4.1 Run `pytest` and verify the full suite passes with no drop in line
  or branch coverage.
- [x] 4.2 Run `ruff format --check .`, `ruff check .` and `ty check .` and
  verify each reports no diagnostics.
- [x] 4.3 Run `openspec validate fix-gtk4-checkbutton-set-active --strict`
  and verify it passes.

## Workflow follow-up

- Archive the change with `/opsx-archive-change` after review, which creates
  the `scan-dialog-initialization` capability in the main specs.
