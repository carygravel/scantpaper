# Proposal

## Why

On Ubuntu 26.04 and 26.10, saving a PDF with the downsampling option for a
bilevel page fails. The Ubuntu builds of Pillow 12.1 (26.04) and 12.3
(26.10) raise a bare `SystemError` from their nearest-neighbour resampler.
Pillow always resamples mode `1` and `P` images with nearest-neighbour,
whatever filter is requested, so any downsample of a bilevel or palette page
crashes instead of completing. The fault is a bad Ubuntu backport of an
upstream commit (`CVE-2026-112402.patch`) written for Pillow 13, where
`ImagingTransform()` returns an `int` instead of the output image, so the
backported success test is inverted in the 12.x trees. The PyPI builds of
the same versions are unpatched upstream releases and work, as do Pillow
10.2 on Ubuntu 24.04 and current upstream Pillow, which is why only the
26.04 and 26.10 jobs fail.

## What Changes

- Add a page-image resize helper that resamples a bilevel page as 8-bit
  grayscale with a box filter and thresholds it back to one bit.
- Resample palette pages in their true colours, keeping transparency.
- Use the helper for PDF downsampling and for the DjVu resolution
  equalisation that also resizes page images.
- Add regression tests for bilevel and palette downsampling.
- Document the behaviour in the changelog.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `pdf-image-compression`: downsampling SHALL resample bilevel and palette
  pages without failing and without changing a bilevel page's bit depth.

## Impact

- `src/scantpaper/page.py`: `_resize_image()` used by `write_image_for_pdf()`
  and `_equalize_resolution()`. The helper's docstring records the affected
  Pillow versions (Ubuntu's 12.1 on 26.04, 12.3 on 26.10) and that it can be
  reduced to a plain `Image.Image.resize()` once both series are EOL.
- `src/scantpaper/tests/test_04_page.py`: regression coverage.
- `openspec/specs/pdf-image-compression/spec.md`: spec delta for downsampling
  bilevel and palette pages.
- `changelog.md`: note that downsampling completes on every supported series.
- No change to the target-resolution arithmetic, codec selection, the stored
  page image, or dependencies.
