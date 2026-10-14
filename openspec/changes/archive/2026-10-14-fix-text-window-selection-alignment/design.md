# Fix Text-Window Selection Alignment — Design

## Context

See `proposal.md` — Why. The Canvas widget (`canvas.py`) and the `ImageView`
(`imageview.py`) share the same `zoom`, `offset`, and `selection` values through
property bindings (`session_mixins.py`). Both store `offset` in **image units**
(a positive offset shifts the image rightward in widget space).

The `ImageView` converts image→widget coordinates with a **non-uniform**
transform (see `imageview.py:753-762`):

- x: `(img_x + offset.x) * zoom / factor / ratio`
- y: `(img_y + offset.y) * zoom / factor`

where `ratio` is the resolution ratio (`xres / yres`, a `GObject.Property`
defaulting to 1) and `factor` is the GTK display scale factor (HiDPI).

The Canvas instead assumes a **uniform** transform everywhere — `(p + offset) *
zoom` in `_draw_scene`, `rect.x * zoom + offset.x` in
`_draw_selection_rubberband`, and plain `x / zoom` in its widget→image
conversions. So the Canvas deviates from the ImageView in two ways:

1. The selection rubberband treats `offset` as widget units (`rect.x * zoom +
   offset.x`) rather than image units (`(rect.x + offset.x) * zoom`), producing
   the zoom-dependent drift (`offset * (zoom - 1)`).
2. The Canvas ignores `ratio` and `factor` entirely, producing a constant
   misalignment whenever the resolution is non-square or the display is HiDPI.

## Goals / Non-Goals

**Goals:**
- Make the Canvas selection rectangle and OCR bounding boxes land at the same
  widget coordinates as the `ImageView` at every zoom, offset, resolution ratio,
  and display scale factor.
- Keep the widget→image conversions (drawing a selection in the text pane,
  panning, zooming, offset clamping) the exact inverse of the same transform.
- Pin the behaviour with tests that assert exact rendered coordinates.

**Non-Goals:**
- Not changing the `ImageView` (it is correct) or the zoom/offset/selection
  bindings.

## Decisions

### D1: Share one non-uniform transform, expressed via a `resolution_ratio`

Add a `resolution_ratio` property to the Canvas (default 1, mirroring the
ImageView) and bind it from the view in `session_mixins.py`, alongside the
existing `zoom`/`offset`/`selection` bindings. The display `factor` comes from
`self.get_scale_factor()` (a `Gtk.Widget` method available on the Canvas
itself).

The Canvas then renders with the same cairo transform as the ImageView:

```
ctx.scale(self._zoom / factor / ratio, self._zoom / factor)
ctx.translate(self._offset.x, self._offset.y)
```

which maps `p → ((p.x + offset.x) * zoom / factor / ratio,
(p.y + offset.y) * zoom / factor)`, matching `to_widget_coords` exactly.
Rationale: reusing the view's `resolution_ratio` keeps a single source of truth
and reuses the established binding pattern. Alternatives considered:
- **Hardcode ratio = 1** — rejected: leaves the non-square-resolution
  misalignment unfixed.
- **Read the ratio from the view each draw** — rejected: a bound property is
  idiomatic with the other shared values and avoids coupling draw code to the
  view instance.

### D2: Apply the transform in every canvas coordinate path

Update each Canvas method that converts coordinates to use the shared
non-uniform transform (image→widget) or its inverse (widget→image):

- `_draw_scene` — the cairo `scale`/`translate` above.
- `_draw_selection_rubberband` — `wx = (rect.x + offset.x) * zoom / factor /
  ratio`, `wy = (rect.y + offset.y) * zoom / factor`, `ww = rect.width * zoom /
  factor / ratio`, `wh = rect.height * zoom / factor`.
- `_to_image_distance` — `(x * factor / zoom * ratio, y * factor / zoom)`
  (matches the ImageView and the offset-clamping setter).
- `_widget_to_image_rect` — divide x by `zoom / factor / ratio` and y by
  `zoom / factor` before subtracting `offset`.
- `_set_zoom_with_center` — `offset_x = allocation.width * factor / 2 / zoom *
  ratio - center_x`, `offset_y = allocation.height * factor / 2 / zoom -
  center_y` (mirrors `imageview.py:794-795`).
- `_scroll` / `_motion` — scale mouse deltas by `factor * ratio` (x) and
  `factor` (y) before dividing by zoom, mirroring `imageview.py:662-664`.

Rationale: the Canvas is not just a display — the user can draw a selection,
pan, and zoom *inside* the text pane, and those inputs must round-trip through
the same transform or the boxes and selection will be misplaced again. Updating
every conversion keeps the renderer and the input paths consistent.

### D3: Assert exact coordinates in the tests

Replace the "render was called" assertions with checks on the exact
`(x, y, w, h)` passed to `Gtk.render_background` (and the exact image rectangle
produced by a drag), computed via the shared transform — covering zoom > 1 with
a non-zero offset, zoom == 1, offset == (0, 0), a non-1 resolution ratio, and a
non-1 display factor. Mirror the existing `ImageView` rubberband test in
`test_imageview.py:1064`.

## Risks / Trade-offs

- [Changing `_scroll`/`_motion`/`_set_zoom_with_center` affects interactive
  feel in the text pane] → Mitigation: the formulas are copied verbatim from the
  working `ImageView` paths, and `ratio = factor = 1` reduces every change to the
  current uniform behaviour, so existing behaviour is preserved on the common
  path.

## Migration Plan

None — pure rendering/input fix in a desktop GUI; no data or deployment steps.

## Open Questions

None.
