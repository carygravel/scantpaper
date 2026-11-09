# Proposal

## Why

On Ubuntu 26.04, which ships Ghostscript 10.06, saving a bilevel page as
Group 4 produces a PDF whose image is Flate-encoded instead. scantpaper writes
the page with img2pdf, then asks OCRmyPDF to graft the text layer and produce
PDF/A with lossless image handling. Ghostscript 10.06 ignores that request for
1-bit images and rewrites them as Flate during the PDF/A conversion. Later
Ghostscript releases (10.07 and 10.08) preserve CCITT Group 4, so the same
document saves correctly on every other supported series but loses its chosen
encoding on 26.04.

The user-visible effect is not merely a larger file. Group 4 is the encoding
the **Automatic** preference and the explicit **G4** option promise, the
bilevel tests assert it, and the resolute CI job fails on it. A save should
produce the encoding the user selected regardless of which Ghostscript the
distribution happens to ship.

## What Changes

- After a successful text-layer embed, re-encode any page image that is still
  an unconverted 1-bit `DeviceGray` image as CCITT Group 4 before the save
  completes.
- Cover both image XObjects and images that the PDF/A converter inlined into
  the page content stream; an inlined image becomes a named XObject.
- Leave images that are already CCITT Group 4 or JBIG2 untouched, and touch no
  image that is not 1-bit gray.
- Treat the restoration as best-effort: if it fails, log a warning and keep the
  saved PDF rather than failing the whole save.
- Keep the existing lossless PDF/A request, which still prevents Ghostscript
  from transcoding grayscale and colour images to JPEG.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `pdf-image-compression`: a bilevel page selected for Group 4 SHALL still be
  Group 4 in the final PDF when the PDF/A converter rewrites it with another
  lossless codec, and an image that is already Group 4 or JBIG2 SHALL NOT be
  re-encoded.

## Impact

- `src/scantpaper/savethread.py`: new Group 4 restoration helpers and their
  call in `do_save_pdf` after `_embed_text_layer` and before the JBIG2 pass.
- `src/scantpaper/tests/test_savethread.py`: unit coverage for XObject and
  inline conversion, the skip cases, and the best-effort call site.
- `openspec/specs/pdf-image-compression/spec.md`: spec delta extending the
  lossless-PDF/A requirement.
- `README.md` and `changelog.md`: document that Group 4 survives the PDF/A
  conversion even when the converter rewrites it.
- No change to codec selection, the stored image format, the session schema,
  or dependencies. The pass uses `img2pdf` and `pikepdf`, both already
  imported by `savethread.py`.
