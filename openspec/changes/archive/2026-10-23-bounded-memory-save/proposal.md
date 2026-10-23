# Proposal

## Why

Saving a large scanned document crashes the whole application with an
out-of-memory kill ("Getötet"). A reproduced 330-page case of 3968x5356 RGB
scans (~64 MB decoded per page) reached a ~21 GB resident footprint and was
SIGKILLed during the Ghostscript PDF/A pass of the save. Two design choices
drive that footprint: every `Page` is fully decoded just to log its byte
size, and the PDF save keeps every decoded page alive for the entire
pipeline instead of releasing each page after its own contribution is
written. The images are never used as pixels on that path - the output
re-embeds the stored JPEG streams verbatim and the text layer is separate -
so the decode and the retention are pure waste that scales with page count.

## What Changes

- A page image is no longer decoded eagerly inside `Page` construction
  purely to report its size; the logged size is derived from the image's
  width, height and pixel depth, and the image decodes lazily on first
  pixel access (thumbnail, OCR, display, or re-encode).
- The PDF save writes each page's temporary image, applies any required
  encoding, and releases the page's image data immediately afterwards. The
  save no longer retains all page images while ocrmypdf embeds the text
  layer and converts to PDF/A; the hOCR sidecar phase reads only each
  page's lightweight text layer and metadata.
- As a result, saving a many-page document needs memory proportional to a
  handful of pages rather than to the whole document, so large saves
  complete instead of being killed by the OOM killer.
- **BREAKING**: none. No configuration, CLI, database format, or output
  file changes. The observable change is that large PDF saves stop running
  out of memory (and the save path no longer performs hundreds of
  full-image decodes it never uses).

## Capabilities

### New Capabilities

- `memory-bounded-page-images`: Governs how full-size page image data is
  held in memory - a page's pixel data is decoded only when a consumer
  actually needs it and is released once it has no live consumer, so
  documents with many high-resolution pages do not require keeping every
  image decoded at once. This capability can own related future
  requirements (e.g. releasing displayed pages on navigation, bounded
  memory in other bulk operations).

### Modified Capabilities

None. Existing specs cover behaviour that does not change here:
`image-storage-format` (storage formats and verbatim embedding),
`pdf-size-limit-warning` (the 2 GiB output-size guard),
`save-searchable-text-layer` (text-layer embedding),
`thumbnail-generation` (thumbnails are still produced from downscaled
images). None of their requirements are altered by this change.

## Impact

- `src/scantpaper/page.py`: remove the forced full decode in `Page.__init__`
  and replace the `tobytes()`-based size log with a size computed from
  width x height x depth.
- `src/scantpaper/savethread.py`: `_assemble_pdf` / `do_save_pdf` release
  each page's image after its temporary file is written, and keep only
  lightweight per-page records (identifier, text layer, resolution, page
  size) for the hOCR sidecar phase.
- Callers that currently assume `Page` construction decodes the image
  (search for `image_object.<pixel op>` and any reliance on eager decoding).
- Tests: new tests asserting a page stays undecoded until first pixel use
  and that a PDF save releases page images; existing page and save tests may
  be adjusted if they relied on the eager decode.
- No new dependencies. No change to the SQLite schema or output artefacts.
- README note covering the restored ability to save large documents,
  per the project's change-visible-to-users convention.
