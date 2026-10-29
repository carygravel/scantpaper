# Proposal

## Why

A primary click anywhere inside the text layer that does not land on a word
currently focuses the container box under the pointer (a line, column or page).
In confidence sort order this raises `TypeError` from
`ListIter.set_index_by_bbox()` because a container has no confidence value; in
position sort order it silently focuses the container, whose empty text means
accepting the control deletes the whole line and its words.

The same conflation of "any bbox" with "editable slice" also means the
documented draw-a-selection gesture in the layer pane cannot start inside the
page once a layer is loaded, because the page and its containers cover it.

## What Changes

- A primary click focuses a slice only when the pointer lands on a word box.
  Containers (page, column/block, para, line) are never focused, edited,
  deleted or navigated to.
- A primary press that does not land on a word is treated as empty space: it
  begins a selection drag, exactly as it already does on a page with no layer
  content.
- The existing geometric hit test (deepest box containing a point) is retained
  for choosing a new slice's parent; only the focus decision applies the
  word-only rule.
- A plain click (no drag) on non-slice space neither focuses nor clears the
  current slice; the previously focused slice stays focused.

## Capabilities

### New Capabilities

- None. This fixes behavior already covered by existing capabilities.

### Modified Capabilities

- `canvas-widget`: a primary press focuses only a word slice; any other press
  begins a selection drag when the page extent is known, so the click target
  and the selection gesture are defined in one place.
- `layer-editing`: the editor focuses only word slices, so accepting an
  untouched control cannot delete or rewrite a container.

## Impact

- `src/scantpaper/canvas.py`: the primary-button handler and the editor's
  focus/index entry points. `_hit_test()` and `get_bbox_at()` keep their
  current geometric contract.
- `src/scantpaper/layer.py`: any guard needed so `edit()` cannot focus a
  non-slice, and the resulting rotate/OK/delete behavior.
- Tests in `src/scantpaper/tests/test_7_canvas.py` and
  `src/scantpaper/tests/test_layer.py` that currently pin container focus or
  rely on a container without a click callback.
- No new dependencies, no data migration, no user-facing configuration.
