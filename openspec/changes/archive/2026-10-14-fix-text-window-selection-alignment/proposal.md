# Fix Text-Window Selection Alignment

## Why

In split view (Picture Window beside Text Window), the selection rectangle drawn
in the Text Window drifts out of alignment with the Picture Window, and the
misalignment grows as the zoom level changes. OCR text boxes stay put; only the
selection rectangle moves.

## What Changes

- Make the Canvas widget apply the same image-to-widget transform as the
  `ImageView`: the selection rectangle and the OCR bounding boxes SHALL sit at
  the same widget position as the Picture Window at every zoom level, pan
  offset, and non-square resolution, on HiDPI displays.
- Concretely, the Canvas SHALL scale the pan offset by the zoom level (fixing
  the zoom-dependent drift) and SHALL apply the `ImageView`'s resolution ratio
  and display scale factor (fixing the constant misalignment on non-square
  resolutions and HiDPI displays).
- Add tests that assert exact rendered widget coordinates (matching
  `to_widget_coords`), not merely that a rubberband/box is drawn.
- The `ImageView` is already correct; only the Canvas renderer and its
  coordinate conversions change.

## Impact

- `src/scantpaper/canvas.py` — `_draw_selection_rubberband`, `_draw_scene`,
  `_to_image_distance`, `_widget_to_image_rect`, `_set_zoom_with_center`,
  `_scroll`, and `_motion` must incorporate the resolution ratio and display
  scale factor. The Canvas also needs a `resolution_ratio` value (bound from
  the `ImageView`, like `zoom`/`offset`/`selection`).
- `src/scantpaper/session_mixins.py` — bind the Canvas `resolution_ratio` to the
  view's, alongside the existing zoom/offset/selection bindings.
- `src/scantpaper/tests/test_7_canvas.py` — extend the selection/bbox rendering
  tests to assert exact coordinates for non-zero zoom, non-zero offset,
  non-1 resolution ratio, and non-1 scale factor.
- No dependency changes; the `ImageView` is untouched.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `canvas-widget`: the Canvas SHALL render the selection rectangle and OCR
  bounding boxes with the same image-to-widget transform as the `ImageView`,
  scaling the pan offset by zoom and applying the resolution ratio and display
  scale factor, so they stay aligned with the Picture Window at any zoom,
  offset, resolution, and display scale.
