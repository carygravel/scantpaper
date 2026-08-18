## Why

Saving many uncompressed scanned pages produces a PDF larger than 2 GiB.  At that size, three downstream tools — img2pdf's linearizing engine (0.6.2), Ghostscript's PDF/A conversion (10.07.1), and pikepdf's xref-stream linearization (10.5.0/qpdf 12.4.0) — overflow 32-bit file offsets and produce truncated or corrupt output.  Attempts to work around each tool individually (switching to a non-linearizing engine, disabling PDF/A, suppressing linearization) proved fragile: pikepdf's metadata-save step still corrupts the file at ~7 GiB because qpdf itself has internal 32-bit limits.

The simplest correct approach is to **estimate the output size before conversion** and, if it would exceed 2 GiB, **refuse to save with a clear error message** telling the user to save fewer pages at a time.  This avoids silent data loss and gives the user an actionable path forward.

## What Changes

- Add an `_estimate_page_pdf_size` helper that computes a per-page size estimate from image dimensions and pixel format, with JPEG passthrough detection for compressed sources.
- In `do_save_pdf`, accumulate the per-page estimates and raise an error via `request.error()` when the total exceeds 2 GiB, before any image conversion or PDF writing begins.
- Roll back the previous 2 GiB workarounds (img2pdf internal engine selection, `output_type="pdf"`, `fast_web_view`, `linearize=False` for `_remove_pdf_title`, pikepdf version-upgrade re-save, output validation via `pikepdf.open`), since they no longer serve a purpose once the size check rejects large saves early.
- Document the three known 32-bit overflow bugs in README.md under a "Known Limitations" section, with enough detail (affected component, threshold, symptom) that anyone updating img2pdf, ocrmypdf, pikepdf, or Ghostscript can re-test quickly.

## Capabilities

### New Capabilities
- `pdf-size-limit-warning`: The save operation SHALL estimate the output PDF size from source images and, when the estimate exceeds 2 GiB, SHALL abort with a user-visible error suggesting fewer pages.

### Modified Capabilities
- `save-pdf-metadata`: Add a requirement that the save pipeline SHALL NOT attempt to produce output exceeding 2 GiB, since the downstream tools corrupt it.  This extends the existing "Saved PDF remains valid" requirement.

## Impact

- **Code**: `scantpaper/savethread.py` — `_estimate_page_pdf_size` (new helper), `do_save_pdf` (size check + error), rollback of `_embed_text_layer` skip_pdfa/fast_web_view params and `_remove_pdf_title` linearize param.
- **Tests**: `scantpaper/tests/test_savethread.py` — new test for the size-limit error, update existing large-PDF test to verify error instead of engine selection.
- **Documentation**: `README.md` — new "Known Limitations" section documenting the three overflow bugs.
- **Dependencies**: No new dependencies.  The rollback removes complexity from the ocrmypdf/pikepdf integration.
