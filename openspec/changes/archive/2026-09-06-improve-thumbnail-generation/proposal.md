## Why

scantpaper generates page thumbnails by downscaling each scanned page with
PIL's `Image.Resampling.BOX` filter in a single pass (`page.py:get_pixbuf_at_scale`).
Compared with gscan2pdf, which lets gdk-pixbuf do the downscaling with a
higher-quality interpolation, the resulting thumbnails are visibly flatter and
blockier, and fine text in a 100 px thumbnail reads as distorted. Thumbnails are
generated in the import worker thread, so improving the filter only affects
total import time, not UI responsiveness.

## What Changes

- Replace the single-pass `Image.Resampling.BOX` downscale in
  `page.py:get_pixbuf_at_scale` with a two-step decimate-then-resize:
  an integer box-decimation (`Image.reduce`) to roughly twice the target size,
  followed by a `Image.Resampling.LANCZOS` resize to the exact thumbnail size.
- Preserve existing behavior: thumbnails remain at most `THUMBNAIL` (100 px) in
  each dimension, respect the page's x/y resolution ratio, and are still written
  to a temporary PNG and loaded into a `GdkPixbuf` for the thumbnail panel.
- No change to thumbnail size, storage, or the displayed thumbnail panel.

## Capabilities

### New Capabilities
- `thumbnail-generation`: Governs how page thumbnails are generated from a
  scanned page, specifying that the downscale produces a sharp, high-quality
  thumbnail using decimation-then-resampling rather than a single coarse filter.

### Modified Capabilities
<!-- None. The existing `image-rendering` capability governs Cairo interpolation
     in the main image view, which is unchanged by this work. -->

## Impact

- **Code**: `scantpaper/page.py` (`get_pixbuf_at_scale`), the sole thumbnail
  generation entry point used by `docthread._insert_image`.
- **Dependencies**: none added. Uses PIL APIs (`Image.reduce`, `Image.Resampling.LANCZOS`)
  available since Pillow 4.0 (installed: 12.3).
- **Performance**: negligible impact on import throughput because the expensive
  LANCZOS pass runs on a ~2x-target intermediate image rather than the full
  resolution scan, and the work stays on the import worker thread.
- **Tests**: existing thumbnail tests in `scantpaper/tests/` must still pass
  (dimensions, rotation behaviour); add coverage for the two-step path.