# Proposal

## Why

Focusing a text slice zooms the view so the slice fills a fixed fraction of the
pane's limiting axis. That makes the rendered text size depend on the slice's
aspect ratio and the pane's aspect ratio rather than on whether the text is
comfortable to read: a narrow slice is shown much larger than a long one, and
the size changes when the pane is resized or the split view is used. The
confidence-sorted correction workflow, which jumps from slice to slice across
the page, makes that inconsistency most obvious, and there is no way to tune
the level to the reader or the screen.

## What Changes

- Replace the fixed fraction-of-the-pane rule (`ZOOM_CONTEXT_FACTOR`) with a
  legibility target: a focused slice is shown at a consistent on-screen text
  height, independent of the slice's aspect ratio and the pane's aspect ratio.
- Derive the target size from the height of the line containing the slice
  where that is available, measured across the line's rotation, so a word such
  as "I" and a word such as "man" on the same line are rendered at the same
  text size. Fall back to the slice's own height when no line box exists, as
  for a slice added by hand or an annotation note.
- Keep fitting as a bound: never zoom past what allows the focused slice, plus
  a small margin, to remain fully visible, so long words are not clipped on a
  narrow pane.
- Apply the same rule on every path that focuses a slice: clicking a word, the
  least-confident/first/previous/next/last navigation controls, and the
  automatic advance after accepting or deleting a slice.
- Make the level user-adjustable from a compact control in the text and
  annotation layer control bar, next to the navigation controls, rather than
  from the Preferences dialog. The adjustment applies live to the focused
  slice, so its effect is visible while the user tunes it.
- The adjustable level scales the stable target: 100% is the default text size,
  and a lower value trades text size for more surrounding context. The level is
  kept in `scantpaperrc` so it survives a restart, and a reset restores the
  default.
- **Behaviour change:** users will generally see a less extreme zoom level when
  focusing a slice. The current destinations are too close for the
  confidence-sorted workflow; a stable text size is the intended improvement,
  and the new control lets users tune it further.

## Capabilities

### New Capabilities

- `slice-focus-zoom`: governs how the view zooms and centres when a text
  slice is focused, so the focused text is consistently legible and remains
  fully visible across every focus path and pane shape, and lets the user
  adjust the focus level in context.

### Modified Capabilities

None. `layer-editing` continues to own which slice is focused and what the
control displays; this change only changes the view state applied when a slice
is focused.

## Impact

- `src/scantpaper/layer.py`: `LayerEditor.edit` no longer scales the slice-fit
  zoom by a constant; it requests focus zoom for the slice under the new rule.
  `LayerControls` gains the compact focus-level control and its signal.
- `src/scantpaper/imageview.py`: a focus-zoom helper (or an extension of
  `zoom_to_box`) combining the legibility target, the adjustable level, the fit
  bound and centring.
- `src/scantpaper/canvas.py`: the focused slice's containing line box is made
  available for the target-height calculation where present.
- `src/scantpaper/const.py`: `ZOOM_CONTEXT_FACTOR` is replaced by the target
  text height and context-margin constants. The default focus level lives with
  the config defaults.
- `src/scantpaper/config.py`: a new default entry for the focus level, loaded
  and written through the existing `scantpaperrc` handling. No config-loading
  behaviour changes; the generic type normalisation already covers it.
- `src/scantpaper/session_mixins.py`: the editor and control are wired to the
  setting so a change applies immediately and is persisted on the next write.
- Tests: `src/scantpaper/tests/test_layer.py` covers each focus path and the
  control's live adjustment, and `src/scantpaper/tests/test_imageview.py`
  covers the zoom being independent of slice and pane aspect ratios.
- `README.md`: the layer-editing paragraph describes the focus zoom and the
  control; the Preferences description is unchanged.
- New translatable strings for the control label, tooltip and reset action.
- No dependency, database or migration changes.
