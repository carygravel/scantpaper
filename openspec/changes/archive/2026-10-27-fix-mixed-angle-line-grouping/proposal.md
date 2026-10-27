# Proposal

## Why

A page whose flat text layer mixes upright (0 degree) and rotated (90
degree) slices saves to a PDF where every upright word is drawn enormously
tall, so search highlights become huge blocks. The words are still found
and the on-screen editor is correct, which makes the output look
searchable while its rendered positions and glyph sizes are wrong. A
single tall rotated slice is enough to trigger it.

## What Changes

- Fix `_group_words_into_lines` in `src/scantpaper/bboxtree.py` so a tall
  word can no longer inflate the grouping tolerance for unrelated short
  words. Grouping becomes a local decision: a candidate word joins the
  current line only when its vertical centre is within a tolerance derived
  from the smaller of the two words' heights, instead of the global maximum
  word height.
- Keep the existing behaviour for equal-height words: rows stay separate,
  rotated words stay separate, and genuinely aligned words still share a
  line.
- Add grouping-level unit coverage for the flat/mixed-angle paths, plus one
  save-level check that a mixed-angle flat layer renders upright words at a
  sane height.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `save-searchable-text-layer`: adds the requirement that grouping a flat
  text layer into synthetic lines does not distort the rendered size or
  position of upright words when rotated words are present.

## Impact

- Code: `src/scantpaper/bboxtree.py` (`_group_words_into_lines`).
- Tests: `src/scantpaper/tests/test_75_bboxtree.py` (grouping) and
  `src/scantpaper/tests/test_1111_save_pdf.py` (mixed-angle flat layer).
- No dependency, data-model, or CLI change. On-disk layer JSON is
  unchanged; only the exported hOCR grouping changes.
