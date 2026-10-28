# Proposal

## Why

The OCR dialog grows when the user opens **Advanced Tesseract engine
parameters**, but collapsing that expander leaves the dialog at the expanded
height. The leftover height is then claimed by the **Page Range** frame, which
stretches and spreads its radio buttons apart, so the dialog looks broken after
a normal open/close cycle. The same frame stretching appears whenever a dialog
containing the page-range selector is enlarged by hand.

## What Changes

- The OCR dialog returns to the height it had before the advanced expander was
  opened when the expander is collapsed. The dialog keeps the width it
  currently has, including a width the user set manually.
- The page-range selector no longer claims surplus vertical space. Its frame
  stays at its natural height in every dialog, instead of growing to absorb
  extra window height.
- The scan dialog is not resized by this change: its OCR controls live in a
  scrolled window and it keeps its own persisted user-set size.
- Add regression tests for the dialog height and for the page-range selector
  not expanding.
- Add a changelog entry for the fix.

No **BREAKING** changes: the OCR options, page-range values, settings, and
session format are unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `dialog-layout`: a dialog whose optional content collapses returns to its
  pre-expansion height, and the page-range frame keeps its natural height
  instead of absorbing surplus window height.

## Impact

- `src/scantpaper/pagerange.py`: stop the radio buttons from requesting
  vertical expansion.
- `src/scantpaper/tools_menu_mixins.py`: make the OCR dialog fit its
  pre-expansion height when the advanced expander collapses.
- `src/scantpaper/postprocess_controls.py`: expose the advanced expander to the
  dialog (only where the Tesseract controls exist) so the dialog can observe
  its collapse without reaching into a private attribute.
- Tests covering the page-range selector, the OCR dialog wiring, and the
  height restoration.
- `changelog.md`.

No new dependencies; no settings, CLI, or file-format changes.
