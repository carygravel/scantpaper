## Context

Canvas and ImageView are both `Gtk.DrawingArea` subclasses whose `zoom` and `offset` properties are bound via `GObject.bind_property(BIDIRECTIONAL)`. However their Cairo transforms implemented differently:

**ImageView** (imageview.py:546–548):
```
context.scale(z/f/r, z/f)
context.translate(ox, oy)
```
```
widget_x = (image_x + ox) * z/f/r
widget_y = (image_y + oy) * z/f
```
Offset = how much the image has been shifted rightward.

**Canvas** (canvas.py:750–754):
```
ctx.translate(W/2, H/2)
ctx.scale(S, S)
ctx.translate(-W/2/S, -H/2/S)
ctx.translate(-ox, -oy)
```
Simplifies to `widget_x = (image_x − ox) * S`, which means the **same offset value means opposite scrolling** on each widget. The translate-center dance cancels out mathematically; centering is already handled by `_clamp_direction` in the offset setter.

See proposal.md - Why for motivation.

## Goals / Non-Goals

**Goals:**
- Canvas uses the same Cairo transform formula as ImageView (`scale + translate(offset)`)
- Offset sign convention matches ImageView (positive offset = rightward shift)
- All coordinate conversion methods (`_hit_test`, `_scroll`, `_motion`, `_set_zoom_with_center`, `_to_image_distance`) use consistent math
- The blank initial view is eliminated: both widgets show the same image region at the same zoom/offset

**Non-Goals:**
- No changes to ImageView's coordinate system
- No changes to the `bbox` data model (Bbox tree stores image-pixel coordinates, unchanged)
- No changes to the drawing of bboxes themselves (rectangle, text, rotation — all in image-pixel coordinates as before)

## Decisions

### Decision: Match ImageView's transform exactly

`_draw_scene` will change from:
```python
ctx.translate(allocation.width / 2, allocation.height / 2)
ctx.scale(scale, scale)
ctx.translate(-allocation.width / 2 / scale, -allocation.height / 2 / scale)
ctx.translate(-self._offset.x, -self._offset.y)
```
to:
```python
ctx.scale(scale, scale)
ctx.translate(self._offset.x, self._offset.y)
```

**Rationale:** The translate-center/scale/translate-back formula was a legacy from when Canvas was independent. Now that zoom/offset are bound to ImageView, keeping a different transform guarantees inconsistency. The `_clamp_direction` mechanism (shared through offset setter clamping) already handles centering of small images.

### Decision: Remove the widget-center centering from `_draw_scene`

The old transform centers the zoom about the widget center, but the combination of:
1. Scaling about widget center (`translate(W/2) → scale → translate(-W/2/S)`)
2. Then applying offset (`translate(-ox, -oy)`)

...simplifies to just `widget = (image - offset) * zoom`, with no centering in the transform. The centering happens entirely in offset clamping. So removing the translate-center dance changes no actual behavior — it just makes the transform match what the math already does.

### Decision: Update all coordinate methods consistently

| Method | Change |
|---|---|
| `_draw_scene` | `translate(W/2,H/2); scale(S); translate(-W/2/S)` → `scale(S); translate(ox,oy)` |
| `_hit_test` | `image_x = widget_x / S + offset.x` → `image_x = widget_x / S − offset.x` |
| `_scroll` | Cursor-to-image conversion: update to subtract offset instead of adding |
| `_motion` | Drag delta math uses `_to_image_distance` which already returns `delta / zoom` — no change needed |
| `_set_zoom_with_center` | Compute `offset_x` to place `center_x` at widget center: now `offset_x = widget_center / zoom − center_x` (currently flipped sign) |
| `_to_image_distance` | Unchanged: `x / zoom, y / zoom` (pure distance, no offset involved) |

## Risks / Trade-offs

- **Risk: Existing tests assert on old coordinate math** → All tests in `test_7_canvas.py` that check offset/zoom/scroll behavior need updating. Specifically `test_canvas_scroll`, `test_drag_text_layer`, `test_set_zoom_with_center_clamp`, and `test_canvas_set_offset_clamping`.
- **Risk: Saved sessions with stale offset values** → Offset is not persisted in session files (it's a view state), so no migration needed.
- **Trade-off: Offset setter clamping logic** currently converts allocation to image distance via `_to_image_distance(x/zoom)` before clamping against pixbuf size. This is the same approach as ImageView and works correctly with the new transform. No change needed there.
