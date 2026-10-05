## Why

Page switching is slow for large color scans (600 dpi A4) because the full-resolution display path encodes the entire page as a PNG to a temporary file before creating a GdkPixbuf. For noisy scan images this is very expensive (tens of seconds in practice). Creating the pixbuf directly from PIL image data eliminates this roundtrip and dramatically improves display performance with no user-visible behavior change.

## What Changes

- Optimize `Page.get_pixbuf()` to create GdkPixbuf directly from PIL pixel data instead of saving to a temporary PNG file. This preserves the same API, behavior, and error handling.
- Preserve compatibility with existing tests (including tests that mock `GdkPixbuf.Pixbuf.new_from_file`).
- Maintain correct handling for all image modes (RGB, RGBA, LA, PA, P, 1, L, I, and 16-bit variants).

## Capabilities

### New Capabilities
None

### Modified Capabilities
- `image-rendering`: Improve performance of pixbuf creation for page display without changing rendering behavior or API contracts.

## Impact

- Affected: `src/scantpaper/page.py` (`get_pixbuf()` method)
- No API changes, no behavior changes visible to users
- All existing tests continue to pass
- Significant performance improvement for large color scans
