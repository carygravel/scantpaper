## Why

When a user draws a box around vertical text and adds a slice, the slice is
created with a text angle of zero, so the renderer fits the text across the
box's narrow *width* instead of its tall *height*; the glyphs shrink to
near-invisibility and the UI looks broken. The user already expressed the text
orientation when they drew a tall, narrow rectangle, but the editor ignores
that signal. Separately, a slice rotated by 180 degrees selects the same wrong
axis, so genuinely upside-down horizontal text is rendered tiny on any box that
is wider than it is tall.

## What Changes

- When a new slice is added (Add) or duplicated (Copy) and it inherits no
  rotation from an ancestor or focused slice, the editor SHALL guess the
  slice's text angle from the selection geometry together with the text that
  will be placed in it: keep the text upright when its ink fits the box
  upright, otherwise choose a 90-degree angle when the text fits the box only
  when rotated, otherwise choose the orientation that fits the text largest.
- The guess SHALL be expressed in the parent's frame, so a slice placed inside
  an already-rotated line inherits that rotation without the guess fighting it.
- A guessed angle is an ordinary text angle: it is persisted, drawn, serialised
  in hOCR, and remains correctable with the existing rotate controls.
- The same geometry-aware creation path SHALL apply when the first slice is
  created on a page that has no text layer.
- **Fix**: the text-fit scale SHALL select the box's width for angles 0 and
  180 degrees and the box's height for 90 and 270 degrees, so a 180-degree
  slice is rendered at the same legible size as an upright one.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `layer-editing`: Adding, duplicating, or seeding the first slice now derives
  the new slice's rotation from the selected rectangle and its text when no
  rotation is inherited.
- `canvas-widget`: The text-fit scale for a rotated slice uses the width axis
  for 180-degree text (and, generally, the height axis only for 90/270), so
  180-degree text is not shrunk.

## Impact

- `src/scantpaper/layer.py`: `LayerEditor.add`, `LayerEditor.copy`,
  `LayerEditor._new_layer_json` - angle selection.
- `src/scantpaper/canvas.py`: the fit-scale line in `_draw_bbox` (line ~915);
  a small text-measurement helper so the editor can compare the text's ink
  extent against the selection.
- Tests: `tests/test_layer.py`, `tests/test_text_layer_control.py`,
  `tests/test_7_canvas.py`, plus a save round-trip covering a 180-degree slice.
- No new dependency, no data-model change, no CLI or file-format change.
