## Why

In the OCR text editor, sorting by confidence is the primary workflow for
eliminating OCR errors: the user corrects the least confident slice, then the
next, and so on. Deleting a slice already advances to the next surviving slice,
but accepting a correction does not — it re-focuses the same slice, so the user
must click the "next" arrow after every correction. In a confidence-sorted pass
this forces one extra click per correction, which is exactly the repetition the
workflow is meant to avoid.

## What Changes

- Accepting a correction (the OK control with non-empty text) SHALL advance
  focus to the next surviving slice in the current sort order, instead of
  re-focusing the corrected slice.
- Advancing SHALL follow the active sort method:
  - confidence sort: move to the next-least-confident surviving slice;
  - position sort: move to the next slice in reading order.
- Deleting, adding, duplicating, and cancelling keep their existing focus
  behaviour; only the correction path changes.
- The existing layer-editing spec already states that after a correction the
  editor leaves the next surviving slice focused, but the implementation does
  not do this and no scenario covers it. This change brings the behaviour and
  the spec into agreement and adds scenarios.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `layer-editing`: extend the "Navigation continues from the affected slice"
  requirement with correction scenarios that lock in advancing to the next
  surviving slice after accepting a correction, in both confidence and position
  sort order.

## Impact

- `src/scantpaper/layer.py` — `LayerEditor.ok()` changes which slice it
  re-focuses after a successful correction (it currently calls
  `self.edit(bbox)`).
- `src/scantpaper/tests/test_layer.py` — update the OK test that asserts
  re-editing, and add tests for advancing in both sort orders.
- No changes to the confidence index, scene graph, serialisation, undo/redo, or
  any other capability.
