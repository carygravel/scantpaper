# Proposal

## Why

Dialog content sits flush against the window edges and adjacent widgets touch,
which is most visible in the dialogs opened from the **Tools** menu
(Threshold, Brightness / Contrast, Negate, Unsharp Mask, Crop, Clean up,
Split, OCR, User-defined): labels sit directly against their spin buttons and
rows are crammed together. The GTK3 code derived the content inset from the
active theme (`get_style_context().get_border(...)`, commented
`content-area-border`); the GTK3→GTK4 migration replaced that with a literal
`set_margins(widget, 0)`, and `Gtk.Box`'s default spacing is `0`, so both the
outer inset and the inner spacing were lost.

## What Changes

- Give every dialog's content area a consistent outer inset and vertical
  spacing between the blocks appended to it (the page-range frame and each
  option row).
- Give the rows of widgets inside dialogs a consistent horizontal spacing, so
  a label, its control, and its unit no longer touch.
- Apply both through the shared `Dialog` base class so every dialog (Tools,
  scan, save, preferences, crop, unpaper, OCR) is laid out consistently and
  the fix does not drift across nine copies.
- Introduce the two padding values as shared constants so both layers and
  their tests read from one source of truth.

## Capabilities

### New Capabilities
- `dialog-layout`: how a dialog presents its content — a consistent outer
  inset around the content area and consistent spacing between and within the
  rows of widgets a dialog appends.

### Modified Capabilities
<!-- None: dialog-buttons covers button labels/mnemonics only, and the
     scan-dialog-size-persistence requirements (remember/record/restore the
     dialog size) are unaffected by adding content padding. -->

## Impact

- `src/scantpaper/dialog/__init__.py` — `Dialog` base sets the content-area
  inset and spacing.
- `src/scantpaper/tools_menu_mixins.py`, `src/scantpaper/dialog/crop.py`,
  `src/scantpaper/unpaper.py`, `src/scantpaper/postprocess_controls.py` — row
  boxes get spacing.
- `src/scantpaper/const.py` — new shared padding constants.
- Tests (`test_05_dialog.py` and the tool/scan dialog tests) and `README.md`.
