# Proposal

## Why

The Pan, Select and Select & Pan tools are presented as global view
controls — on the main toolbar, in the View menu, in the image view's
context popover, and in README ("drag the image or canvas to pan the
view") — but the text-layer and annotation canvases ignore them. Both
canvases always behave like the combined tool: a primary press selects
(or focuses a word) and a middle drag pans, whichever tool is active.
Choosing Pan therefore cannot drag a layer pane, and the controls appear
broken whenever a layer is shown.

The image view is not consistent either: its Select tool starts a
rubber-band selection on a middle press, so the three tools do not
describe one button matrix across the two viewers.

This is how the canvases have behaved since before the GooCanvas
replacement, so it is not a GTK4 regression. It still contradicts the
documented tool contract and the expectation that the tool applies to
whichever pane the user is working in.

## What Changes

- Give the text-layer and annotation canvases the active tool, using the
  same view-to-canvas synchronisation already applied to zoom, offset,
  resolution ratio and selection.
- Apply one button matrix in both viewers:
  - **Pan**: a primary drag pans the view. The middle button does
    nothing. No selection starts and no slice is focused.
  - **Select**: a primary press focuses a word (canvas) or draws or
    adjusts a rubber band (image view). The middle button does nothing.
  - **Select & Pan**: a primary press focuses a word or draws a rubber
    band; a middle drag pans.
  - The secondary button keeps its current role: the image view's context
    menu, and nothing in the canvases.
- Make the middle button meaningful only for Select & Pan, so it has one
  meaning across the tools. The image view currently pans on a middle
  press with Pan and starts a selection with Select, so both are
  deliberate behaviour changes; Select & Pan remains the default and
  still pans.
- Keep scroll-wheel zoom unchanged in every tool and in both viewers.
- Show the matching pointer cursor on the canvases: grab/grabbing while
  panning with the Pan tool and a crosshair while selecting, matching the
  feedback the image view already gives.
- Update README's View Menu tool descriptions and the layer-editing
  instructions so the tool's scope and the button matrix are stated once.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `canvas-widget`: canvas button handling SHALL follow the active viewer
  tool instead of always selecting with the primary button and panning
  with the middle button. The primary-press focus and selection-drawing
  requirements become conditional on the selecting tools, and
  middle-button panning becomes conditional on the Select & Pan tool.
- `image-view-tools`: only the Select & Pan tool SHALL act on a middle
  press; the Select and Pan tools SHALL ignore it, so the tool matrix is
  identical in the image view and the canvases.

## Impact

- `src/scantpaper/canvas.py`: route primary and middle presses by tool
  mode, reusing the existing pan and selection paths; add cursor
  feedback.
- `src/scantpaper/imageview.py`: expose the active tool mode for the
  canvases, and make the Select and Pan tools ignore the middle button.
- `src/scantpaper/session_mixins.py`: synchronise the tool mode to both
  canvases alongside the existing zoom/offset/resolution/selection
  bindings.
- `src/scantpaper/app_window.py`: keep the tool action and the initial
  configured tool as the single source of truth.
- `src/scantpaper/layer.py`: no editor logic change is expected; the
  canvas keeps emitting `selection-drawn` for the selecting tools.
- Tests: canvas tool-matrix and cursor tests, image-view Select and Pan
  middle-button tests, session-binding tests, and any test that relies
  on the old unconditional canvas mapping.
- `README.md`: the View Menu tool descriptions and the layer-editing
  instructions.
- No new dependencies; no session/database format, saved-format or
  configuration changes; no migration.
