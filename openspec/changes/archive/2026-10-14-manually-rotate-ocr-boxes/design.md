## Context

The text-layer editor (`layer.py`) already lets a user draw a selection, type
text, and add/correct/delete text slices over a page. Every slice is a `Bbox`
whose `textangle` field (degrees) controls how its text is drawn; the canvas
already renders rotated text (`canvas.py:905-906`:
`angle = -(bbox.textangle + rotation) % 360`) and serialises a non-zero
`textangle` into the hOCR text layer (`canvas.py:435-439`, round-tripped by
`bboxtree.py` and embedded in saved output by `page.export_hocr()`).

So the display-and-persist machinery for rotated text already exists and is
shared with the vertical boxes Tesseract itself emits. The only missing piece
is a UI affordance that sets a slice's `textangle`. See proposal.md - Why for
the motivation.

## Goals / Non-Goals

**Goals:**
- Let the user rotate the focused text slice 90° clockwise or anticlockwise.
- New slices added while a rotation is in effect inherit that rotation.
- The rotation is drawn on the page and persisted/saved like Tesseract's own
  vertical text.

**Non-Goals:**
- Re-running OCR on a cropped/rotated region (interpretation B). The user types
  the corrected text by hand.
- Arbitrary (non-90°) angles, or rotating the slice's bounding box geometry -
  only the glyphs turn, the box stays axis-aligned (matches `textangle`).
- Changing the annotation layer; rotation is scoped to the text layer editor.

## Decisions

### Rotation is stored as `textangle` on the focused `Bbox`

`Bbox.textangle` is already the single source of truth for how a slice's text
is drawn, serialised, and embedded. Setting it on the focused `Bbox` and
committing through the existing `LayerEditor._commit()` path reuses all the
existing round-trip and undo machinery. No new data model is introduced.

Alternatives considered:
- Storing a separate "rotation" flag on the canvas scene graph. Rejected: it
  would diverge from the hOCR `textangle` that must be emitted anyway and would
  need extra serialisation plumbing.

### Rotation is incremental: CW adds 90°, CCW subtracts 90° (mod 360)

Repeated clicks turn the slice 0 → 90 → 180 → 270, matching "turn a box
clockwise/anticlockwise" and covering both generating a fresh 90° box and
flipping an existing one. `textangle` values of 90 and 270 render as vertical
text (bottom-to-top / top-to-bottom); the drawing formula already handles any
multiple of 90. This also means the new-inherit behaviour falls out naturally:
a slice added while a rotated slice is focused copies that slice's `textangle`.

Alternatives considered:
- Absolute set-to-90/270 controls. Rejected: less flexible, cannot express 180,
  and does not read as "turn".

### New slices inherit the focused slice's rotation

`LayerEditor.add` currently calls `canvas.add_box(text=..., bbox=selection)`
with no `textangle`, so new slices default to 0. The change passes the focused
slice's `textangle` (0 when nothing is focused) through to `add_box`. `add_box`
already accepts a `textangle` kwarg (`_bbox_kwargs`, `canvas.py:1288-1305`), so
this is a one-line call-site change plus the inherit-from-focused wiring.

### Two new controls on the text-layer editing bar

Add rotate-clockwise and rotate-anticlockwise icon buttons to `LayerControls`,
each emitting a new signal (e.g. `rotate-clockwise-clicked` /
`rotate-anticlockwise-clicked`), wired in `LayerEditor._connect_controls` to
handlers that:
1. no-op when no slice is focused;
2. update `_current_bbox.textangle`;
3. call `self.canvas.queue_draw()` to redraw the page;
4. call `self._commit()` to persist the layer (same path as OK/Add/Delete, so
   the edit is undoable).

The controls are disabled when no slice is focused, mirroring the existing
Add-control sensitivity pattern (`LayerControls.set_add_enabled`), to make the
"acts on the focused slice only" rule discoverable.

## Risks / Trade-offs

- **Glyph orientation may look inverted for one of the two directions.** The
  exact bottom-to-top vs top-to-bottom mapping of `textangle` 90/270 is a
  rendering convention shared with Tesseract; if it looks backwards for the
  authoring use case, only the sign in the CW/CCW handler changes, not the
  data model or spec. → Verify visually during implementation; adjust the
  handler's +/- sign if needed. The spec only mandates that the two directions
  are distinct and persistent.
- **Rotation is per-slice, not recursive.** Rotating a line rotates only that
  line, not its child words. The editor operates on the focused slice, which is
  the documented contract. → Acceptable for the authoring use case; the focused
  slice is a word by default.
- **Undo coverage** depends on `_commit()` feeding the layer setter, which
  already provides undo for OK/Add/Delete. → Confirmed path; rotation reuses it,
  so undo/redo work without new plumbing.

## Migration Plan

N/A - purely additive UI within the existing editor; no stored data format
change (`textangle` already exists in the layer schema).

## Open Questions

None. The direction sign is resolved empirically during implementation without
changing the spec, design, or task breakdown.
