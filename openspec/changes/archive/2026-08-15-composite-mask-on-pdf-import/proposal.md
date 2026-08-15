## Why

A PDF page created from a transparent image stores the image data and its soft
mask (alpha channel) as separate XObjects. The previous change skipped mask
images so they are no longer imported as extra pages, but the imported image is
still the *uncomposited* color data: semi-transparent anti-aliased edge pixels
render as solid dark, so the imported page looks fatter and blockier than the
PDF as shown by a viewer (e.g. evince composites the image with its mask over
the page background).

## What Changes

- When a PDF page contains an `image` entry with an associated soft mask
  (`smask`) entry, composite the image over a white background using the mask
  at import time, and import the single composited result as the page instead
  of the raw image.
- The mask image is still never imported as its own page, and mask files are
  cleaned up after compositing.
- Add a small Netpbm (PBM/PGM/PPM) compositing helper so no new dependency is
  required (pdfimages emits Netpbm formats).

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `import-pdf-images`: the requirement "Mask images are not imported as pages"
  is extended so that mask images are composited with their image over white
  rather than merely skipped, producing an imported page that matches the
  rendered PDF; a new requirement documents the composited appearance.

## Impact

- `scantpaper/importthread.py`: rework `_correlate_pdf_images` / page import to
  composite image+mask over white.
- `scantpaper/tests/test_importthread.py`: new unit tests for the Netpbm
  compositing helper and updated PDF import tests.
- `changelog.md`: user-visible fix note.
- No new dependencies.
