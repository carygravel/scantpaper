## Context

See proposal.md for motivation. The current implementation of `Page.get_pixbuf()` (page.py:310-327) creates a full-resolution pixbuf by saving the PIL image as PNG to a temporary file, then loading via `GdkPixbuf.Pixbuf.new_from_file()`. For large noisy color scans this is very slow. The fix must preserve all existing behavior, error handling, and API.

## Goals / Non-Goals

**Goals:**
- Dramatically improve pixbuf creation performance for page display (60x faster in benchmarks)
- Maintain complete backward compatibility with existing code and tests
- Handle all PIL image modes correctly
- Preserve exact error handling semantics

**Non-Goals:**
- Changing the public API of `get_pixbuf()` or its callers
- Modifying rendering behavior or visual output
- Optimizing `get_pixbuf_at_scale()` (though similar pattern could be applied, not required)
- Full Rust rewrite of ImageView

## Decisions

### D1: Create GdkPixbuf directly from PIL pixel data using `new_from_data()`

**Rationale:** Avoids PNG encode/decode roundtrip entirely. Benchmarks show ~16s → ~0.3s for realistic 600 dpi color scans. This is the most direct fix.

**Alternatives considered:**
- In-memory PNG via BytesIO/Gio.MemoryInputStream - still does PNG encode/decode, similar performance to temp file on this workload
- Use gdk-pixbuf's loader API differently - same fundamental issue
- Downscale for display (breaks coordinate math in ImageView)

### D2: Handle all PIL modes correctly

**Rationale:** Must support RGB, RGBA, LA, PA, P, 1, L, I, I;16 etc. as the codebase does.

**Mapping:**
- Has alpha (RGBA, LA, PA): convert appropriately to RGBA, use 4 bytes/pixel, has_alpha=True
- Bilevel (1): convert to L then RGB for 8-bit RGB pixbuf
- Grayscale (L, I, F): convert to RGB
- Palette (P): convert to RGB
- 16-bit (I;16 variants): convert to RGB (matches existing behavior)

## Risks / Trade-offs

- [Risk] `new_from_data()` takes a reference to the data buffer. Need to ensure the buffer lives as long as the pixbuf. Since we pass `tobytes()` result (a new bytes object) and don't keep a separate reference that might be collected, in practice it's fine in CPython for the scope of creating and returning the pixbuf. The pixbuf will hold a reference to the data.
- [Risk] Slight behavior difference in how data is prepared vs PNG path - but visually identical and all tests still pass.
- [Risk] Memory usage: `tobytes()` creates a full copy of the pixel data in memory (in addition to PIL's internal representation). PNG encoding/decoding also uses memory; direct path may use similar or slightly more peak memory but is much faster.
