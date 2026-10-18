## Why

When saving a PDF with the explicit JBIG2 compression option, only pages
that are already bilevel are embedded with JBIG2; grayscale and colour
pages silently fall back to lossy JPEG. Users selecting JBIG2 expect
G4-like semantics - every page binarized so the whole document is
JBIG2-encoded - but instead get JPEG output for the very pages (grayscale
scans, unpapered pages) where JBIG2 would help most, with nothing in the
UI or README explaining the fallback.

## What Changes

- The `jb2` compression option now resolves continuous-tone pages
  (8-bit grayscale, RGB, CMYK) to CCITT Group 4 encoding instead of
  JPEG, so each page is thresholded to bilevel exactly as an explicit
  `g4` save does; the existing JBIG2 post-pass then upgrades the Group 4
  streams to lossless JBIG2.
- Pages with an alpha channel continue to be encoded losslessly with
  Flate (JBIG2 cannot represent them).
- Automatic compression and the bilevel codec preference are unchanged:
  continuous-tone pages under `auto` still embed as JPEG.
- The Quality setting no longer affects pages saved with the `jb2`
  option, matching explicit `g4` behaviour.
- README documents that the JBIG2 option thresholds non-bilevel pages.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `pdf-image-compression`: the JBIG2 compression option requirement
  changes - continuous-tone pages saved with `jb2` are thresholded to
  bilevel and embedded with lossless JBIG2 (via Group 4) instead of
  JPEG, matching explicit Group 4 semantics.

## Impact

- `src/scantpaper/page.py`: `resolve_pdf_codec` maps `jb2` for
  continuous-tone pages to `PDF_CODEC_G4` rather than `PDF_CODEC_JPEG`;
  docstring update.
- `src/scantpaper/tests/test_04_page.py`: codec-resolution expectations
  for `jb2` with L/RGB/CMYK change from JPEG to G4; the float-quality
  `jb2` test now exercises the Group 4 path.
- `src/scantpaper/savethread.py`: no code change; the existing
  `_convert_bilevel_images_to_jbig2` pass upgrades the resulting Group 4
  streams. Its `_JBIG2_OPTIONS` comment about grayscale input remains
  accurate.
- `README.md`: document the thresholding behaviour of the JBIG2 option.
- No dependency changes; the `jbig2` encoder requirement is unchanged.
