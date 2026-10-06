## Why

The alternating-rotation toggle for destructive flatbed book scans is only
available when a multi-page batch is configured, because parity currently
resets at the start of every scan job. Many flatbed scanners have no hardware
Advance button, so batch scanning is unusable: the batch would finish before
the user can flip the page, forcing them to scan one page at a time with a
mouse click per page. Those users cannot use alternating rotation at all
today, so they must rotate pages manually and re-run OCR afterwards.

## What Changes

- The alternating-rotation toggle becomes visible and effective for
  single-page flatbed scanning (manual one-page-at-a-time workflow), in
  addition to multi-page flatbed batches.
- In manual mode, parity is stateful across consecutive scans: each
  individually-started scan increments the parity counter instead of
  resetting it, so every second manual scan is rotated an extra 180 degrees.
- Parity in manual mode resets only when the user explicitly turns the
  alternating-rotation toggle off (turning it back on starts again at an odd
  page).
- Existing multi-page batch behaviour is unchanged: parity still resets to
  odd at the start of each batch, so a second book still begins with a front
  page.
- ADF and duplex behaviour remains unchanged.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `flatbed-alternating-rotation`: the toggle's binding requirement is
  relaxed to cover single-page flatbed scans (not only multi-page batches),
  and the parity-reset requirement gains a manual-mode rule where parity
  persists across scans until the toggle is explicitly turned off.

## Impact

- `src/scantpaper/scan_menu_item_mixins.py`: `_flatbed_batch_active`
  gating, `_alternating_rotation_active`, checkbox visibility callback, and
  the parity counter reset in `clicked_scan_button_cb`.
- `src/scantpaper/tests/test_scan_menu_item_mixins.py`: visibility, parity,
  and reset-semantics tests.
- `README.md` (book-scan FAQ) and `changelog.md` user documentation.
