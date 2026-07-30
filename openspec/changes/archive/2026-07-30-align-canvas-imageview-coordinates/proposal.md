## Why

Canvas and ImageView share zoom/offset via `GObject.bind_property(BIDIRECTIONAL)` but their Cairo transforms have opposite sign conventions for the offset. The same offset raw value means opposite things in each widget, causing Canvas to show the wrong portion of the image — resulting in a blank initial view. Additionally, Canvas centers the zoom about the widget center while ImageView does not, creating a second inconsistency.

## What Changes

- **Canvas `_draw_scene`**: Replace the translate-center/scale/translate-back/translate-offset formula with the same `scale + translate(offset)` pattern ImageView uses
- **Canvas `_hit_test`**: Update to match the new forward transform (offset sign change)
- **Canvas `_scroll`, `_motion`, `_set_zoom_with_center`, `_to_image_distance`**: Update coordinate math to match the new transform
- **Canvas offset setter**: Remove the translate-center effect; centering the image when smaller than the widget already happens via `_clamp_direction` (same as ImageView)
- **Update tests** in `test_7_canvas.py` that assert on coordinate values or transform behavior

## Capabilities

### Modified Capabilities

- `canvas-widget`: The offset property semantics change. Previously `offset=(ox, oy)` meant the image starts at `(ox, oy)` in widget-space (with inverse transform `image = widget/zoom + offset`). After the change it will match ImageView's convention: `image = widget/zoom − offset`. All zoom-related transforms (`_draw_scene`, `_hit_test`, `_scroll`, `_motion`, `_set_zoom_with_center`, `_to_image_distance`) are updated accordingly.

## Impact

- `scantpaper/canvas.py`: `_draw_scene`, `_hit_test`, `_scroll`, `_motion`, `_set_zoom_with_center`, `_to_image_distance`, offset setter
- `scantpaper/tests/test_7_canvas.py`: Tests that assert on coordinate values
