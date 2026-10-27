# Design

## Context

See `proposal.md` - Why. The relevant current state:

- `Canvas._draw_scene` renders the scene with `Canvas._scale_factors()`:
  `(zoom / factor / ratio, zoom / factor)`, then translates by `offset`.
- `Canvas._widget_to_image_rect`, `_to_image_distance`, `_scroll` and
  `_set_zoom_with_center` all use `_scale_factors()` too.
- `ImageView.to_image_coords` uses the same `x * factor * ratio / zoom -
  offset.x` inverse, so the Canvas renderer and the ImageView agree.
- `Canvas._hit_test` still uses `image = widget / zoom - offset`, which is
  the inverse of an older renderer that ignored `factor` and `ratio`. Commit
  `154b7cbd` updated every conversion except this one, so the Canvas no
  longer agrees with what it draws whenever `factor != 1` or `ratio != 1`.

`_hit_test` is called only by `Canvas._button_pressed` (and by tests);
`get_bbox_at` is a separate, image-coordinate entry point and is correct.

## Goals / Non-Goals

**Goals:**

- The widget click that focuses a slice maps to the same image point as the
  renderer and the ImageView, at any zoom, offset, resolution ratio and
  display scale factor.
- A regression test fails if the hit test and the renderer transform drift
  apart again.

**Non-Goals:**

- Changing the rendering transform, or the ImageView.
- Changing `get_bbox_at` (image coordinates), or line-vs-word click
  granularity (documented as pre-existing and unchanged elsewhere).
- Reworking the hit test into an acceleration structure; the linear scan is
  unchanged.

## Decisions

### D1: `_hit_test` inverts `_scale_factors()`, the single source of the transform

`_hit_test` becomes:

```
sx, sy = self._scale_factors()
image_x = widget_x / sx - self._offset.x
image_y = widget_y / sy - self._offset.y
```

`_scale_factors()` is already the one place that knows the transform; the
inverse is then correct by construction rather than by a second hand-written
formula. This also removes the last remaining duplicated transform in the
Canvas.

*Alternatives considered:*

- *Call `ImageView.to_image_coords` from the Canvas.* Rejected: it couples
  the Canvas to the view, and the Canvas is constructed standalone in tests
  and owns its own zoom/offset properties. The two already share values
  through property bindings; sharing the formula through one helper is
  enough.
- *Drop the `factor` division from the renderer instead.* Rejected: it would
  break the Canvas/ImageView alignment that `154b7cbd` established and that
  `canvas-widget` specifies, turning one regression into another.

### D2: Pin the behaviour with transform-explicit tests

Add tests that set `get_scale_factor`, `_resolution_ratio`, `_zoom` and
`_offset` and assert that `_hit_test` resolves a widget point to the intended
word. The existing `test_hit_test_nonzero_offset` only holds for
`factor == 1 and ratio == 1`; the new ones cover the two axes that were
missing so the drift cannot recur silently.

## Risks / Trade-offs

**Risk: a widget point now maps to a different word than before on HiDPI.**
→ That is the fix; the previous mapping was the bug. Scenarios in the delta
spec pin the intended mapping.

**Risk: `_scale_factors` returns `inf`/NaN for a zero ratio.** → No new
exposure: the renderer already calls `_scale_factors()` unconditionally, so
a degenerate ratio breaks drawing first; the hit test inherits the same
input from the same source.

## Migration Plan

No data migration, no schema change, rollback is a plain revert.
