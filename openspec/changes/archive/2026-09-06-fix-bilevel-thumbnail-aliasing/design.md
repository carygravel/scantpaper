## Context

See proposal.md - Why. The current `Page.get_pixbuf_at_scale` already runs the
decimate-then-LANCZOS pipeline for grayscale/colour pages, but pages whose
`image_object.mode` is `"1"` (bilevel, e.g. JBIG2 scans imported as PBM) or
`"P"` (palette) keep their mode through PIL's `resize`, so every anti-aliasing
shade is discarded and the 100 px thumbnail collapses to the two original
tones. `_REDUCE_UNSUPPORTED` in `page.py` already skips `Image.reduce` for
`"1"` and `"P"` because PIL's C `reduce` raises on them.

## Goals / Non-Goals

**Goals:**
- Bilevel and palette thumbnail sources render as anti-aliased grayscale/colour
  using the existing decimate-then-LANCZOS pipeline.
- Fix the two-shade collapse without touching the stored page image, save
  formats, or depth semantics.

**Non-Goals:**
- Changing the downscale algorithm for grayscale/colour pages.
- Changing how bilevel pages are stored or their `get_depth()` value.
- Gdk-pixbuf-based scaling (option 1/2) or a PIL pyramid; the committed
  reduce+LANCZOS path is retained.

## Decisions

### D1: Convert the thumbnail source mode before scaling
In `get_pixbuf_at_scale`, alongside the existing `mode == "I"` → `"L"`
conversion, convert `mode == "1"` → `"L"` and `mode == "P"` → `"RGB"` before
the `image.size != (width, height)` check and any resize.

Rationale: after conversion the normal reduce+LANCZOS path applies, and PIL's
filters anti-alias against an 8-bit intermediate, restoring the grey shades at
text strokes. The conversion is local to the thumbnail and never re-encoded
back to the page. Verified empirically: the same 1-bit JBIG2 page yields a
2-shade thumbnail on the current code, ~125 shades with the conversion, and
~128 shades via gdk-pixbuf (the gscan2pdf behaviour we are matching).

Alternatives considered:
- **Let gdk-pixbuf scale the full-res file (gscan2pdf parity)**: auto-fixes
  bilevel but rewrites the full-res page to a temp PNG and decodes it; drops
  the reduce+LANCZOS perf benefit and larger change than needed.
- **Single LANCZOS on the bilevel image**: still collapses to two shades (PIL
  keeps mode `"1"` in `resize`), so no fix at all.
- **Dithering before resize**: adds noise and complexity; unnecessary when
  converting to 8-bit first.

### D2: Where the conversion happens
Apply the conversion unconditionally before the size check (not only when a
resize will happen), mirroring the existing `mode == "I"` conversion, so the
code path is uniform and mode-normalised before either scaling or box-fill.

### D3: `_REDUCE_UNSUPPORTED` becomes narrower
With `"1"` and `"P"` converted away, only the 16-bit integer modes
(`"I;16"`, `"I;16B"`, `"I;16L"`, `"I;12"`) remain unsupported by
`Image.reduce`. Keep the guard for those; drop `"1"` and `"P"` from the set to
reflect the new invariants (they can no longer reach `reduce`). No behaviour
change to the `"I"`/`"I;16"` handling.

## Risks / Trade-offs

- [Palette pages with a colour palette converted via a simple mode choice] →
  `"P"` → `"RGB"` preserves colour exactly; `"1"` → `"L"` matches grayscale.
- [Mode conversions change thumbnail bytes/hashes for existing pages] →
  thumbnails are derived data in the session DB; they are regenerated on
  import/modification and stored alongside, so no migration is needed.
- [A palette image with no default palette hitting `"P"` → `"RGB"`] → PIL
  `convert` handles the default palette; existing `"I"` conversion already
  relies on PIL for the same class of edge case.