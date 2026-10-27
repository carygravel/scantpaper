# Design

## Context

See `proposal.md` - Why. A flat text layer (words directly under the page,
as produced by the layer editor) is wrapped into synthetic `ocr_line`
elements by `Bboxtree.to_hocr`. `_group_words_into_lines` currently seeds
the grouping tolerance from the single tallest word in the whole set:

```python
tolerance = max(height) * 0.6
```

OCRmyPDF then computes a line's font size from the line's bounding box
(`fpdf_renderer/renderer.py`, `font_size = line_size_height + intercept`),
so a synthetic line that spans several rows renders every word at that
inflated size.

## Goals / Non-Goals

- Goal: make line grouping a local decision so one word's size cannot
  change another word's rendered geometry.
- Goal: preserve existing grouping for equal-height words and for rotated
  words, so no current scenario regresses.
- Non-Goal: change the layer JSON schema, the editor, or the save pipeline.
- Non-Goal: rework angle handling in `_normalise_textangles`, which already
  splits real mixed-angle OCR lines correctly.

## Decisions

### Decision: compare each candidate against its neighbour, not a global max

A candidate word joins the current line only when the vertical distance
between their centres is within a tolerance derived from the **smaller** of
the two words' heights:

```python
tolerance = min(height(previous), height(candidate)) * 0.6
```

The `0.6` factor is kept from the current implementation so the scale of
"same row" is unchanged. Taking the minimum means a tall word can never
widen the tolerance for a short one, which is the observed failure.

### Decision: keep chaining against the previous word

The existing loop compares against `current[-1]`. Keeping that avoids
changing line-assembly semantics for the common case and keeps the change
minimal. Drift over a long row is bounded by the short words' own heights,
which is what we want.

### Alternatives considered

- **Partition by effective text angle before grouping (per-angle groups).**
  Also fixes the repro, but it ignores inherited ancestor angles unless it
  re-derives the effective angle, and it still merges same-angle runs of
  differing heights (for example a large title word beside body text). The
  local-tolerance choice fixes both without angle awareness.
- **Tolerance from the line's minimum height so far.** Equivalent in
  practice to the chosen rule for the failing cases, but reads as mutable
  line state; pairwise-min is simpler to reason about and to test.

## Risks / Trade-offs

- [A legitimate line has words of very different heights that should share
  one line] -> They will now split into more lines. This is acceptable: a
  line's renderer uses one font size for all its words, so grouping such
  words together was already lossy.
- [Existing flat-layer tests assume the global-max tolerance] -> Add
  grouping-level unit tests for both equal-height and mixed-height cases
  and run the full suite; adjust only if a test encodes the old bug.

## Migration Plan

No data or schema migration. The change affects only exported hOCR, so
existing sessions and files are unaffected until the next save.

## Open Questions

None.
