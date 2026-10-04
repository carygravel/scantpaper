## Context

See proposal.md - Why. The save pipeline writes each page's hOCR via
`Page.export_hocr()` (page.py:167) → `Bboxtree.to_hocr()` into
`000001_ocr_hocr.hocr`, then hands it to ocrmypdf's `_hocr_to_ocr_pdf`
(savethread.py:157). ocrmypdf 16.13's fpdf2 renderer only walks
`ocr_page > ocr_par > ocr_line > ocrx_word`; anything else is silently
dropped, producing an empty `/OCR-*` form XObject.

The affected tree shapes:
- PDF import builds a flat `page > word` tree (`_pdftotext2boxes` never emits
  `line`/`para`, bboxtree.py:576-631).
- `Bboxtree.to_hocr()` mirrors whatever tree it is given; a flat tree yields a
  flat hOCR (bboxtree.py:300-323), so the renderer emits nothing.
- OCR'd scan pages already carry `column`/`para`/`line`, so they are unaffected.

## Goals / Non-Goals

**Goals:**
- Guarantee that `to_hocr()` output always contains `ocr_par`/`ocr_line`
  containers for every text-bearing page, so the saved PDF is searchable
  regardless of the in-app tree shape.
- Keep the in-app scene graph (canvas editing, cropping, deletion) unchanged;
  the fix is confined to hOCR export.
- Add a regression test driving the real `_hocr_to_ocr_pdf` pipeline.

**Non-Goals:**
- Do NOT restructure the in-app tree (`from_pdftotext`) to build line/para
  nodes. That changes the tree used by canvas rendering/editing and the 
  existing test expectations, with no user-visible benefit over fixing export.
- Do NOT change `Canvas.hocr()`'s `ocr_word` emission; it is an internal,
  self-consistent path (`ocr_word` is re-parsed by `_hocr2boxes`), not the save
  path.
- No changes to ocrmypdf, img2pdf, or the OCR engine.

## Decisions

### Decision 1: Synthesize containers in `to_hocr()`
Make `Bboxtree.to_hocr()` emit an `ocr_par` (and per-y-group `ocr_line`)
container when a page's children would otherwise be words (or lines) without
an enclosing paragraph. This is a single source of truth: every export path
(`Page.export_hocr`, DjVu text export consumers, tests) inherits the fix.

- Group words into `ocr_line` by y (using a small tolerance on the word's
  vertical centre), then wrap all lines in one `ocr_par`.
- Alternative considered: fix `_pdftotext2boxes` to build line/para nodes.
  Rejected: it changes the in-app tree, affects rendering/deletion and many
  tests, and does not protect against other degenerate trees.

### Decision 2: Reuse the existing bbox walk
Implement synthesis inside `to_hocr()` by walking `each_bbox()`. When the walk
sees a word/line whose parent chain lacks a `para`, emit a synthetic
`<p class='ocr_par'>` (and `<span class='ocr_line'>`) open tag at the correct
indent, mirroring `_hocr_open_tag` (bboxtree.py:663). Keep the emitted geometry
from each word's own bbox so positions stay correct.

### Decision 3: Regression test drives the real pipeline
Add a test that builds a flat tree (as `from_pdftotext` does), calls
`to_hocr()`, runs it through ocrmypdf `_hocr_to_ocr_pdf` against a small
image-only origin PDF, and asserts the output's text layer is non-empty and
extractable (e.g. via pikepdf content inspection). This exercises the actual
failure the existing string-only tests miss.

## Risks / Trade-offs

- [Synthesized per-word lines may produce looser spacing than a real line
  layout] → Acceptable; the requirement is searchability and correct position,
  not pixel-identical spacing. y-grouping keeps most words on shared lines.
- [ocrmypdf's aspect-ratio guard (`_check_aspect_ratio_plausible`) could
  suppress a synthetic line] → Mitigated: synthesis uses each word's own
  bbox for the line bbox (word-sized), matching the shapes verified to render
  (see investigation: 206 Tj rendered from real line bboxes).
- [Adding containers changes the exact hOCR string, breaking string-equality
  tests] → Update those assertions to the new expected structure; the 
  regression test covers the observable behaviour.
- [The fix depends on ocrmypdf's renderer contract] → It is already a pinned
  dependency (16.13) and the only renderer used; the regression test guards it.

## Open Questions

None.
