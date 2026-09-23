## Context

`do_rotate` (`src/scantpaper/docthread.py`) rotates the stored `image_object`
with PIL `rotate(angle, expand=True)`, which produces a bounding-box image
whose width/height are swapped for 90° and 270° turns. The page metadata
width/height and resolution tuple are only swapped for angles in `(-90, 90)`,
so a 270° rotation leaves the metadata describing the pre-rotation shape.
Thumbnails and previews regenerate from that metadata via
`Page.get_pixbuf_at_scale()` / `get_size()`, so they render the rotated pixels
squeezed into the un-swapped box (distorted). The PDF save path derives
geometry from the actual image, which is why output files are unaffected.

## Goals / Non-Goals

**Goals:**
- Swap page width/height and x/y resolution after any quarter-turn rotation
  (90, 270, -90, -270) so thumbnail/preview aspect stays correct.
- Keep the swap a pure metadata operation on the docthread worker, with a
  regression test at 270°.

**Non-Goals:**
- No change to the pixel rotation itself, to rotation of 0°/180° (dimensions
  are unchanged by `expand=True` there), or to the save/OCR pipelines.
- No UI changes or new configuration.

## Decisions

- Extend the existing `if options["angle"] in (-90, 90)` condition in
  `do_rotate` to also accept 270 and -270. An angle is a quarter turn when
  `abs(angle) % 360 == 90`; expressing it as the explicit tuple
  `(-270, -90, 90, 270)` keeps the intent obvious and avoids surprises with
  equivalent angles such as 450. A separate 180° case remains unnecessary
  because `expand=True` does not swap dimensions at 180°.
- The resolution swap already mirrors the width/height swap in the same branch,
  so extending the condition fixes both together.
- Regression test mirrors the existing `test_rotate` in
  `tests/test_211_tools.py`, rotating by 270° (and -270°) and asserting the
  page size and thumbnail width/height swap.

## Risks / Trade-offs

- Very low risk: the change is one condition extension plus tests, and it only
  affects the quarter-turn cases that already swap the visible image.
- Angles outside the UI's 0/90/180/270 increments (e.g. arbitrary values that
  happen to leave dimensions unchanged at 90°) are not handled, but the scan
  dialog only offers 0/90/180/270, and 180° correctness is covered by the
  unchanged branch.