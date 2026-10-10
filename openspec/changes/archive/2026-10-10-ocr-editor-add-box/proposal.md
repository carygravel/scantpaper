# OCR Editor Add Box

## Why

The "Add" control in the OCR editor places a new slice at the current image
selection, but this is undocumented and fails silently when nothing is
selected: the placement rectangle must be drawn on the Image tab first, and
there is no way to draw that rectangle in the Text layer pane itself. Users
cannot predict where a new slice will appear and get no feedback when the
control is unusable.

## What Changes

- The "Add" control is **ghosted (disabled)** whenever there is no selection,
  and shows a tooltip explaining that a rectangle must be drawn or selected
  before adding. This applies to both the text and annotation editors.
- A selection rectangle can be **drawn directly in the Text layer pane** (and
  the annotation pane) as well as on the Image tab. There is a **single shared
  selection** drawn from either pane - drawing in one pane replaces the
  selection shown in the other, and the Add control uses that same rectangle.
- Drawing a box in a layer pane feeds the resulting rectangle into the Add
  control path, so adding a slice no longer requires switching to the Image
  tab.

## Capabilities

### New Capabilities

- `layer-add-selection`: lets the user draw a selection rectangle in the layer
  pane (Text or Annotation) and governs when the Add control is available,
  with a single shared selection between the image view and the layer panes.

### Modified Capabilities

- `layer-editing`: adds requirements for the Add control's enabled state and
  for drawing a selection in the layer pane that is shared with the image
  view, extending the existing "Slices can be added and duplicated"
  requirement.

## Impact

- `src/scantpaper/layer.py` - store the Add button, drive its sensitive state
  and tooltip from the shared selection; allow a layer-pane rectangle to seed
  the Add path.
- `src/scantpaper/canvas.py` - add rectangle-drawing interaction to the layer
  canvas and report the resulting selection.
- `src/scantpaper/app_window.py` - propagate selection changes to the editors
  so the Add control state stays current.
- `src/scantpaper/session_mixins.py` - keep the two editors' Add state in sync
  with the shared selection.
- Tests in `src/scantpaper/tests/` (`test_layer.py`, `test_7_canvas.py`,
  `test_imageview.py`) and coverage thresholds in `pyproject.toml`.
- No new dependencies.
