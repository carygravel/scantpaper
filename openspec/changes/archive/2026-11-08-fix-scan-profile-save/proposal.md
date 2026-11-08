# Proposal

## Why

On the GTK4 build, clicking the Save button in the scan dialog's **Scan
profiles** frame does nothing. `_save_profile_callback()` constructs the
naming dialog as `Gtk.Dialog(_("Name of scan profile"), ...)`, but GTK4's
PyGObject initialiser accepts properties only, so the call raises
`TypeError: GObject.__init__() takes exactly 0 arguments (1 given)` before the
dialog is shown. The exception is swallowed by the signal handler, so the user
sees no error, no profile is created, and the profile list can never be
populated. A first-time user concluded the feature was disabled.

The existing tests cannot catch this because they replace `Gtk.Dialog` with a
mock, so the real constructor is never exercised.

## What Changes

- Pass the dialog title as the `title=` property when building the profile
  naming dialog, so it opens the way the working Edit path already does.
- Add regression coverage that builds a real `Gtk.Dialog` and patches only the
  modal runner, so a constructor regression fails the test instead of being
  mocked away.
- Keep the rest of the flow unchanged: non-empty name validation, overwrite
  confirmation, the `added-profile` signal and config persistence.
- No data migration or configuration change is needed; profiles already stored
  in the config continue to load and apply.

## Capabilities

### New Capabilities

- `scan-profiles`: named, reusable sets of scan options that can be created
  from the current settings, selected in the scan dialog, edited, deleted and
  persisted across sessions. This change adds the contract for creating a
  profile from the current scan options.

### Modified Capabilities

None.

## Impact

- `src/scantpaper/dialog/scan.py` (`_save_profile_callback`).
- `src/scantpaper/tests/test_06099_dialog_scan.py` and
  `test_0621_dialog_scan_edit_save.py`, which currently mock the constructor.
- `changelog.md`.
- No dependency changes. No translation changes: the dialog title is an
  existing msgid.
