## Context

`_do_import_pdf` in `scantpaper/importthread.py:410` currently runs
`pdfimages -f i -l i -list` to find the page resolution, then
`pdfimages -f i -l i <path> x` to extract every image, and imports all globbed
`x-*.???` files as pages. A page holding a transparent image yields two extracted
files (the image plus its soft mask), so an extra page is created and a spurious
"expects one image per page" warning fires. See proposal.md for motivation and
`specs/import-pdf-images/spec.md` for the behavioral contract.

Two facts about `pdfimages` shape the approach (verified against the repo's
`dog.pdf`):

- `-list` reports a `num` that is a **global document counter** (`0,1,2,3...`),
  but file extraction **restarts at `x-000` for each page**.
- The type column distinguishes `image`, `smask`, and `stencil` entries.

## Goals / Non-Goals

**Goals:**
- Import only real images from a PDF page, never its masks.
- Keep the one-image-per-page warning meaningful (counts images, not files).
- Give each imported page its own resolution from `-list`.

**Non-Goals:**
- Flattening transparent images to RGB on save (the "Option B" follow-up).
- Vector-only pages, genuinely multi-image pages, or other exotic structures
  beyond preserving the existing warning behavior.

## Decisions

### D1: Parse `pdfimages -list` by whitespace, not fixed columns

Split each data line on whitespace. The column layout (after the 2-line header)
is stable:

```
page  num  type  width height color comp bpc enc interp object ID x-ppi y-ppi size ratio
  1     0  image  ...
```

Tokens are `[page, num, type, width, height, color, comp, bpc, enc, interp,
object, ID, x-ppi, y-ppi, size, ratio]`; `x-ppi`/`y-ppi` can be `0` and object
columns can be `[inline]` or `-`, all of which split cleanly. A data line is one
whose first two tokens are integers. Header and separator lines are skipped
because they do not parse as integers.

Alternatives considered: fixed-column slicing (`line[11:16]` for type) as the
existing code does for ppi — rejected because it is version-fragile and would
need a second slice for the type. A regex — rejected as unnecessary once tokens
are split.

Parse into a module-level pure function `_parse_pdfimages_list(out)` returning
`list[dict]` (keys: `page`, `num`, `type`, `x_ppi`, `y_ppi`). Pure and
independently testable.

### D2: Correlate extracted files with `-list` entries by index

After extraction, `sorted(glob.glob("x-??*.???"))`; the k-th file corresponds to
the k-th `-list` entry for that page (both iterate images in document order).
Mask entries are never imported; their files are removed.

Alternatives considered: deriving each file's global `num` from the page offset
— rejected: it assumes `num` stays a contiguous global counter across versions.
A count-based "skip the last N" rule — rejected: masks can interleave real
images (`image, smask, image, smask`), so only index correlation is correct.

Fallback when the counts disagree (`len(images) != len(entries)`): the index
mapping is untrustworthy, so import every extracted file and warn, preserving
today's behavior.

### D3: Clean up leftover `x-*` files each page iteration

Remove any remaining `x-*` extraction files at the start of each page's import.
This keeps index correlation sound and fixes a latent bug where an image whose
import raised `PermissionError`/`IOError` was left behind and then picked up by
the next page's glob.

### D4: Warning based on non-mask image count

`warning_flag` is set when the number of entries of type `image` on the page
differs from 1. An image+smask pair counts as one image, so no warning; two real
images still warn (see `specs/import-pdf-images/spec.md`).

## Risks / Trade-offs

- [`-list` output format changes in a future poppler] → The whitespace parser
  degrades to an empty entry list; the count-mismatch fallback (D2) then
  preserves today's import-all-and-warn behavior rather than dropping pages.
- [Extraction order differs from `-list` order] → Count check in D2 cannot catch
  an order swap at equal counts; in practice both iterate poppler's image list,
  and the two have agreed across versions. Residual risk is a wrong page pairing,
  flagged only by the existing warning if counts differ.
- [Page with zero images (vector-only)] → No entries, no files, warning raised
  (0 != 1), matching current behavior.

## Migration Plan

Behavior-only fix; no schema, data, or API changes. Existing sessions that
already contain the phantom mask pages are not repaired retroactively — only new
imports are affected. Rollback is a revert of the `importthread.py` change.

## Open Questions

None. Whether to also flatten transparency on save (Option B) is tracked
separately and intentionally out of scope.
