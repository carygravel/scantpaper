## Context

See `proposal.md` - Why. The defect lives at the hOCR-export boundary.
`Bboxtree.to_hocr()` calls `_hocr_with_containers()`
(`src/scantpaper/bboxtree.py:668`), which currently short-circuits:

```python
if not bboxes or any(b["type"] == "para" for b in bboxes):
    return bboxes
```

When a page carries OCR paragraphs, this skips the synthetic-container pass
entirely. A word the user added in empty space is nested under the page (or a
`carea`), not under a `para`, and is emitted as a bare `span class='ocrx_word'`
inside `ocr_page`. ocrmypdf's renderer (`hocr_parser.py`) iterates
`p[class='ocr_par']` and only falls back to bare page-level words when the page
has no paragraphs at all, so the manual word is dropped. The fix is confined to
this one function and its regression test.

## Goals / Non-Goals

**Goals:**
- Guarantee every word/line in the exported hOCR is nested under a `para`,
  whether the tree is flat, fully structured, or a mix.
- Preserve existing structure for already-well-nested words (no unnecessary
  re-wrapping that would churn output).

**Non-Goals:**
- Changing how ocrmypdf renders text layers.
- Changing the canvas editor, session persistence, or DjVu export paths
  (the DjVu path has its own exporter and is not affected by this bug).
- Introducing new dependencies.

## Decisions

**Decision: Rewrite `_hocr_with_containers` to wrap any un-paragraphed
word/line instead of bailing out on the first `para`.**

The current early return is the bug. The wrapping pass already handles the
all-flat case correctly; the same pass should run per-subtree, wrapping only the
nodes that lack a `para` ancestor. An approach that keeps the existing
stack-based rebuild but, after building the nested tree, walks it and applies
the existing `_ensure_hocr_containers` to every node whose children include
bare words/lines — instead of skipping the whole tree when any `para` exists —
satisfies both goals.

Rationale over the alternative of "only wrap words that were manually added":
- The bboxtree stores no provenance for whether a word came from OCR or from a
  manual edit, so we cannot reliably distinguish them at export time.
- Re-wrapping is idempotent for words already under a `para` (the pass skips
  word/line children of `para` nodes), so running it over the whole tree is safe
  and produces no churn for the structured portion.

**Decision: Keep the existing `_ensure_hocr_containers`/`_group_words_into_lines`
helpers and reuse them, extending `_ensure_hocr_containers`'s leaf detection.**

They already encapsulate line-grouping and paragraph wrapping. The fix changes
the gating that decides whether they run. Running the pass over already
structured trees revealed that `_ensure_hocr_containers` treated the line-level
containers `header`/`footer`/`caption` as generic wrapper nodes and re-wrapped
their words, corrupting OCR output. These are therefore added to the leaf set
(`word`/`line`/`para`/`header`/`footer`/`caption`) so their words are left
untouched; only words/lines not under a paragraph are wrapped.

## Risks / Trade-offs

- [Changing the gating could affect already-correct output] → The wrapping pass
  is a no-op for words/lines already under a `para`; the only output change is
  newly-wrapped bare words, which is the intended fix. The existing flat-tree
  test guards the current behaviour.
- [Word that lands under a `line` but not a `para`] → The rewritten pass must
  also handle a `line` with no `para` ancestor (e.g. added under a `carea`),
  wrapping it in a `para`. This is covered by exercising the helpers on mixed
  trees in the regression test.

## Migration Plan

Not applicable — this is a bug fix in a desktop application with no data
migration. Release normally.

## Open Questions

None.
