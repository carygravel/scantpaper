# Design

## Context

See `proposal.md` for motivation. `page.resolve_pdf_codec(image, compression)`
maps a colour model to a codec; mode `L` and other continuous-tone modes
resolve to JPEG under `auto`. `page.to_stored_bytes` stores mode `L` as JPEG at
quality 92. Import decodes the source once; save re-encodes from the stored
blob. `savethread._estimate_page_pdf_size` also calls `resolve_pdf_codec`. The
project keeps constants shared between code and tests in `const.py`.

## Goals / Non-Goals

**Goals:**

- A posterised (low-colour-depth) grayscale page is stored and written
  losslessly, and is smaller for it.

**Non-Goals:**

- Colour/RGB posterised images.
- Changing JPEG for genuinely continuous-tone pages.
- Changing bilevel or alpha-channel handling, or the explicit `jpg`/`jp2`
  choices.

## Decisions

### Decision: define low colour depth as <= 16 distinct intensity levels

Add `LOW_COLOUR_DEPTH_LEVELS = 16` to `const.py`, so code and tests share one
value, and a predicate that counts distinct levels with `Image.histogram()` on
an `L`-mode image. Posterised scans use 3-4 bits; 16 sits above the reported 8
levels and far below the ~256 of continuous tone. `histogram()` is C-level, so
there is no per-pixel Python loop.

### Decision: apply the predicate at import and at save

Use the same predicate in `to_stored_bytes`, to store such an image as PNG
(preserving the levels and, for these pages, shrinking the blob), and in
`resolve_pdf_codec`, to resolve automatic compression to Flate. Both call sites
must agree, and the count must be taken before any lossy re-encode. Counting
the stored blob instead was rejected: the import-time JPEG has already smeared
the levels, so the predicate would not fire.

### Decision: scope the predicate to grayscale

Only grayscale continuous-tone pages resolve differently. Alpha and bilevel
rules are unchanged, and the explicit `jpg` and `jp2` options still force their
codecs.

## Risks / Trade-offs

- A continuous-tone image that happens to carry <= 16 levels is treated
  losslessly and may be larger than JPEG. Mitigation: such an image is
  posterised, where lossless is accurate and usually smaller.
- One histogram per page at import and save. Mitigation: `histogram()` is
  C-level, and save already re-encodes the full image.
- Sessions stored before this change keep JPEG blobs, so the save-time
  predicate does not fire for them. Mitigation: acceptable - they behave as
  before, and re-importing a page adopts the new behaviour.
