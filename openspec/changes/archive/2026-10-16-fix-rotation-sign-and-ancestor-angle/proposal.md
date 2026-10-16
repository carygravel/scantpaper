## Why

The 90-degree rotate controls added in
`2026-10-14-manually-rotate-ocr-boxes` turn a slice's glyphs in the opposite
direction to their labels, and the ancestor-rotation angle is not composed
correctly. Both were left to empirical verification by that change's design;
the first check came back inverted and the second is a real defect.

## What Changes

- **Rotation direction.** Swap the sign applied by the rotate-clockwise and
  rotate-anticlockwise controls so the glyphs turn the way the control is
  labelled. "Rotate text clockwise" SHALL visibly rotate the text clockwise.
  The shared draw formula and the persisted `textangle` values are unchanged;
  only the control handler's sign changes.
- **Ancestor-angle composition.** A rotation is currently computed from only
  the slice's *immediate* parent (`canvas.py` `add_box` fallback), because the
  accumulated-rotation list built in `_boxed_text` is never passed to
  `add_box`. As a result a slice below the first rotated level loses its
  ancestors' rotation (a page with `textangle 90` leaves its `para` at 0
  degrees), and the angle is applied twice when the focused slice is also the
  new slice's parent. The rendered angle of a slice SHALL be its own
  `textangle` plus the accumulated `textangle` of all its ancestors,
  regardless of nesting depth.
- **Inheriting a rotation when adding.** A slice added while a rotated slice is
  focused SHALL render at the same angle as the focused slice, without
  double-applying the angle of the box the new slice lands in.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `layer-editing`: the wording of the rotation requirement is corrected
  (clockwise now runs top-to-bottom), and a new requirement defines how a
  slice's own rotation composes with its ancestors' rotation and with the
  rotation inherited when a slice is added.

## Impact

- `src/scantpaper/layer.py` — sign in `rotate_clockwise` /
  `rotate_anticlockwise`, and the inherited-angle calculation in `add`.
- `src/scantpaper/canvas.py` — `add_box` transformation fallback, and removing
  the dead accumulated-rotation list in `_boxed_text` in favour of a single
  accumulated-ancestor-angle helper.
- `openspec/specs/layer-editing/spec.md` — corrected and new rotation
  requirements.
- Tests in `src/scantpaper/tests/test_layer.py` and
  `src/scantpaper/tests/test_7_canvas.py`.
- No data-format or dependency changes: `textangle` already exists in the
  layer schema, and the persisted values keep their existing meaning.
