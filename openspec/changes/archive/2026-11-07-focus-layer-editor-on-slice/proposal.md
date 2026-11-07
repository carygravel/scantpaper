# Proposal

## Why

Clicking a text or annotation slice shows its text in the editing control, but
does not move keyboard focus there. Focus normally remains on the page list, so
pressing Delete deletes the page instead of editing the OCR text. The user then
has to undo the page deletion before correcting the text, which makes the most
common correction workflow risky and slow.

This is a focus gap, not a shortcut-mapping gap: the shortcut scoping added
previously already lets Delete edit text once the text control has focus.

## What Changes

- Focusing a slice by clicking it, using the first/previous/next/last
  navigation controls, adding or duplicating a slice, or accepting a correction
  that moves to the next slice SHALL move keyboard focus to that layer's text
  control.
- When the control takes focus for a slice, it SHALL select the slice's whole
  text. Delete therefore clears the incorrect OCR text immediately, typing
  replaces it, and clicking inside the control still positions the caret for
  character-level edits.
- Focusing the page list or another non-editing control SHALL continue to let
  Delete delete pages.
- Starting an edit with no slice focused SHALL NOT move focus into an empty
  control.
- The existing shortcut scoping for Ctrl+X/C/V/A/Z, Ctrl+Shift+Z, `+` and `-`
  is unchanged; this change makes the text control the focused editing context
  so that scoping applies during correction.

This is not a breaking change. Page deletion with Delete remains available
whenever the page list has focus.

## Capabilities

### New Capabilities

<!-- None. -->

### Modified Capabilities

- `layer-editing`: focusing a slice moves keyboard focus to its editing control
  and selects the slice text, so Delete edits the text instead of deleting the
  page.

## Impact

- `src/scantpaper/layer.py`: `LayerEditor.edit()` focuses the layer's text
  control and selects its text. The layer data model, commit path, and undo
  behavior are unchanged.
- `src/scantpaper/tests/test_layer.py`: cover focus and selection for the
  click, navigation, add, duplicate, and accept paths, and confirm that
  `edit(None)` does not steal focus.
- A live GUI check should confirm Delete edits text in both tabbed and split
  views, while Delete from the page list still deletes pages.
- `README.md`: note that focusing a slice puts the cursor in its text control.
- No new dependencies, database changes, or asynchronous workflow changes.
