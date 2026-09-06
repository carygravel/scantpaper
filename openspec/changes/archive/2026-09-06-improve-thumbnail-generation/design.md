## Context

Thumbnail generation currently lives in a single entry point,
`Page.get_pixbuf_at_scale` (`scantpaper/page.py`), which is called from
`docthread._insert_image` when a page is stored in SQLite. It downscales the
page's PIL `Image` to at most `THUMBNAIL` (100 px) with a single
`Image.Resampling.BOX` pass, writes the result to a temporary PNG, and loads it
into a `GdkPixbuf` for the thumbnail panel.

The motivation and scope are in `proposal.md`; the behaviour contract is in
`specs/thumbnail-generation/spec.md`. This document records only the technical
approach and the reasoning behind it.

## Goals / Non-Goals

Goals:
- Produce visibly sharper thumbnails without meaningfully slowing bulk imports.
- Keep the change local to the thumbnail generation path.

Non-Goals:
- Changing thumbnail size, storage, or the thumbnail panel rendering.
- Changing main-view interpolation (governed by `image-rendering`).
- Altering the full-resolution page display path.

## Decisions

### D1: Two-step decimate-then-resample instead of a single filter pass

Replace the single `Image.Resampling.BOX` resize with:

1. `image.reduce(factor)` — an integer box-decimation down to roughly twice the
   target size. This is C-fast and is the correct "ink coverage" downscaler for
   document text.
2. `image.resize((w, h), resample=Image.Resampling.LANCZOS)` — a final
   high-quality pass to the exact thumbnail size, running on the now-tiny
   intermediate image (negligible cost).

The decimation factor is derived from the larger target dimension so the
intermediate lands at ~2x the target, e.g.
`factor = max(1, ceil(max(w, h) / (2 * target_max_dim)))`.

Alternatives considered:
- **Single `LANCZOS`**: best one-pass quality but ~4-8x slower than BOX on a
  full-resolution scan; can also ring slightly around high-contrast text edges.
- **Single `BICUBIC`**: middle quality, still slower than BOX on the full image.
- **Let gdk-pixbuf do BILINEAR (gscan2pdf parity)**: requires writing the
  full-resolution PNG to the temp file first (more I/O) and yields only moderate
  sharpness; it diverges from the PIL pipeline for marginal benefit.

The two-step approach gives LANCZOS-class quality at approximately BOX cost
because the expensive resample runs on a ~2x-target image instead of the full
scan.

PIL's C `Image.reduce` is unsupported for a few modes common in scans/bilevel
images ("1", "P", and some 16-bit integer modes, tracked by
`_REDUCE_UNSUPPORTED`). For those modes the decimation step is skipped and the
thumbnail is produced by a direct LANCZOS resize, which PIL supports for every
mode; the quality improvement still applies, only without the fast pre-decimate.

### D2: Preserve existing mode normalisation

Keep the existing `image.mode == "I"` → `"L"` conversion and the
`_prepare_scale` resolution-ratio sizing unchanged, so aspect ratio and
non-uniform x/y resolution handling are identical to today.

### D3: Preserve the temp-PNG round-trip and fill-box behaviour

Continue writing the resized thumbnail to a temporary PNG and loading it via
`GdkPixbuf.Pixbuf.new_from_file_at_scale`, and keep resizing any source image
(including one smaller than the box) to fill the computed `_prepare_scale` box.
Upscaling small sources to fill the box is the existing, intended behaviour
(consistent panel appearance) and only affects artificially small images; real
scanned pages are always larger than the 100 px box and take the downscale path.

## Risks / Trade-offs

- **[LANCZOS ringing on 1-bit/high-contrast text]** → Mitigated by the
  decimation-first approach: `reduce` handles the bulk downscale, and LANCZOS
  only smooths a small intermediate, keeping ringing minimal.
- **[Decimation factor rounding leaves a thumbnail slightly larger/smaller than
  the box]** → `resize` to the exact `_prepare_scale` size in step 2 clamps to
  the target, so the output stays within the 100 px box.
- **[Slight per-page CPU increase vs BOX]** → Negligible because the resample is
  on a ~2x-target image and the work is off the GUI thread; import wall-time
  impact is expected to be within noise.

## Migration Plan

- Rollback: revert `get_pixbuf_at_scale` to the single BOX resize. No schema,
  storage, or data migration is needed; thumbnails are regenerated on import.
- No external dependency or packaging changes.

## Open Questions

None. The spec, approach, and task breakdown are fully determined.