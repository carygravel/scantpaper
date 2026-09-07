## Why

Thumbnails of bilevel (1-bit) and palette page images — the common output of
scanner/OCR PDFs such as JBIG2-encoded scans — collapse to two shades because
PIL's `resize` keeps such images bilevel, discarding all anti-aliasing. Page
previews become illegible even though `improve-thumbnail-generation` added
high-quality resampling. The downscale algorithm was never the problem; the
missing step is anti-aliasing for `mode == "1"` / `mode == "P"` sources before
scaling (verified: the same 1-bit JBIG2 page yields a 2-shade thumbnail on the
current code vs ~125 anti-aliased grey shades when converted to grayscale
first).

## What Changes

- `Page.get_pixbuf_at_scale` converts bilevel (`mode == "1"` → `"L"`) and
  palette (`mode == "P"` → `"RGB"`) page images before the existing
  decimate-then-LANCZOS scaling, so thin text strokes survive as anti-aliased
  grey and the thumbnail matches gscan2pdf's readability.
- The reduce + LANCZOS downscale for grayscale/colour pages is unchanged; mode
  conversion affects the thumbnail only, never the stored page image.
- Regression test: a bilevel source produces an anti-aliased thumbnail (more
  than two distinct shades), not a 2-tone collapse.
- README: thumbnail note clarified to mention legible bilevel previews.

## Capabilities

### New Capabilities

- none

### Modified Capabilities

- `thumbnail-generation`: extend "Thumbnails are generated with high-quality
  resampling" — thumbnails of bilevel/palette pages SHALL be anti-aliased
  rather than collapsing to two shades.

## Impact

- `src/scantpaper/page.py`: `get_pixbuf_at_scale` only (adds a mode
  conversion for `"1"`/`"P"`; stored images and depth/mode semantics
  elsewhere are untouched).
- `src/scantpaper/tests/test_04_page.py`: new regression test; the
  reduce+LANCZOS and box-size tests remain valid.
- README.md: wording update of the Thumbnails feature bullet.
- No dependencies added.