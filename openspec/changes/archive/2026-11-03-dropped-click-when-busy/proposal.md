# Proposal

## Why

A deliberate click on a primary action can be silently discarded while the
application is busy. In the scan dialog the Scan button is made insensitive
while scan options are applied or reloaded — for example after choosing a page
size, or after any option that makes the scanner backend reload. GTK drops a
click whose press lands on an insensitive button, and also drops one whose
press was accepted but whose release arrives after the button became
insensitive. The user sees nothing happen and has to click again. The new
focus-level control shows the same user-visible failure from a different
cause: its popover can remain logically active after the layer control bar is
hidden, so the next click only closes an invisible popover.

Both reports have one root behaviour: a user action on an enabled control is
lost instead of being remembered or visibly refused. Fixing them separately
would leave the same trap for the next busy state.

## What Changes

- Treat an activation of a primary action that arrives while scan options are
  being applied or reloaded as a pending request: keep the control available
  to the pointer, remember at most one activation, and run it when the apply
  completes, instead of disabling the control and dropping the click.
- Do not use transient insensitivity as the busy indicator for the scan
  dialog's Scan action. Keep a visible busy state (wait cursor and progress
  reporting) that does not invalidate a press already in progress.
- Still refuse, rather than queue, a second scan while a scan is actually
  running, so a double click cannot start two scans.
- Pending actions are cleared when the dialog is closed or the work errors, so
  a stale click cannot fire during a later, unrelated operation.
- Make the focus-level control's popover start closed whenever its control bar
  is shown: pop it down before hiding the bar, so the first activation after a
  layer or tab switch always opens it.
- Keep the keyboard path equivalent: Enter on the scan dialog's default action
  behaves like a pointer click, including when options are being applied.
- Add regression coverage for the press-then-busy sequence, the queued scan,
  and the hidden-bar popover cases.

Not in scope: the standard light-dismiss behaviour where the first click
outside an open menu or popover closes it. That is expected platform
behaviour; this change is about clicks on an enabled primary action being
discarded by the application's own busy or show/hide handling.

## Capabilities

### New Capabilities

- `busy-action-handling`: how primary actions requested while background work
  is in flight are remembered, coalesced and executed, and when they are
  visibly refused instead.

### Modified Capabilities

- `slice-focus-zoom`: the in-context focus-level control must open on its
  first activation and must not keep an active popover while its control bar
  is hidden.

## Impact

- `src/scantpaper/dialog/scan.py`: `cursor` setter, `_do_scan`,
  `_set_option_profile`, `_complete_profile_setting`.
- `src/scantpaper/dialog/sane.py`: `_device_opening_started`,
  `_initialise_options`, `scan`, `_scan_finished_callback`.
- `src/scantpaper/dialog/__init__.py`: action and response wiring for actions
  that can be requested while busy.
- `src/scantpaper/layer.py`: `LayerControls._add_focus_zoom_control`,
  `LayerEditor.set_active`.
- `src/scantpaper/app_window.py`: `_update_layer_visibility`.
- Tests: `src/scantpaper/tests/test_dialog_scan.py`,
  `test_06198_dialog_scan_sane.py`, `test_0610_dialog_scan_sane.py`,
  `test_layer.py`, `test_text_layer_control.py`.
- No new dependencies and no changes to the session database or output files.
  If the final fix introduces a new visible busy string, regenerate the
  translation template with `dev/generate_pot.py` and mark new catalogue
  entries fuzzy.
