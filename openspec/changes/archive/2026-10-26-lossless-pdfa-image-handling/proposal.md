# Proposal

## Why

A page saved with a lossless compression option can still come out lossy and
larger than it should. scantpaper assembles the PDF with img2pdf and then hands
it to OCRmyPDF to graft the text layer and produce PDF/A. On OCRmyPDF 17.5 and
earlier the PDF/A conversion lets Ghostscript transcode lossless grayscale and
colour images to JPEG, even at OCRmyPDF's lowest optimization level, which is
what scantpaper requests. On OCRmyPDF 17.6 and later the same call keeps
lossless images. scantpaper passes no explicit setting, so whether a lossless
save stays lossless depends entirely on the installed OCRmyPDF version.

A real report showed it: a 624 KB, 8-level grayscale TIFF saved with the
lossless option became a 1.1 MB PDF whose single image was a JPEG, because the
machine ran OCRmyPDF 16.13. The same input and option on OCRmyPDF 17.10
produce a 653 KB PDF with the Flate image preserved. The user chose lossless
and did not get it, for a reason they could not see.

## What Changes

- Request lossless image compression from the OCRmyPDF hOCR-to-PDF call, so the
  PDF/A conversion never transcodes scantpaper's lossless image streams to
  JPEG, on every supported OCRmyPDF version.
- Keep the request scoped to the PDF/A conversion. It must not change the codec
  scantpaper chooses for a page, nor the image bytes it writes before the call.
- A save whose chosen codec is lossless (Flate, or a bilevel stream that is
  already lossless) SHALL yield a PDF whose page image is still that lossless
  codec.
- Do not regress the common JPEG case: a page image scantpaper wrote as JPEG
  SHALL stay JPEG rather than be re-encoded to a lossless codec, which would
  only inflate it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `pdf-image-compression`: a losslessly written page image survives the
  OCRmyPDF PDF/A conversion unchanged, and scantpaper asks for lossless PDF/A
  image handling explicitly rather than inheriting a version-dependent default.

## Impact

`savethread.py` (`_embed_text_layer`, the `ocrmypdf.api._hocr_to_ocr_pdf`
call). New reliance on the `pdfa_image_compression` option of the OCRmyPDF API;
the option exists since OCRmyPDF 16, but its `auto` meaning changed in 17.6, so
the request must be explicit. On older OCRmyPDF the `lossless` value may
re-encode an existing JPEG, which is why the JPEG-passthrough clause above
matters; design will decide whether to pin the value unconditionally or only
for pages that were written losslessly. Tests in `tests/test_savethread.py` and
`tests/test_1111_save_pdf.py`. No change to `page.py` codec selection or to the
stored image format.
