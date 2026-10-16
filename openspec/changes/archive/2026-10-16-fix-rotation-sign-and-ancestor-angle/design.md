## Context

See proposal.md - Why. Two pieces of existing machinery matter:

- The draw formula in `canvas.py` is
  `angle = -(bbox.textangle + bbox.transformation[0])`, and `ctx.rotate(angle)`
  in Cairo (y-down) turns clockwise for a positive angle. `bbox.textangle` is
  therefore "degrees of anticlockwise glyph rotation from horizontal", which is
  also how Tesseract's native vertical text is encoded.
- `Bbox.transformation` is `[rotation, x, y]`; only `rotation` is used for
  drawing (`canvas.py` `_draw_bbox`). It is computed in `canvas.py::add_box`
  from the immediate parent alone, while `_boxed_text` separately maintains an
  accumulated `transformations` list that is never passed to `add_box`.

## Goals / Non-Goals

**Goals:**
- The rotate controls turn the glyphs the way their labels say.
- A slice's drawn angle is its own text angle plus the accumulated text angle of
  every ancestor, applied exactly once, at any depth.
- A slice added while a rotated slice is focused renders at the focused slice's
  angle.

**Non-Goals:**
- Changing the on-disk `textangle` meaning or the hOCR/JSON schema.
- Changing the draw formula or how Tesseract-authored vertical text renders.
- Rotating or moving the bounding-box rectangle (rotation is glyphs only).

## Decisions

### 1. Correct the control sign, not the draw formula

`rotate_clockwise` currently adds +90 to `textangle`; because the draw angle is
negated, that turns the glyphs anticlockwise. Swap the deltas:
`rotate_clockwise` applies `-90`, `rotate_anticlockwise` applies `+90`, keeping
`_apply_rotation`'s incremental `(textangle + delta) % 360`.
The draw formula and the persisted convention stay untouched, so text Tesseract
emitted with a `textangle` keeps rendering exactly as before.

Alternative considered: negate the draw formula instead. Rejected - it would
flip every existing (Tesseract-authored) rotated slice.

### 2. One accumulated-frame-angle helper replaces both rotation bookkeepings

`_draw_bbox` computes `angle = -(bbox.textangle + bbox.transformation[0])`, so
the angle stored in a box's `transformation[0]` is the total rotation of its
*parent's* local frame. Define the frame rotation of a box as the sum of its own
`textangle` and every ancestor's:

```
accumulated_textangle(b) = b.textangle + accumulated_textangle(b.parent)
```

i.e. *inclusive* of `b`, returning 0 once the root is reached. Then a child's
`transformation[0]` is exactly `accumulated_textangle(parent)`, so:

- `add_box`'s fallback becomes
  `transformation = [self.accumulated_textangle(parent), parent.bbox.x, parent.bbox.y]`
  (still `[0, 0, 0]` for a root parent). This is the fix for the dropped
  ancestor angle: the old fallback stored only `parent.textangle`.
- Delete the `transformations` list from `set_text` and `_boxed_text`; it was
  dead and its "append `textangle + rotation`" step is now done by the helper
  when the next box is created.

`accumulated_textangle` is public (`layer.py` calls it, and the editor only
calls public `Canvas` methods).

Alternative considered: pass `_boxed_text`'s accumulated list into `add_box` via
a `transformation` kwarg. Rejected - it keeps two sources of truth and leaves
`add()`/`copy()` (which call `add_box` directly) still wrong. Walking the parent
chain gives one implementation for every caller and fixes the depth bug for
free.

### 3. Compose the inherited rotation against the new slice's parent

`add()` currently copies `_current_bbox.textangle` verbatim. Combined with the
parent angle, a focused slice that is also the new slice's parent is rotated
twice, and a focused slice elsewhere contributes an angle that ignores the new
parent's own ancestors.

A slice is drawn at `-accumulated_textangle(slice)`, so set the new slice's
stored angle so its frame rotation matches the focused slice's:

```
new.textangle = (accumulated_textangle(focused)
                 - accumulated_textangle(parent)) % 360
```

with the same inclusive `accumulated_textangle` and `parent` resolved once via
`canvas.get_bbox_at(selection)` before `add_box` (passing `parent=` explicitly).
When the focused slice is `None`, the angle is 0.

- Focused slice and new slice share a parent: the shared ancestor term cancels,
  leaving `focused.textangle` (today's behaviour, preserved).
- Focused slice is the new slice's parent: `parent` *is* `focused`, so the
  result is `focused.textangle` again, but drawn once, because the ancestor term
  is subtracted instead of added.
- Focused slice is unrelated: the new slice renders at the focused slice's
  angle, which is what "inherit the current rotation" means.

This needs the resolved parent, so `add()` resolves it (as `add_box` already
does) and handles the existing `ReferenceError` when the selection is not over
any box.

### 4. Keep `transformation[1]`/`[2]` as parent x/y

Only `[0]` is read for drawing, but the other two slots are part of the existing
`transformation` shape and are left as the parent's x/y for continuity.

## Risks / Trade-offs

- [Removing the `_boxed_text` accumulator changes the number of options passed
  to `add_box`] -> The parent-chain walk produces the same values for the
  single-level case, so unrotated and singly-rotated documents render
  identically; the nested case is the bug being fixed.
- [Modulo 360 on the inherited angle could differ from a raw stored value] ->
  `textangle` is only ever meaningful modulo 360; existing values are already
  produced modulo 360 by `_apply_rotation`.
- [Resolving the parent twice (in `add()` and again implicitly)] -> `add()`
  resolves it once and passes it explicitly, so `add_box` does not re-resolve.

## Migration Plan

None. No stored data changes; the fix only affects the sign of new rotations and
how an existing `textangle` is composed for rendering.
