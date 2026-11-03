# Proposal

## Why

The edit bar is the end child of the outer vertical `GtkPaned`. Its divider is
pinned to the bar's height only at first paint and when the pane's
`max-position` changes. Showing or hiding a layer's controls changes the
minimum height of content inside the always-visible `edit_hbox`, which does not
move the divider. The bar is then allocated below the bottom of the pane:
selecting the Text layer tab or entering a split view from the Image tab shows
the bar only after the window is resized. That is why a word can be focused,
zoomed, centred and selected while the edit bar still does not appear.
Returning to the Image tab then leaves an empty strip the height of the bar
that the view never regains.

Keeping the bar behind a divider also makes it user-resizable, but its size is
neither persisted nor honoured when the pane changes size, so an enlarged bar
snaps back on the next resize. The bar only ever needs its natural height, so
the divider adds failure modes without adding a supported feature.

## What Changes

- Replace the outer vertical `GtkPaned` that stacks the view above the edit bar
  with a vertical `GtkBox`: the view row expands and the edit bar takes only
  its natural height.
- **BREAKING (UI):** the edit bar is no longer user-resizable by dragging a
  divider. The view above it always receives all vertical space that the bar
  does not need.
- Showing and hiding the bar with its layer now takes effect immediately: the
  view gives up the bar's height when the bar appears and reclaims it when the
  bar is hidden, without a window resize or a divider adjustment.
- Remove the outer-pane startup pin and the `keep_at_minimum` handler, along
  with the `end_at_minimum` mode of the split-pane initialiser. Keep the inner
  horizontal/vertical split panes, their initial divider and their persisted
  positions unchanged.
- The scanner progress bar appearing or disappearing now only changes the
  space offered to the view row; the bar keeps its natural height without a
  separate re-pin.
- Update the README layer-editing description and record the change in the
  changelog: the bar has a fixed height and is not draggable.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `active-layer-selection`: control-bar visibility must mean the bar is laid
  out on screen. The bar SHALL appear as soon as its layer's canvas is shown
  (tab switch, View-menu selection or split view) and SHALL NOT reserve space
  while hidden.
- `view-layout`: the edit bar becomes a fixed-height row instead of the end
  child of a draggable pane. The requirement that the image area receives a
  usable share at startup is retained without an outer divider, and the
  outer-pane divider-position scenarios are removed. The inner split panes
  keep their initial divider and persisted positions.

## Impact

- `src/scantpaper/app.ui`: replace `GtkPaned id="vpaned"` with a vertical
  `GtkBox` holding the notebook and `edit_hbox`, with the notebook expanding.
- `src/scantpaper/app_window.py`: drop `_vpaned` and `_vpaned_initialised`;
  repack the view row in the box; simplify `_init_split_pane` by removing the
  `end_at_minimum` mode and `keep_at_minimum`; stop setting an outer divider.
- `src/scantpaper/tests/test_app_window.py`: remove the outer-pane pin tests
  and any test that moves `_vpaned`; add real-layout assertions that the bar
  is allocated inside the window after a layer is shown and that the view
  regains the height after it is hidden.
- `README.md` and `changelog.md`.
- No dependency, data-model or configuration changes.
