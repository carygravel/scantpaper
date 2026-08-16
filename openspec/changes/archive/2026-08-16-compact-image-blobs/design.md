## Context

Import stores every page by re-encoding to PNG twice: `_insert_image` calls `page.to_bytes()` (docthread.py:284, PNG encode #1) and `page.get_pixbuf_at_scale(self.heightt, self.widtht)` (docthread.py:298), which writes a FULL-SIZE PNG just to make a 100 px thumbnail (page.py:321-330, PNG encode #2). Benchmark on the archive's 200 dpi spreads: ~4.1s PNG encode + ~4.1s full-size-thumb encode per page.

PDF save writes each page as a PNG (`write_image_for_pdf`, savethread.py:143) and feeds it to img2pdf. img2pdf cannot embed uncompressed 8-bit grayscale TIFF natively and re-encodes at PNG-encode cost; JPEG input is embedded natively in ~0.07s/page.

Key facts already established: `Image.open(BytesIO(blob))` auto-detects format (page.py:105), so mixed-format blobs load everywhere; img2pdf auto-detects its input; DjVu output (`write_image_for_djvu`) always decodes the PIL image and never reads the blob format; `_bytes_to_pixbuf` (docthread.py:704) uses GdkPixbuf which also sniffs content. No schema change is needed. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Eliminate both full-size PNG encodes at import for continuous-tone pages.
- Store a format img2pdf embeds without re-encoding, so PDF save also gets faster.
- Keep the bilevel path lossless (PNG) for lossless DjVu (cjb2) and bilevel PDF.
- Make the PDF save path pass stored JPEG bytes through when no options force a re-encode.

**Non-Goals:**
- OCR speed (feeding pixels to tesserocr, skipping the byte-compare re-encode) — separate change.
- Imported PDF page handling — follows the same storage rule as other continuous-tone pages.
- Wiring up real cancellation, adjusting JPEG quality settings, or PNG passthrough for bilevel at PDF save.
- Any database schema change.

## Decisions

**1. New `Page.to_stored_bytes()` decides the blob format, replacing `to_bytes()` in the import path.**
The single decision point is on `Page` (the old `to_bytes()` becomes the storage-decision method; nothing else used it):
- `mode == "1"` (bilevel) → PNG (lossless; feeds cjb2 losslessly for DjVu).
- source format is `"JPEG"` or `"PNG"` → the original file bytes, no re-encode (importing an already-compact file must not round-trip through PIL). This also covers transparent PNG sources.
- images with an alpha channel (`RGBA`/`LA`/`PA`) → PNG (lossless; JPEG cannot carry an alpha channel, so transparency is preserved).
- otherwise (opaque continuous-tone TIFF/PNM/scan) → JPEG encode at quality 92 (39.7 dB PSNR, SSIM 0.990 vs the TIFF per benchmark).

Rationale for JPEG-not-TIFF: storing raw uncompressed TIFF only right-shifts the encode to img2pdf, which recompresses it; JPEG is natively embeddable.

**2. Original bytes are captured at Page construction for compact sources only.**
`Page.__init__(filename=...)` already opens the file. For JPEG/PNG sources we read `open(filename, "rb").read()` into `self._stored_bytes`; for other formats we skip reading (a 37 MB uncompressed TIFF must not be slurped just to discard it). `to_stored_bytes()` returns `_stored_bytes` when the image's format is compact. For the multi-page TIFF case, each tiffcp-split page is a TIFF → re-encoded to JPEG per page.

**3. Thumbnails downscale before encoding.**
`get_pixbuf_at_scale` (page.py:307) keeps its `_prepare_scale` sizing and the `.load()` race-condition fix, but resizes the PIL image to the target box (`Image.resize` with `Image.BOX` on the full-size image down to ~100 px) before saving to the temp file. GdkPixbuf then loads an already-small PNG; the full-size re-encode disappears (~4.1s → ~10ms).

**4. PDF save passes stored JPEG bytes through.**
`write_image_for_pdf` (page.py:359) writes the stored blob directly to the temp file when: the page's stored format is JPEG (detected via `self.image_object.format`, which PIL sets from the blob header), no downsampling option, and no G3/G4 compression option. Otherwise it behaves as today. To make the stored bytes available, `Page.from_bytes` (page.py:103) stashes the blob on the page (`page._stored_bytes`). img2pdf reads DPI from `layout_fun` (savethread.py:149-155), not from the JPEG header, so embedded DPI is irrelevant. Bilevel pages keep the current PNG write path.

**5. Byte-compare reuse still works.**
`_insert_image(if_different_from=...)` compares stored blobs. PIL's PNG and JPEG encodes are deterministic for identical pixels, so edited-but-unchanged pixels (e.g. the OCR path) still match and reuse the existing image row. No change needed here for correctness.

## Risks / Trade-offs

- **JPEG is lossy for continuous-tone pages** → measured q92 keeps SSIM 0.990 / max diff 18; bilevel pages stay lossless. Acceptable for the archival use case; quality constant is a single place to tune.
- **Mixed-format blobs confuse debugging/migrations** → all readers auto-detect; no column added (see proposal). If tooling later needs it, a `format` column can be added then (YAGNI).
- **Image-object pages (fresh scans, edits) default to JPEG q92** → consistent with the import policy; scans are continuous-tone by nature.
- **Deterministic re-encode assumption** → if a PIL/OS upgrade changes encoder output, `if_different_from` may fail to match and insert a duplicate row. Correct, just a few extra MB. Acceptable.
- **Passthrough only benefits JPEG** → PNG bilevel pages still go through img2pdf's encoder; bilevel pages are typically far fewer and smaller, so the saving is dominated by JPEG pages.

## Migration Plan

No DB migration. New sessions write mixed-format blobs; existing sessions keep their PNG blobs and load unchanged (spec: Existing PNG sessions remain readable).
