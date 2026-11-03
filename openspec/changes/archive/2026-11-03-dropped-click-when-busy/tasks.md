# Tasks

## 1. Scan action pending state

- [x] 1.1 Add a busy depth counter and a pending-activation flag to `Scan`,
  and make the `cursor` setter set only the cursor. Verify with a new unit
  test in `src/scantpaper/tests/test_dialog_scan.py` that setting the cursor
  to `wait` no longer makes `scan_button` insensitive.
- [x] 1.2 Increment the counter when an option apply or device open starts and
  decrement it on every success, error, and cancellation path. Verify with
  tests in `test_06198_dialog_scan_sane.py` and
  `test_0610_dialog_scan_sane.py` that the counter returns to zero after a
  clean apply and after an option error.
- [x] 1.3 Change `_do_scan` to queue one pending activation while the counter
  is positive and to start the scan through `GLib.idle_add` when the counter
  reaches zero, clearing the flag first. Verify with a test that activates
  Scan three times during one apply and asserts exactly one `scan()` call
  afterwards.
- [x] 1.4 Clear the pending activation on `hide()` and on option and
  device-open errors, and keep emitting `clicked-scan-button` on every
  accepted activation. Verify with tests for close-during-pending and
  error-during-pending, and assert the signal still fires.
- [x] 1.5 Set the Scan button's sensitivity explicitly: insensitive only
  while a scan runs or when no device is selected; sensitive while options
  are prepared. Verify with a test that the button is sensitive during a
  profile apply and insensitive once `scan()` starts.

## 2. Focus-level popover lifecycle

- [x] 2.1 Add `LayerControls.close_focus_zoom()` to pop the focus-level menu
  button down, and call it from `LayerEditor.set_active(active=False)` before
  hiding the control bar. Verify with a test in `test_layer.py` that the
  button's `active` state is false after hiding a bar whose popover is open.
- [x] 2.2 Verify the first activation after a bar is shown opens the popover
  again, with a test in `test_layer.py` or `test_text_layer_control.py` that
  hides and re-shows the bar and asserts a single activation leaves the menu
  button active.

## 3. Documentation

- [x] 3.1 Document in `README.md` that activating Scan while scan options are
  still being applied starts the scan when the apply finishes, instead of
  requiring a second click; verify the sentence appears in the scan-flow
  section.
- [x] 3.2 Add an entry under `## 4.0.3 (unreleased)` in `changelog.md`
  describing the queued Scan activation and the focus-level popover fix;
  verify the entry reads as user-visible behaviour, not implementation.

## 4. Verification and quality gates

- [x] 4.1 Run `ruff format` and `ruff check` with no new suppressions and
  verify both succeed.
- [x] 4.2 Run `ty check .` and verify it reports no diagnostics.
- [x] 4.3 Run the full `pytest` suite and verify it passes with coverage at
  or above the configured gate; then run
  `python3 dev/check_test_coverage.py` and verify no new uncovered lines.
- [x] 4.4 Run `openspec validate --specs --strict --no-interactive` and
  verify the change passes.
- [x] 4.5 On a scanner whose backend reloads options (for example a Brother
  model), change the paper size and click Scan once; verify the scan starts
  after the apply without a second click.
- [x] 4.6 Open the focus-level popover, switch to the other layer and back,
  and activate the control once; verify the popover opens on that first
  activation.

## Workflow follow-up

- Archive the change after review and implementation are complete.
- Run `openspec validate --archived --no-interactive` after archiving.
