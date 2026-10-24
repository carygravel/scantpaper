# Proposal

## Why

The GTK3→GTK4 migration regressed the scan dialog layout: the Device
combobox, which was the first control at the top of the window under GTK3,
now renders at the bottom, below the scan-options notebook. An audit of the
migration (all 31 production files, every `pack_end` site) confirms this is
the only instance of the packing order regression in production code.

## What Changes

- Restore the scan dialog layout so the Device selector (label +
  combobox) is the first control in the dialog's content area, above the
  options notebook, matching the pre-migration GTK3 behaviour.
- Add a regression test asserting the Device row is the first child of the
  scan dialog's content area, so the layout contract is enforced.

No other dialogs or capabilities change; the audit verified the remaining
migration translations preserve GTK3 visual order.

## Capabilities

### New Capabilities

- `scan-device-selection`: behaviour of the scan dialog's device
  selector, starting with its placement as the first control in the
  dialog.

### Modified Capabilities

(empty)

## Impact

- `src/scantpaper/dialog/scan.py` — `Scan._add_device_combobox()` adds the
  device row to the dialog content area after the notebook that
  `PageControls.__init__` appends.
- `src/scantpaper/tests/test_dialog_scan.py` — new regression test.
- No dependencies, data model, or public API changes.
