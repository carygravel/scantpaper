## Why

Opening a PDF created from a transparent image adds an extra page. The PDF stores
the image plus a separate soft mask (`smask`) for its alpha channel, and
`pdfimages` extracts both. scantpaper imports every extracted file as a page,
assuming one image per page, so the alpha mask becomes a phantom page (issue #43).

## What Changes

- PDF import parses `pdfimages -list` output to discover the images on each page
  together with their type.
- Only entries whose type is `image` are imported as pages; `smask` and `stencil`
  (mask) entries are skipped and their extracted files are cleaned up.
- Extracted files are correlated with `-list` entries by index, because
  `pdfimages` restarts extracted-file numbering at `x-000` for each page while
  the `-list` `num` column is a global document counter.
- Each imported image uses its own resolution from `-list` rather than the first
  image on the page.
- The "scantpaper expects one image per page" warning is based on the number of
  non-mask images, so ordinary image+smask pages no longer trigger it.

## Capabilities

### New Capabilities

- `import-pdf-images`: Defines how scantpaper imports pages from a PDF by
  extracting its images, including which images are imported and how the
  one-image-per-page expectation is enforced.

### Modified Capabilities

<!-- None: existing specs cover PDF metadata only and are unaffected. -->

## Impact

- `scantpaper/importthread.py`: `_do_import_pdf` reworked to parse `-list`,
  filter mask images, and correlate files by index.
- `scantpaper/tests/test_importthread.py`: unit tests for the new parsing and
  filtering logic.
- An integration test that imports a PDF created from a transparent image and
  asserts a single page is created.
- Requires `pdfimages` (poppler-utils) with `-list` support, already a
  dependency.
