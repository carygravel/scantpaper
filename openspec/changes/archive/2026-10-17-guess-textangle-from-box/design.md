## Context

See `proposal.md` - Why. The relevant mechanics today:

- `LayerEditor.add` (`src/scantpaper/layer.py:497`) computes the new
  slice's angle only as `accumulated(focused) - accumulated(parent)`, so a
  selection drawn on a flat page gets `textangle = 0`.
- `LayerEditor.copy` and the first-slice path `_new_layer_json` do the same,
  also defaulting to 0.
- The renderer `_draw_bbox` (`src/scantpaper/canvas.py:903-915`) derives a
  uniform scale for the text layout; the axis it spans is chosen by
  `scale = h / text_w if angle else w / text_w`, where `angle` is the drawn
  (`textangle + ancestor`) angle. The text layout is measured at a fixed
  `Sans 10` (`LAYOUT_FONT_DESCRIPTION`, `canvas.py:57`).

A tall, narrow selection therefore makes the renderer span the selection's
narrow width, shrinking the glyphs to near-invisibility. A 180-degree slice on
a wide box hits the same wrong-axis branch.

## Goals / Non-Goals

**Goals:**

- Recover the orientation the user expressed by drawing a tall, narrow
  selection, using the text that will be placed in it, without a dialog or
  pixel analysis.
- Make a 180-degree slice render at the same size as an upright one.

**Non-Goals:**

- Changing the render scale formula itself (still one governing axis, not a
  contain-fit). Overflow of the non-governing axis is unchanged behaviour.
- Re-guessing the angle when an existing slice is resized or its text is
  corrected with the OK/accept control.
- Detecting 180 versus 0 from image content, or reading OCR's orientation
  data.
- Changing the on-disk layer format.

## Decisions

### Decision: a text-aware fit criterion, not raw aspect ratio

Measure the text's ink extents `(tw, th)` for the fixed layout font, and the
selection `(w, h)`. Compute the largest uniform scale at which the text fits
entirely inside the selection for each orientation:

```
upright(u)    = min(w / tw, h / th)
rotated(r)    = min(h / tw, w / th)
```

- Choose 0 degrees when `u >= r` (ties favour upright).
- Choose 90 degrees when `r > u`.

Rationale: for a long text in a tall narrow box, `r` dominates `u` and the
slice is created vertical - the bug is fixed. For a short text in a selection
that is only slightly taller than wide, `u` dominates and the text stays
upright, which is why the criterion is text-aware rather than a bare `h > w`
test. Guard `tw > 0` and `th > 0`; if either is zero (degenerate layout),
fall back to `r > u` computed from the remaining axis, and ultimately to
`h > w` if both are zero.

Alternatives considered:

- **Bare `h > w`** - simplest, but rotates a short word placed in a
  marginally tall selection, the opposite surprise.
- **Compare text ink length to the selection's dimensions** - a coarser form
  of the same idea that ignores the text thickness and needs an arbitrary
  tolerance; the min-fit ratio above is scale-invariant and needs none.
- **Inspect the pixels under the selection** - accurate but heavy, and
  duplicates work tesseract already did; rejected as YAGNI.

### Decision: only guess when no quarter turn is inherited

`add` currently computes a relative angle so a slice inserted inside an
already-rotated line is drawn once at that angle. The guess must not fight
that. The guess is applied only when the inherited relative angle is 0 **and**
the parent's accumulated angle is 0 or 180 degrees (i.e. `% 180 == 0`). When a
quarter turn is already inherited (parent accumulated is 90 or 270), the drawn
angle is already `h / text_w`-legible and the guess is skipped.

Because the guess is added to the parent's frame, an inherited 180-degree
rotation still allows a relative guess of 0 or 90, yielding a drawn angle of
180 or 270 with the correct axis. The comparison uses the selection's absolute
width and height, which are the axis-aligned box dimensions the renderer also
uses.

The same helper is called from `add`, `copy`, and the first-slice construction
in `_new_layer_json`.

### Decision: a pure, testable helper plus a text-measurement method

Add a pure function that takes the selection width and height, the text ink
extents, and the inherited-rotation flag, and returns 0 or 90. It has no GTK
dependencies and is unit-tested directly. The text measurement lives on the
Canvas next to the existing layout code (reusing `_create_pango_layout`), so
the editor calls `canvas.measure_text(text)` and then the pure helper. This
keeps the decision logic testable without a display and the Pango work in the
one place that already owns the layout.

The measurement source is the same fixed `Sans 10` layout the renderer draws,
so the guess and the rendering agree on which axis is the governing one.

### Decision: fix the render axis for 180 degrees

In `_draw_bbox`, replace the truthiness test on the drawn angle with an axis
selection:

```
scale = (w if angle % 180 == 0 else h) / text_w
```

`angle` is already normalised to `[0, 360)`, so `% 180 == 0` selects width for
0 and 180 and height for 90 and 270. This is the only rendering change.

## Risks / Trade-offs

- **Near-square selections flip orientation on small text changes.** With
  `u` and `r` close, a borderline box may render rotated. Mitigation: the
  guess is a one-time hint, always visible on the page and correctable with
  the existing rotate controls; the spec records this as a normal text angle.
  If it proves noisy we can add a bias toward upright later without changing
  the specs.
- **The non-governing axis can still overflow.** Out of scope by design; the
  renderer's govern-one-axis behaviour is unchanged, so a long line in a short
  box still overflows vertically exactly as before.
- **Measurement font differs from the eventual PDF font.** The guess only
  picks orientation, which is robust to the exact metrics; ocrmypdf still owns
  the saved text size.
- **180 fixes only the on-screen axis, not PDF embedding.** The saved layer is
  rendered by ocrmypdf from geometry and textangle; this change does not alter
  that path, and the round-trip test guards that the angle still persists.
