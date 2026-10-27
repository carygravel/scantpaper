# Proposal

## Why

Clicking an OCR word in the Text or Annotations layer does not focus the
word the user clicked when the display scale factor is not 1 (HiDPI or
fractional scaling) or the page's x/y resolution differ. The click is
mapped through a stale widget-to-image transform, so it lands on a
neighbouring word or on the page box and the correction cannot begin until
the user clicks several more times. The Canvas renderer and every other
coordinate conversion already use the ImageView transform; only the hit
test was left behind, so the Canvas hit test no longer agrees with what it
draws.

## What Changes

- Make `Canvas._hit_test` invert the same image-to-widget transform the
  renderer uses (`Canvas._scale_factors()`), so a widget click maps to the
  same image point that `ImageView.to_image_coords` produces.
- Add regression coverage for hit testing under a non-1 display scale
  factor and a non-1 resolution ratio, at a non-trivial zoom and offset.
- No change to `get_bbox_at`, which already takes image coordinates and is
  correct; and no change to the visible rendering.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `canvas-widget`: The display-transform requirement already states that
  *every* widget-to-image coordinate conversion must apply the resolution
  ratio and display scale factor. The click-to-focus conversion is called
  out explicitly and given a scenario, so the hit test is held to the same
  transform as the renderer and the ImageView.

## Impact

- `src/scantpaper/canvas.py` — `Canvas._hit_test` only.
- `src/scantpaper/tests/test_7_canvas.py` — new hit-test regression tests.
- No dependency, data-model, SQLite, saved-output, or user-visible
  rendering change. `LayerEditor` and the control bar are unchanged; they
  receive the correct `Bbox` once the click maps correctly.
