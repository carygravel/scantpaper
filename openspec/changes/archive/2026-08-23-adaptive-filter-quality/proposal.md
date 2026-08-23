# Proposal: Adaptive filter quality — FAST during interaction, GOOD on idle

## Why

When an entire A4 page is displayed on screen, the fit-to-window zoom drops
below 0.5 and `ImageView` renders with `cairo.FILTER_FAST` (point sampling).
At ~0.3× this makes scanned pages — and thresholded pages especially — look
blurred, speckled and broken, so users can't assess scan/threshold quality in
the full-page view. Zooming in one step crosses into `FILTER_GOOD` and the
image suddenly looks fine. Measurement shows `FILTER_GOOD` is ~5× more
expensive than `FILTER_FAST` (≈21 fps vs ≈74–91 fps at fullscreen A4), so the
FAST band exists for a real reason and cannot simply be removed.

## What Changes

- `ImageView` will render with `cairo.FILTER_GOOD` (the configured
  interpolation) whenever the page is static.
- `ImageView` will temporarily switch to `cairo.FILTER_FAST` only while the
  user is interacting (dragging/panning, scroll-zooming), then return to
  `FILTER_GOOD` on idle.
- The current zoom-threshold logic in `_get_adaptive_filter()` (FAST below
  0.5×, GOOD below 1.0×, user interpolation above) is replaced by this
  interaction-driven approach, so high-quality rendering no longer depends on
  zoom level.
- The user-selected `interpolation` property is honoured for all static
  renderings, not just zoom ≥ 1.0.

## Capabilities

### New Capabilities
- `image-rendering`: Screen rendering of scanned page images in the main image
  view, covering interpolation selection for static display versus interactive
  manipulation.

### Modified Capabilities
<!-- No existing capability covers the image view's interpolation behaviour. -->

## Impact

- `scantpaper/imageview.py` — `_get_adaptive_filter()` and its callers; draw
  path; interaction handlers (drag/pan, scroll).
- Existing tests in `scantpaper/tests/test_imageview.py` that assert the
  current zoom-threshold behaviour (`test_adaptive_filter`) will be updated.
- No new dependencies. No data-model changes.
