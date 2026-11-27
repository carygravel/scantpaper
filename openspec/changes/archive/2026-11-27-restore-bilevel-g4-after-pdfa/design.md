# Design

## Context

See `proposal.md` - Why. A PDF save assembles page images with
`img2pdf.convert()`, then `_embed_text_layer()` calls
`ocrmypdf.api._hocr_to_ocr_pdf()`, which runs Ghostscript to produce PDF/A.
The image codec is already chosen by `resolve_pdf_codec()`: CCITT Group 4 for
bilevel pages, unless the bilevel preference selects JBIG2. The lossless PDF/A
request added for `2026-10-26-lossless-pdfa-image-handling` stops Ghostscript
from turning lossless grayscale or colour images into JPEG, but Ghostscript
10.06 still rewrites 1-bit images as Flate.

Ghostscript 10.07.1 (Ubuntu 26.10) and 10.08.0 (Debian sid) keep CCITT Group 4
with the same OCRmyPDF 17.10 call, so the defect is version-specific. Shipping
a newer Ghostscript would be a distribution decision and would not help users
on 26.04 who install scantpaper from their own archive. The fix belongs in
scantpaper.

## Goals / Non-Goals

**Goals:**

- Guarantee that a bilevel page selected for Group 4 is Group 4 in the final
  PDF on every supported Ghostscript version.
- Preserve the exact bitmap; the post-processing is a lossless re-encode.
- Cover both image XObjects and images the converter inlined, including very
  small page images that Ghostscript inlines instead of keeping as XObjects.
- Leave images that are already Group 4 or JBIG2, and every non-bilevel image,
  exactly as the converter wrote them.
- Keep a failure in the pass from failing an otherwise successful save.

**Non-Goals:**

- Changing the codec selected for a page, or the image bytes written before
  OCRmyPDF runs.
- Changing the PDF/A conversion, OCRmyPDF, or the installed Ghostscript.
- Restoring JBIG2 when the converter rewrites it; the JBIG2 pass already runs
  after this point and re-encodes bilevel images when requested.
- Rewriting images that are not 1-bit `DeviceGray`.
- Adding a dependency: `img2pdf` and `pikepdf` are already used by the save
  pipeline.

## Decisions

### Post-process after the text-layer embed

`_embed_text_layer()` is the only step that can rewrite the image streams; the
Group 4 pass runs immediately after it returns `True` and before
`_maybe_convert_to_jbig2()`. Running it earlier would be pointless because
Ghostscript has not touched the file yet; running it later would fight the
JBIG2 pass. The pass opens the output PDF with
`allow_overwriting_input=True` and saves in place only when it changed
something.

Alternatives considered:

- **Ship Ghostscript 10.07 or later.** Not in scantpaper's control on 26.04,
  and it would leave the library and the distribution free to regress again.
  Rejected.
- **Pass a different OCRmyPDF option.** There is no OCRmyPDF or Ghostscript
  option that keeps 1-bit images as CCITT on 10.06. `lossless` still yields
  Flate. Rejected after testing every accepted value.
- **Re-encode before the PDF/A step.** Ghostscript would rewrite the result
  anyway. Rejected.
- **Fail the save when Group 4 cannot be restored.** A save that is otherwise
  correct should still succeed; the user asked to save a document, not to
  enforce a particular stream codec. Rejected in favour of a warning.

### Detect by stream properties, not by recollection

The pass re-encodes an image only when all of these hold:

- `/BitsPerComponent` is 1.
- `/ColorSpace` is `/DeviceGray`.
- The filter list contains neither `/CCITTFaxDecode` nor `/JBIG2Decode`.

The last check makes the pass idempotent and leaves JBIG2 output alone. Colour,
grayscale, and already-bilevel images are skipped, which keeps the pass from
undoing a lossless Flate or JPEG stream that a non-bilevel page legitimately
uses.

### Decode with pikepdf and encode with img2pdf

`pikepdf.PdfImage(stream).as_pil_image()` decodes the stream to a 1-bit
`PIL.Image`. Saving that image as PPM and running `img2pdf.convert()` yields
the same CCITT Group 4 bytes the normal save path produces, so the two paths
cannot drift. The filter is written as the array form
`[/CCITTFaxDecode]` with `/DecodeParms` `[/K -1 /Columns W /Rows H
/BlackIs1 true]`, matching img2pdf. The existing `/Decode` array is removed so
the new stream's values are not remapped.

The temporary PPM lives in the save's temporary directory, so it is removed
with the rest of the working files.

### Handle inline images by promoting them to XObjects

Ghostscript inlines very small images into the page content stream instead of
keeping them as XObjects. `pikepdf.parse_content_stream()` returns a
`ContentStreamInlineImage` for those; the pass decodes it, writes a
`/ScantpaperImN` XObject to the page resources, and replaces the inline image
with a `/ScantpaperImN Do` instruction. The generated name is advanced past any
existing `/ScantpaperImN` entry so a conversion never overwrites a resource.
The content stream is rewritten only when at least one inline image changed.

### Best-effort call site

The call is wrapped in `try`/`except Exception` and logs a warning. A malformed
stream or an unexpected pikepdf failure leaves the PDF exactly as OCRmyPDF
produced it, which is the same output the user gets today on 26.04, rather than
turning a recoverable encoding mismatch into a failed save.

## Risks / Trade-offs

- [Re-encoding changes the stream] -> Group 4 is lossless and the encoder is
  the same one used on the normal path; tests decode the result and compare
  the 1-bit image.
- [A converted inline image changes page resources] -> The new XObject is
  added under a unique name and the instruction list preserves order; the page
  renders identically.
- [Large pages take longer to save] -> Only unconverted 1-bit images are
  decoded and re-encoded, and only on Ghostscript versions that rewrite them.
  Already-Group 4 output, which is every other supported series, is a no-op.
- [The pass masks a future Ghostscript regression] -> The spec now requires the
  final Group 4 encoding on every supported version, so the CI matrix keeps
  checking the observable result.
- [Coverage gate] -> Unit tests cover XObject and inline conversion, every skip
  condition, name collision, missing resources, a PDF with no images, the
  best-effort call site, and the warning path.

## Migration Plan

None. The pass runs at save time on the assembled PDF, so existing sessions
save correctly on the next save. Reverting the change restores the previous
behaviour without altering stored data.

## Open Questions

None.
