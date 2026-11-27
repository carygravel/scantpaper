# Design

## Context

See `proposal.md` - Why. The defect is at the hOCR-export boundary.

`Page.export_hocr()` serialises the stored text layer through
`Bboxtree.to_hocr()`. That method rebuilds a nested tree from the flat,
depth-annotated bbox list and calls `_hocr_with_containers()`, which runs
`_ensure_hocr_containers()` before `_normalise_textangles()`.

`_ensure_hocr_containers()` currently treats `para` as an already-grouped
container and returns early. It only wraps bare `word`/`line` children at
generic containers such as `page`, `carea`, and `column`. That assumes every
word under a paragraph is already inside one of its lines.

The canvas breaks that assumption when a user adds a word in empty space:

- `canvas.get_bbox_at()` returns the deepest bbox containing the selection
  centre.
- An OCR paragraph often has a large bounding box. Adding a word beside a
  short line lands inside the paragraph but outside any of its lines.
- `canvas.add_box(parent=para)` appends the new word directly under the
  paragraph.
- `page.import_hocr(canvas.hocr())` stores that shape as
  `page -> para -> word`.

The exported hOCR therefore contains a bare `ocrx_word` directly under
`ocr_par`. ocrmypdf's renderer walks `ocr_par` children that are line-class
spans (`ocr_line`, `ocr_header`, `ocr_textfloat`, `ocr_caption`). It only
falls back to page-level bare words when the page has no lines at all. The
word is silently dropped.

The debug evidence is concrete: the stored text layer has 183 words, the
saved PDF extracts 181, and the only missing words are `119/120` and
`Doppelband`, both emitted as bare children of the large header paragraph.

There is a second symptom on the same path. `_normalise_textangles()` only
moves an angle onto a line-like node. A word that is not inside a line has its
`textangle` popped and discarded. A rotated word added under a paragraph would
therefore lose its rotation even if it were somehow rendered.

## Goals / Non-Goals

**Goals:**

- Guarantee that every word in exported hOCR sits under a line-like node that
  sits under a paragraph.
- Preserve existing paragraph and line structure; synthesise only what is
  missing.
- Repair existing sessions and imported hOCR on the next save, with no data
  migration or re-editing.
- Keep output stable for already well-formed trees.
- Preserve rotated words added under a paragraph by giving their synthetic line
  the word's angle.

**Non-Goals:**

- Changing canvas parent selection or how `layer.add()` builds the scene graph.
- Changing the stored text-layer JSON schema or the hOCR import parser.
- Changing ocrmypdf or its renderer.
- Merging a bare word into an existing line, even when it looks like it belongs
  there.
- Adding ids, baselines, or font metrics to synthetic lines beyond what the
  renderer needs.

## Decisions

### Normalise at export, not at add time

Export is the boundary that must satisfy the renderer contract. Doing it there
fixes all save paths, repairs existing sessions, and covers imported hOCR that
already contains bare words, without touching the canvas or the session schema.

Alternatives considered:

- **Normalise when the word is added.** This would keep stored sessions
  well-formed, but it leaves existing sessions and imported hOCR broken, and it
  requires changing the canvas tree and edit focus behaviour. Rejected.
- **Normalise when hOCR is imported.** This helps imported files, but words
  added after import would still be bare, so export would need the same fix
  anyway. Rejected as insufficient on its own.
- **Change ocrmypdf.** The renderer is an external dependency and the fix must
  work with the versions users already have. Rejected.

### Give `para` its own wrapping branch

Removing `para` from the early-return set and running the generic wrapping
logic would create a paragraph inside a paragraph, producing invalid
`<p class='ocr_par'>` nesting. Instead, handle `para` explicitly:

- Recurse into its children.
- Wrap consecutive direct `word` children in synthetic `line` nodes, in place.
- Leave existing `line`/`header`/`footer`/`caption` children untouched.
- Never create a synthetic paragraph inside a paragraph.

Generic containers (`page`, `carea`, `column`, and the synthetic root) keep the
current behaviour: direct words and lines are wrapped in one synthetic
paragraph, with words grouped into lines.

### Reuse the existing grouping and bbox helpers

`_group_words_into_lines()` already groups consecutive words by vertical centre
using a tolerance based on the shorter word. That prevents a tall rotated word
from pulling upright words on other rows into its line, which is the existing
"Synthetic line grouping preserves word geometry" contract. `_union_bbox()`
gives each synthetic line a bbox for the renderer.

### Normalise before angles

`_hocr_with_containers()` already runs the container pass before
`_normalise_textangles()`. Once a bare word has a synthetic line parent,
`_normalise_line()` moves the word's effective angle onto that line and clears
it from the word. No separate angle fix is needed; the existing rotation logic
takes over.

### Test at both boundaries

Unit tests on `Bboxtree.to_hocr()` prove the exported structure. An
end-to-end test through `_hocr_to_ocr_pdf()` and `pdftotext` proves the real
renderer accepts it. The end-to-end test is necessary because the defect is a
renderer contract, not merely an hOCR shape.

## Risks / Trade-offs

- [Synthetic line without an id or baseline] -> The renderer only needs a line
  class and a valid bbox. Synthetic lines for flat text layers already work
  this way; the new tests cover the paragraph path too.
- [Bare words could be reordered] -> Wrap them in place, preserving child
  order. The canvas normally appends new words at the end of the paragraph, so
  the extracted order stays natural.
- [A bare word visually belongs on an existing line] -> It gets its own
  synthetic line. The text remains searchable and positioned correctly, though
  extraction order may differ slightly. Merging into an existing line would
  churn its bbox and metadata and is out of scope.
- [Rotated words could distort line metrics] -> Reuse
  `_group_words_into_lines()`; spaced rotated words each form their own line,
  and a line's bbox is the union of its own words only.
- [Existing hOCR round-trip fidelity] -> Well-formed trees, where words are
  already under lines, are unchanged. Only trees with bare words under a
  paragraph gain a synthetic line. The existing page 19 round-trip behaviour
  remains valid.
- [Coverage gate] -> Add unit cases for a paragraph with lines plus bare
  words, a paragraph with bare words only, and a rotated bare word, plus the
  end-to-end save test.

## Migration Plan

None. Existing sessions and imported hOCR files are corrected at the next
export. Reverting the change restores the previous export behaviour without
altering stored data.

## Open Questions

None.
