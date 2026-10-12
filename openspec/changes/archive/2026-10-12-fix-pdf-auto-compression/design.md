## Context

See `proposal.md` for motivation. What shapes the approach:

- PDF assembly is `img2pdf.convert()` over one temp file per page, then
  `ocrmypdf.api._hocr_to_ocr_pdf(..., optimize=0)` embeds the text layer and
  never recompresses images, then `pikepdf` fixes metadata. So whatever
  `Page.write_image_for_pdf` writes is what ends up in the PDF.
- `img2pdf` embeds a non-interlaced PNG's IDAT stream directly as Flate and
  only transcodes to CCITT Group 4 for inputs that are neither JPEG nor PNG
  (e.g. PBM/G4 TIFF). A JPEG input is copied verbatim as DCTDecode.
- Today `write_image_for_pdf` writes a `.png` temp for every page that is not
  a JPEG passthrough, and `auto` is never resolved, so it falls into that
  branch or the JPEG passthrough depending only on the stored format.
- Stored images are JPEG quality 92 for continuous-tone, PNG for
  bilevel/transparency (`Page.to_stored_bytes`). Provenance (original import
  vs scantpaper-generated) is not persisted: `Page.from_bytes` sets
  `_stored_bytes` from the blob for every page.

## Goals / Non-Goals

**Goals:**

- Resolve `auto` to a real per-page codec, matching or beating gscan2pdf's
  output size for the same scan.
- Make the JPEG quality setting actually affect PDF output.
- Emit genuine CCITT Group 4 for bilevel pages.
- Avoid re-encoding unmodified imported images.

**Non-Goals:**

- Changing the in-session storage format (quality-92 JPEG stays).
- JBIG2 or JPEG 2000 output (better ratios, but new encoders/dependencies).
- Default downsampling to 300 ppi (separate, more controversial change).
- A true uncompressed `none` output (`img2pdf` always flates non-JPEG); the
  existing Flate fallback is retained.

## Decisions

### Resolve `auto` per page at save time

`auto` maps to: bilevel -> CCITT G4; alpha channel -> Flate; continuous-tone
(grayscale/RGB/CMYK) -> JPEG. This drops gscan2pdf's grayscale->PNG branch
deliberately: scantpaper stores grayscale as JPEG and currently embeds it as
JPEG, so switching grayscale to PNG would *increase* size, not reduce it.
Alternatives considered: copy gscan2pdf's table verbatim (rejected: makes
grayscale bigger); threshold grayscale to G4 (rejected: lossy and surprising).

### Emit real Group 4 by writing a PBM temp

For bilevel pages the temp file written for `img2pdf` becomes a 1-bit PBM
instead of a PNG, which routes `img2pdf` through its Group-4 transcode path.
Alternatives considered: `tiffcp -c g4` into a G4 TIFF (works, verified, but
an extra subprocess); `pikepdf` post-processing (heavier). This also fixes the
explicit `g3`/`g4` options, which today threshold to 1-bit but still emit
Flate because the temp is a PNG.

### Honour quality by re-encoding generated images at save

On save, a page is re-encoded when the resolved codec requires it and the page
is not an unmodified original import. For JPEG this means the configured
quality is applied. Alternative considered: store scans at the configured
quality so the passthrough is already correct (rejected: the save setting
would leak into storage, later quality changes would not affect already-stored
pages, and editing fidelity would drop).

### Persist image provenance

Distinguishing an original imported JPEG (embed verbatim) from a
scantpaper-generated JPEG (re-encode at quality) needs a flag, because the
stored blob looks the same after a reload: `from_bytes` sets `_stored_bytes`
from the blob for every page, so `_stored_bytes is not None` cannot stand in
for provenance. Add a column on the `image` table (the flag describes the
bytes, which are shared/deduplicated across pages):

```
original  INTEGER NOT NULL DEFAULT 0
    1 = the stored blob is the untouched bytes of an imported file
    0 = the blob was produced by scantpaper's encoder (scan, or any edit)
```

It is deliberately binary: it drives exactly one branch, embed-verbatim vs
re-encode, and every generated encode (scan, rotate, threshold, unpaper) gets
the same treatment, so no finer origin is needed (YAGNI).

Set/clear points:

- Import (`Page.__init__` with a JPEG/PNG filename, whose bytes are kept
  verbatim by `to_stored_bytes`) inserts `original = 1`.
- Any generated encode inserts `original = 0`, so a previously imported page
  that is later rotated or thresholded is correctly treated as generated.
- `Page` carries a persisted `original` field alongside `_stored_bytes`:
  `_stored_bytes` is the bytes to embed, `original` says whether they are an
  unmodified import. `from_bytes` restores it from the column.

Legacy rows cannot be classified, so the migration default is `0`
("generated"). The common content of a saved session is scans, the size fix
is the point of the change, and the cost for an old import is one extra
encode at the same default quality. Alternative considered: `NULL`/"unknown"
with a pass-through policy (rejected: adds a third state and a policy for
little benefit). Alternative considered: infer provenance from the blob
(rejected: not reliably possible).

## Risks / Trade-offs

- [Scanned pages are compressed twice, quality 92 -> configured quality] ->
  visually negligible at the default 75; output size and quality match
  gscan2pdf, which is the comparison the report is about.
- [Old session images default to `original = 0`] -> they are re-encoded on
  save, which is the intended new behaviour for generated images and harmless
  for old imports (one extra encode, no visible change at the same quality).
- [G4 depends on `img2pdf`'s transcode path] -> cover with a test that
  asserts the extracted image is 1-bit and the stream filter is CCITT, using
  `pikepdf`/`pdfimages`, not merely that the image is 1-bit.
- [The re-encode makes `auto` saves slightly slower] -> only continuous-tone
  generated pages are re-encoded; original JPEG imports and bilevel pages are
  not.
- [Provenance flag must be cleared on edit] -> every image re-insert path
  (`to_stored_bytes` callers) must insert without the flag; assert in tests.

## Migration Plan

1. Bump `USER_VERSION` to 3 in `const.py`.
2. On `open()`, for user_version 2, `ALTER TABLE image ADD COLUMN original
   INTEGER DEFAULT 0` and set the version.
3. New databases create the column directly.
4. Rollback: the column is additive and ignored by older builds, so a
   downgrade still opens the session.

## Open Questions

None.
