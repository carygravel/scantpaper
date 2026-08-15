## Context

See `proposal.md` - Why. After the previous change, PDF import skips mask
images so a transparent-image PDF imports one page, but that page is the raw
uncomposited image: its semi-transparent anti-aliased edge pixels are solid
dark, so it looks fatter/blockier than the PDF as rendered by evince. A viewer
composites the image over the page background using the soft mask.

Current state: `scantpaper/importthread.py` extracts images per page with
`pdfimages`, correlates extracted files with `-list` entries by sorted index
(`_correlate_pdf_images`), imports each `image`-type file and deletes the
`smask`/`stencil` files. `Page` opens every page via `PIL.Image.open`, so
Pillow is already a runtime dependency (`scantpaper/page.py`).

## Goals / Non-Goals

**Goals:**
- When a PDF page has an `image` entry with a paired `smask`, import one page
  whose appearance matches the PDF rendered by a viewer (image composited over
  white using the mask).
- Keep the imported page count and the one-image-per-page warning unchanged.
- No new runtime dependencies.

**Non-Goals:**
- Compositing `stencil` (1-bit) masks - those continue to be skipped as today.
- Compositing over non-white page backgrounds - assume white (correct for
  scanned documents).
- Rendering pages with `pdftoppm` instead of extracting images.
- Declaring Pillow in `pyproject.toml` (pre-existing gap: `page.py` already
  imports it; out of scope here).

## Decisions

### D1: Composite with Pillow
Use `PIL.Image.composite(image, white_background, mask)` in a new module-level
helper `_composite_over_white(image_path, mask_path)` in `importthread.py`.
Pillow reads and writes Netpbm (P4/P5/P6) natively and is already required at
runtime by `page.py`, so no dependency is added and no format parsing is
written by hand.
- *Alternative rejected:* hand-written Netpbm parser - more code, more tests,
  reinventing the wheel.

### D2: Pair an image with the smask that immediately follows it in `-list`
`pdfimages -list` does not expose the image-to-mask `SMask` reference, but
poppler lists a soft mask immediately after its image. `_correlate_pdf_images`
pairs `entries[i]` (type `image`) with `entries[i+1]` (type `smask`) and
returns that mask's extracted filename alongside the image.
- *Alternative rejected:* resolving the `SMask` object reference via `pikepdf`
  - robust but heavy; the `-list` ordering covers the practical cases.
- Unpaired `smask`/`stencil` files are still deleted; paired masks are kept
  until after compositing.

### D3: Composite in place, fall back to the raw image
Overwrite the extracted image file with the composited result (same filename,
so the `image_format[ext]` mapping and `Page(filename=...)` plumbing are
unchanged), then delete the mask file. If compositing fails (size mismatch,
unreadable files, no mask), import the raw image exactly as today and skip the
mask - no regression.

### D4: Only `smask` types are composited
Per the reported issue; `stencil` masks remain skipped by the previous change.

### D5: Resolution and warning unchanged
Each imported page keeps the resolution from its own `-list` entry; the
one-image-per-page warning still counts non-mask images only, so a single
image+mask pair does not warn.

## Risks / Trade-offs

- [Assumption: the mask immediately follows its image in `-list`] → Matches
  poppler behavior; if it ever does not, the mask is treated as unpaired and
  the previous (correct) skip behavior applies, so no regression.
- [Composite over white vs a colored page background] → For scanned documents
  the background is white; documented limitation.
- [Compositing alters pixel data] → Verified against `pdftoppm` output: the
  composite over white agrees with evince's render at ~98.6% (mean diff ~3.4 of
  255), vs ~90.4% for the raw image.
