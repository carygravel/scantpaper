## Why

Rotating a page by 270° (or -270°) leaves the page's width/height metadata
un-swapped, so the regenerated thumbnail is drawn with the wrong aspect ratio:
a portrait page rotated 270° is squeezed into a landscape box, appearing
stretched in x and compressed in y. The new alternating-rotation feature makes
this visible on every odd page of a landscape book scan (odd pages rotate
270°, even pages rotate 90°), while manual Tools menu rotation at 270° has the
same defect.

## What Changes

- Fix `do_rotate` in `docthread.py` so a quarter-turn rotation in either
  direction (90, 270, -90, -270) swaps the page's width/height and x/y
  resolution, matching the already-swapped pixel dimensions produced by
  `Image.rotate(..., expand=True)`.
- Ensure the thumbnail regenerated after such a rotation has the correct
  aspect ratio (the rotated, upright page fills the portrait/landscape box
  rather than being distorted).
- Add a regression test rotating a page by 270° and asserting the regenerated
  thumbnail and page size swap correctly.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `thumbnail-generation`: the thumbnail must keep the correct aspect ratio after
  a 90° or 270° page rotation, because the page's width/height metadata must
  track the rotated pixel dimensions.

## Impact

- `src/scantpaper/docthread.py`: the `do_rotate` width/height and resolution
  swap condition.
- `src/scantpaper/tests/`: extend the thumbnail/rotation tests to cover 270°
  (and -270°).
- No new dependencies, no user-visible UI changes, no breaking changes.