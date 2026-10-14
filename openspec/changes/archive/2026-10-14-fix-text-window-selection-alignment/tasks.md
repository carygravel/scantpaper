# Fix Text-Window Selection Alignment — Tasks

## 1. Fix the rubberband rendering

- [x] 1.1 In `src/scantpaper/canvas.py`, update `_draw_selection_rubberband`
      so the offset is scaled by the zoom level, matching `_draw_scene` and the
      ImageView: `wx = (rect.x + self._offset.x) * self._zoom`,
      `wy = (rect.y + self._offset.y) * self._zoom` (width/height unchanged).

## 2. Add a coordinate-asserting test

- [x] 2.1 Extend `src/scantpaper/tests/test_7_canvas.py` so the selection
      rendering test asserts the exact `(x, y, w, h)` passed to
      `Gtk.render_background` using the `(rect + offset) * zoom` formula,
      covering zoom > 1 with a non-zero offset, zoom == 1, and offset == (0, 0).
- [x] 2.2 Confirm the existing selection tests still pass and cover the new
      scenarios from `specs/canvas-widget/spec.md`.

## 3. Add resolution-ratio and scale-factor support

- [x] 3.1 Add a `resolution_ratio` property to the Canvas (default 1.0) and bind
      it from the `ImageView` in `session_mixins.py` alongside the existing
      zoom/offset/selection bindings.
- [x] 3.2 Update `_draw_scene` and `_draw_selection_rubberband` to use the
      non-uniform transform `(p + offset) * zoom / factor / ratio` (x) and
      `(p + offset) * zoom / factor` (y), where `factor = get_scale_factor()`.
- [x] 3.3 Update the widget→image conversions `_to_image_distance`,
      `_widget_to_image_rect`, `_set_zoom_with_center`, `_scroll`, and `_motion`
      to be the exact inverse of the same transform.

## 4. Extend tests for ratio and factor

- [x] 4.1 Extend `src/scantpaper/tests/test_7_canvas.py` to assert exact widget
      coordinates for a non-1 resolution ratio and a non-1 display scale factor,
      and that a drag in the widget produces the inverse-transformed image
      rectangle (scenarios from `specs/canvas-widget/spec.md`).

## 5. Verify

- [x] 5.1 Run `pytest` and confirm the full suite (including coverage gates)
      passes.
- [x] 5.2 Run `ruff format` and `ruff check` on the changed files with no new
      diagnostics.
- [x] 5.3 Run the type checker (`ty check .`) with no new diagnostics.
- [x] 5.4 Document the user-visible fix in `changelog.md`.

## 6. Re-verify after the ratio/factor change

- [x] 6.1 Run `pytest` and confirm the full suite (including coverage gates)
      passes.
- [x] 6.2 Run `ruff format`, `ruff check`, and `ty check .` with no new
      diagnostics.
