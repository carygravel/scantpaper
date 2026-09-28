## Why

Applying a scan profile on Brother (and other) scanners crashes with an
`IndexError: list index out of range` at `scan.py:1182` because
`do_changed_current_scan_options` indexes `self.setting_profile[0]` while the
stack is already empty. The log (`scanner_Brother`) shows it three times in a
single session; the dialog is left in an inconsistent "wait" state and the
profile name is not committed.

## What Changes

- Make profile-apply completion reentrancy-safe: `setting_profile` is read
  defensively and mutated with `pop`/`append` instead of assumed-non-empty
  indexing, so the finalize/emit path can no longer raise `IndexError`.
- Ensure a completed profile apply always leaves `_profile` set and the
  dialog cursor restored, even when finalization re-enters the
  `changed-current-scan-options` handler.
- Add a regression test that reproduces the exact profile-apply race
  (StopIteration finalize re-entering the handler with an empty
  `setting_profile`) and asserts no exception and a settled dialog.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scan-option-convergence`: Profile application must terminate without
  raising when completion re-enters the `changed-current-scan-options`
  handler. Adds a requirement (and scenario) that applying a profile never
  crashes with `IndexError` and always leaves the dialog usable and the
  profile committed.

## Impact

- `src/scantpaper/dialog/scan.py` — `do_changed_current_scan_options`
  (around line 1182) and the `setting_profile` stack handling; possibly
  `_complete_profile_setting`.
- `src/scantpaper/tests/` — new regression test for the profile-apply race;
  existing `test_0618*`/`test_06*_dialog_scan` profile tests may need
  updating to assert the settled-state invariant.
- No dependencies, config, or public API changes.
