## Context

The save pipeline (`SaveThread.do_save_pdf`) writes each page to a temporary
PNG, feeds them to `img2pdf.convert`, then passes the result through
`ocrmypdf` for text-layer embedding and PDF/A metadata.  When the output
exceeds 2 GiB, three tools in this chain use 32-bit file offsets:

- **img2pdf 0.6.2** (pikepdf engine): linearizes with 32-bit xref offsets →
  truncated PDF
- **Ghostscript 10.07.1** (PDF/A conversion via ocrmypdf): reads/writes with
  32-bit offsets → fails or corrupts.  Note: Ghostscript's 64-bit integer
  support is build-dependent and may not be enabled in all packages.
- **pikepdf 10.5.0 / qpdf 12.4.0** (metadata save, xref-stream
  linearization): 32-bit offsets in xref streams → missing /Root dictionary

Attempts to work around each tool individually proved brittle: disabling
linearization and PDF/A still left pikepdf's internal metadata save
step vulnerable.  The only reliable fix is to avoid the threshold entirely.

## Goals / Non-Goals

**Goals:**
- Prevent silent data loss by rejecting saves that would produce >2 GiB PDFs
- Give the user an actionable error (estimated size, suggestion to save fewer
  pages)
- Roll back the now-unnecessary workarounds (engine selection, skip_pdfa,
  fast_web_view, pikepdf version upgrade, output validation) to reduce
  complexity
- Document the three overflow bugs in README.md so they can be re-tested when
  dependencies update

**Non-Goals:**
- Supporting saves larger than 2 GiB (requires upstream fixes in img2pdf,
  ocrmypdf/pikepdf, and Ghostscript)
- Implementing chunked or multi-part saving (future enhancement, not in scope)
- Changing the ocrmypdf pipeline internals

## Decisions

### Estimate size before conversion, not after

**Choice:** Compute per-page size estimates from image metadata (width ×
height × bytes-per-pixel) before writing any temporary PNGs.

**Rationale:** Estimating before conversion means the check fires early,
before the user waits for potentially hundreds of image conversions.  The
estimate is conservative (uncompressed pixel data) so it may reject some
saves that would have been just under 2 GiB — but false negatives (corrupt
output) are far worse than false positives (save a few pages, then the rest).

**Alternatives considered:**
- *Write all pages then check*: Wastes time converting images that will
  never be in the output.  Also means temp files need cleanup on rejection.
- *Use img2pdf's internal engine for >2 GiB*: Avoids linearization but
  pikepdf's metadata save still corrupts at ~7 GiB.  Partial fix, not
  reliable.
- *Skip ocrmypdf entirely for >2 GiB*: Produces a PDF without text layer
  or PDF/A metadata — not acceptable for the user's use case.

### JPEG passthrough detection

**Choice:** When a source page is JPEG and no downsample/compression option
overrides it, use the on-disk file size as the estimate (since img2pdf
stores JPEG data verbatim).  For other formats, use pixel-dimension
estimate.

**Rationale:** JPEG files are already compressed and stored as-is in the
PDF, so the file size is a precise estimate.  Uncompressed formats (PNG,
TIFF, PNM) are stored as raw pixel data, so width × height × bpp is
accurate.

### Raise RuntimeError via request.error()

**Choice:** When the estimate exceeds 2 GiB, raise a `RuntimeError` with
a translated message.  The `basethread` handler wrapper catches this and
displays it as an error dialog.

**Rationale:** Matches the existing error-reporting pattern in the codebase
(e.g., PS conversion errors).  The error message includes the estimated
size in GiB and suggests saving fewer pages.

## Risks / Trade-offs

- **False rejections for compressed formats** → Conservative estimate may
  reject saves that would have been valid (e.g., JPEG-heavy documents
  near the threshold).  This is acceptable: the user can save in smaller
  batches, and the alternative is silent corruption.

- **Estimate inaccuracy** → Pixel-dimension estimate does not account for
  PDF object overhead, metadata, or cross-reference tables.  The overhead
  is small relative to image data for large documents, so the estimate
  remains reliable.

- **Rollback removes partial mitigations** → Users who previously got a
  partially working output (e.g., first N pages readable via fallback)
  will now see an error dialog.  This is better: the previous behavior
  was unpredictable and could lose data silently.
