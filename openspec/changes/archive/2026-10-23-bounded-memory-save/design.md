# Design

## Context

The reproduction (see `proposal.md` - Why) shows two waste sites in the
current code, both grounded in the log:

- `Page.__init__` (`src/scantpaper/page.py`) logs
  `len(self.image_object.tobytes())` on every construction. The arguments
  to a log call are evaluated even when the record is dropped, so simply
  loading a page always performs a full-image decode. The decoded buffer
  then stays cached on the PIL image. The `New page size ...` lines in the
  log confirm 1317 full decodes for one 330-page session.
- `_assemble_pdf` (`src/scantpaper/savethread.py`) calls `get_page()` for
  every page, appends the resulting `Page` objects to a list, and returns
  them. `do_save_pdf` keeps that list alive while it writes the hOCR
  sidecars and then while ocrmypdf embeds the text layer and Ghostscript
  converts to PDF/A. The list is needed only for `page.text_layer`.

The default save re-embeds the unmodified stored JPEG bytes verbatim
(`write_image_for_pdf` fast path), so on this path the pixel data is never
touched. Both waste sites are pure overhead that scales with page count.

## Goals / Non-Goals

Goals:

- Constructing or loading a page never decodes its full-size image; decode
  happens only at the first genuine pixel consumer.
- A PDF save holds at most one page's image data at a time and releases it
  as soon as that page's contribution (temporary image plus hOCR sidecar)
  is written, so the save does not keep earlier pages resident while
  ocrmypdf and Ghostscript run.
- The saved output is unchanged: same bytes, same text layer, same
  metadata (see `memory-bounded-page-images` spec).

Non-Goals (each is a potential follow-up, not this change):

- Reducing ocrmypdf's own pipeline peak (the PDF/A rewrite through
  Ghostscript and pikepdf linearization), which remains the floor for very
  large documents.
- Changing what is stored (SQLite blobs stay as today), or how thumbnails
  are produced.
- Introducing page-count or memory heuristics, warnings, or chunked
  saves that process a range of pages per batch.

## Decisions

### D1. Derive the logged size instead of decoding it

Replace the `tobytes()` argument in the `New page size` log with a size
computed from the header-only fields: `width * height * depth`, where
depth comes from the existing `MODE2DEPTH` mapping (`page.py`, bits per
pixel). PIL reads width/height/format from the file header without
decoding the pixel payload.

Rationale: the log line is genuinely useful diagnostics - the decoded byte
count is exactly how a large-document problem is recognised (this change
was diagnosed from those lines). Dropping the log to remove the decode
would throw away that signal; deriving the number keeps it at zero cost.
The computed value equals the decoded size for `1`/`L`/`RGB`/`RGBA`
modes, which are the ones that matter.

Alternatives considered:

- Remove the log line entirely. Rejected: loses the diagnostic.
- Keep `tobytes()` but guard on log level. Rejected: the option is real
  but the eager argument evaluation is the bug; providing a cheap value
  removes the footgun for good.

### D2. Save processes pages one at a time and releases each

Restructure `_assemble_pdf` so that a page's lifetime ends within one loop
iteration:

- Inside the existing per-page loop, after `write_image_for_pdf()` writes
  the temporary file, write that page's hOCR sidecar (`.hocr` + `.json`)
  from `page.text_layer` immediately, then drop the `page` reference. The
  next iteration replaces it; CPython refcounting frees the image bytes
  buffer as soon as the loop variable is reassigned.
- Do not accumulate `Page` objects. The loop additionally collects only the
  per-page `resolution` needed by `img2pdf`'s `layout_fun`, which is a
  tuple, not an image.
- `_assemble_pdf` returns those resolutions instead of `list[Page]`, and
  `do_save_pdf` drops the separate hOCR sidecar loop entirely.

This merges the previous two-page list usage into the single pass. The
sidecar files land in `outdir` as today, before `_embed_text_layer` runs,
which satisfies the current ordering (sidecars must exist before
ocrmypdf's hOCR-to-PDF pipeline). `export_hocr()` needs only the text
layer (see `Bboxtree.to_hocr`), so no pixel or geometry access is lost.

Alternatives considered:

- Two-pass with lightweight records: `_assemble_pdf` returns a list of
  `(text_layer, ...)` tuples and `do_save_pdf` keeps its own sidecar loop.
  Rejected: same memory result but keeps two passes over the pages and
  introduces a record type that could accidentally carry an image later.
- Reloading pages from SQLite in a second loop. Rejected: re-reads ~1 GB
  of blobs for data already in hand.

### D3. Preserve the verbatim fast path and only decode when required

`write_image_for_pdf` already avoids a decode for unmodified JPEGs. Keep
that branch untouched. For codecs that need pixels (downsample, `g4`,
`jp2`, `flate`, or a re-encoded `jpeg`), the page is decoded inside
`write_image_for_pdf` and released at the end of the same iteration, so
even the re-encode path holds one page at a time.

### D4. Explicit collection is not required upfront

Dropping the references is enough under CPython's refcounting; PIL's
decoded data is freed with the image object. Add `gc.collect()` before
`_embed_text_layer` only if a measurement pass shows cycles keeping pages
alive (the undo/redo snapshots in `docthread` are a candidate). Treat as a
follow-up tuning step, not part of the structural change.

## Risks / Trade-offs

- **Hidden caller expects a decoded image after construction** ->
  Mitigation: audit showed every pixel consumer (`get_pixbuf_at_scale`,
  `do_tesseract`, brightness/contrast, `_equalize_resolution`)
  decodes itself; the default save never touches pixels. A regression test
  asserts a freshly constructed page from stored bytes is not decoded
  until a pixel operation.
- **Merging the sidecar loop changes progress/message timing** ->
  Mitigation: no user-visible ordering contract exists between temp image
  and sidecar writes; both must precede embedding, which the single pass
  preserves. Existing save-progress messages are unchanged.
- **Output drift from the current code** -> Mitigation: saves are already
  well covered by `test_1111_save_pdf.py`; verbatim-JPEG and text-layer
  round-trip tests guard byte content. Scenarios in the spec pin lazy
  decode and one-at-a-time release.
- **The change does not fully bound memory for documents whose ocrmypdf
  pipeline (Ghostscript PDF/A, pikepdf linearize) alone exceeds RAM** ->
  Mitigation: explicitly scoped out (Non-Goals). This change removes the
  ~21 GB self-inflicted floor; a document that still fails after it fails
  inside the tooling, and that is a separate change.

## Migration Plan

- Implement in two independent steps, each shippable alone: D1 first, then
  D2. D1 is a one-line behavioural fix with its own test; D2 is the save
  restructure with its own tests. Both together close the reported case.
- No data migration: SQLite schema and stored blobs are untouched.
- Rollback is a revert of the corresponding commit; neither step changes
  file formats.
- README note describing that large PDF saves no longer exhaust memory and
  that page images are decoded on demand.

## Open Questions

- Whether to also bound memory in the display path (decode only the
  visible page). Deferred: not needed for the reported bug; a natural
  future requirement of the same capability.
- Whether the ocrmypdf pipeline's own peak (PDF/A, linearization) should
  be reduced for very large documents. Deferred: independent of this
  change's approach and task list.
