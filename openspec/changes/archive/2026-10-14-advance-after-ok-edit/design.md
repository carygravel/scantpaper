## Context

See proposal.md — Why for the motivation. The change lives in a single method,
`LayerEditor.ok()` (`src/scantpaper/layer.py:386`), which currently re-focuses
the corrected slice via `self.edit(bbox)` after a successful correction.

The relevant machinery: the canvas keeps two navigation indexes behind the
single active sort method (`Canvas._current_index`):
- `confidence_index` (a `ListIter`) sorted ascending by confidence, lowest
  first;
- `position_index` (a `TreeIter`) in reading order.

`Canvas.update_word()` (`canvas.py:1096`) sets a corrected word's confidence to
100 via `Bbox.set_word()`, which triggers `reindex_by_confidence()` —
`remove_bbox()` then `add_box_to_index()` — moving the corrected word to the
high-confidence end of the index. The two indexes react differently:

- **Confidence:** `remove_bbox()` leaves the cursor on the entry that followed
  the removed word, and `add_box_to_index()` leaves it there. So after
  `update_word` the confidence cursor already sits on the next-least-confident
  surviving slice.
- **Position:** the `TreeIter` cursor stays on the corrected word; `update_word`
  does not advance it.

So "the slice after the corrected one in the current order" can only be
determined reliably *before* `update_word` relocates the corrected word out of
its original rank.

## Goals / Non-Goals

**Goals:**
- After accepting a correction, focus the next surviving slice in the active
  sort order (confidence: next-least-confident; position: next in reading
  order), without extra user clicks.
- Keep delete, add, duplicate, and cancel behaviour unchanged.

**Non-Goals:**
- Changing how corrections set confidence (already 100) or redraw.
- Changing delete's end-of-list fall-back (to the previous slice).
- Changing undo/redo, serialisation, or the scene graph.

## Decisions

### D1: Capture the successor before updating the word

In `LayerEditor.ok()`, capture the next slice via `get_next_bbox()` *before*
calling `update_word`, then edit the captured slice afterwards:

```python
successor = self.canvas.get_next_bbox()      # next in the CURRENT order
self.canvas.update_word(bbox, text, self._view.get_selection())
self._commit()
self.edit(successor)
```

Rationale: `get_next_bbox()` is mode-agnostic — it delegates to whichever index
is active, so it yields the next-least-confident slice under confidence sort and
the next reading-order slice under position sort, with a single code path and no
mode detection. Because `update_word` relocates the corrected word to the
high-confidence end of the confidence index, the successor must be read before
that mutation; afterwards the corrected word's new rank would no longer point at
the next-least-confident slice.

End-of-list behaviour differs by index: `ListIter.get_next_bbox()` (confidence)
clamps at the last entry and returns it, while `TreeIter.next_word()` (position)
raises `StopIteration` once there is no next word. The call is therefore wrapped
in `try/except StopIteration` and falls back to the corrected slice itself, so
correcting the final slice keeps it focused in both sort orders (the spec
scenario "A correction on the final slice stays on that slice").

Alternatives considered:
- **Branch on sort method after update** (confidence → `get_current_bbox()`,
  position → `get_next_bbox()`): works, but relies on the subtle post-reindex
  cursor side-effect for confidence and adds a mode branch. Rejected as less
  clear.
- **Compute the successor after update**: impossible for confidence mode,
  because the corrected word has already moved to the high-confidence end and
  "what followed it" is no longer reachable from its new rank.

## Risks / Trade-offs

- **Non-obvious ordering** → the correctness of `ok()` depends on reading the
  successor before `update_word` mutates the index. This is captured by the
  existing canvas-level test `test_correction_moves_word_in_confidence_order`
  and by new editor-level tests that assert the focused slice after OK; a short
  comment at the `get_next_bbox()` call documents why the capture precedes the
  update.
- **Reliance on `get_next_bbox()` end-of-list behaviour** → confidence clamps to
  the last entry while position raises `StopIteration`; the `try/except`
  fallback to the corrected slice makes "stay on final slice" hold in both
  orders, and the spec scenario pins it.
- **OK on an already-corrected slice** → pressing OK again re-commits the same
  text and advances, matching existing OK semantics; acceptable and unchanged in
  spirit.

## Migration Plan

N/A — small behavioural change with no data or deployment concerns; covered by
the existing test suite and new tests.

## Open Questions

None.
