# Proposal

## Why

Opening the scan dialog can raise `TypeError: Gtk.CheckButton.set_active()
got an unexpected keyword argument 'is_active'` and leave the user with no
scan dialog at all. GTK4 made `Gtk.CheckButton` a direct `Gtk.Widget`
subclass instead of a `Gtk.ToggleButton`, so its setter parameter is
`setting`, not the GTK3-era `is_active`. The default configuration happens to
avoid every affected branch, which is why the regression has stayed hidden.

The same call shape also breaks applying Preferences with an empty
user-defined-tool list while the scan dialog exists.

## What Changes

- Call `set_active()` positionally wherever the target is a
  `Gtk.CheckButton`, in the scan dialog's postprocessing controls and in the
  Preferences apply path.
- Add real-widget regression tests for the saved settings that reach those
  branches: alternate rotation enabled, image clean-up enabled, the clean-up
  tool missing, user-defined tool enabled, and an empty user-defined tool
  list.
- Update the existing mock-based assertions that currently assert the broken
  `is_active=` keyword.

No user-facing setting, file format or default behaviour changes. The dialog
opens as it already does with the default configuration.

## Capabilities

### New Capabilities

- `scan-dialog-initialization`: how the scan dialog is constructed from
  saved settings, including the postprocessing controls whose state depends
  on those settings.

### Modified Capabilities

None. The fix restores the intended opening behaviour; no existing
requirement changes.

## Impact

- `src/scantpaper/scan_menu_item_mixins.py` — the alternate-rotation,
  clean-up and user-defined-tool controls built when the scan dialog opens.
- `src/scantpaper/edit_menu_mixins.py` — the same user-defined-tool control
  when Preferences are applied.
- `src/scantpaper/dialog/scan.py` — the shared check-button value setter,
  which also accepts a `Gtk.Switch`.
- `src/scantpaper/tests/test_scan_menu_item_mixins.py`,
  `test_edit_menu_mixins.py`, `test_dialog_scan.py` and
  `test_06099_dialog_scan.py` — mock assertions and new real-widget tests.
- No dependency, configuration or data-model changes.
