## Context

Saving a PDF with the explicit `jb2` option currently resolves
continuous-tone pages to JPEG (`resolve_pdf_codec`, page.py:98-99), so
only pages that are already bilevel reach the JBIG2 post-pass
(`_convert_bilevel_images_to_jbig2`, savethread.py:928); grayscale and
colour pages stay lossy JPEG. Explicit `g4` already thresholds every
page via `_to_bilevel` (page.py:130-135, 546-547). The JBIG2 post-pass
selects only 1-bpc streams (ocrmypdf `extract_image_jbig2`,
`bits_per_component == 1`), so any encoding that produces bilevel Group
4 streams is upgraded automatically. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**

- Explicit `jb2` saves produce JBIG2-encoded output for bilevel and
  continuous-tone pages alike, with the same thresholding as explicit
  `g4`.
- Minimal change: reuse the existing Group 4 write path and the
  existing JBIG2 post-pass rather than adding a conversion step.

**Non-Goals:**

- Changing automatic compression or the bilevel codec preference;
  continuous-tone pages under `auto` keep embedding as JPEG.
- Changing how `_to_bilevel` thresholds (the 0.4 cutoff stays).
- Lossy JBIG2 (symbol dictionaries, `jbig2_lossy`) or quality tuning
  for JBIG2 output.
- DjVu output; `cjb2` binarization is a separate, untouched path.

## Decisions

### Resolve `jb2` for continuous-tone pages to Group 4, not to a new threshold step

`resolve_pdf_codec` changes `compression == PDF_CODEC_JBIG2` from
`_codec_for_colour_model(image, PDF_CODEC_JPEG)` to
`_codec_for_colour_model(image, PDF_CODEC_G4)`. Alpha pages still
resolve to Flate (`_codec_for_colour_model` handles this), so
`write_image_for_pdf` needs no change: it already thresholds and writes
1-bit PNM for `PDF_CODEC_G4`, and the post-pass upgrades those streams
to JBIG2.

- Alternative considered: thresholding inside the JBIG2 post-pass
  (widening ocrmypdf's selection to 8-bpc images). Rejected: it
  duplicates the threshold logic, bypasses `write_image_for_pdf`'s
  tested G4 path, and ocrmypdf's helper API is not designed for
  injecting custom bilevel conversions.
- Alternative considered: thresholding only grayscale (`L`) pages and
  keeping colour as JPEG. Rejected as arbitrary: a colour text scan
  benefits from JBIG2 just as much, and G4 sets the precedent that an
  explicit bilevel-codec choice means "binarize everything".

### Keep the auto path keyed on the bilevel preference, not on `jb2` reaching the resolver

`_jbig2_requested` (savethread.py:916-924) checks `compression == "jb2"`
or `auto` plus the `bilevel compression` preference. Automatic saves
never pass `"jb2"` into `resolve_pdf_codec`, so the resolver change
cannot affect the auto path. No guard is needed.

### Document, don't warn, at save time

The thresholding is destructive and silent for continuous-tone pages.
A confirmation dialog is not justified: explicit `g4` has always
thresholded silently, and the tooltip/README now describe the
behaviour. Adding a dialog would also need a spec change beyond this
one behaviour.

## Risks / Trade-offs

- [Explicit `jb2` becomes destructive for continuous-tone pages, as
  `g4` already is] → Same semantics as the sibling option, described in
  the save dialog tooltip and README; users wanting lossless
  continuous-tone output keep `auto` or `jp2`.
- [A user's stored configuration has no `jb2` default to migrate;
  `jb2` is only reachable via the save dialog each time] → No config
  migration needed. The "JBIG2 encoder unavailable" scenario still
  defines fallback behaviour for a stored `jb2` value.
- [Tests currently pin `("L", "jb2", PDF_CODEC_JPEG)` etc.] → Updated
  in the same change; the float-quality `jb2` test moves from asserting
  a JPEG stream to asserting a bilevel PNM/G4 path.
- [Slightly larger intermediate PDF before the post-pass runs when the
  encoder is missing but a stored `jb2` value slips through] → The
  post-pass is best-effort; output remains a valid Group 4 PDF, which
  is still smaller than JPEG for text.

## Migration Plan

Single-commit change; no data migration. Rollback is reverting the
resolver line and tests.

## Open Questions

(none)
