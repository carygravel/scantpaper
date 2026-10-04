## Why

Editing the OCR text layer is currently broken in three related ways that all
report success while doing nothing. Deleting a text slice removes it from the
navigation index but leaves it in the scene graph, so the word is still drawn on
the page and is still searchable in the saved PDF. Correcting a slice changes
the text that gets saved but never repaints on the page. Clearing a slice
entirely is rejected because "empty text" is silently reinterpreted as "delete",
which then does nothing and refills the editor with the old text.

OCR text correction is an essential feature for a scanning application, so these
are not cosmetic defects: a user who corrects their OCR and deletes a
misrecognised line produces a PDF that still contains the wrong text, with no
indication that anything went wrong.

The root cause is that the layer being edited is held in three parallel
structures that are not kept in agreement: the bbox tree that is serialised to
hOCR (and therefore to the PDF), a confidence-sorted list used for navigation,
and a position-based tree iterator. The navigation structures are mutable and
are updated correctly; the serialised tree is mutated only through a method that
returns a throwaway copy of the children list, so every structural change to it
is silently discarded. The rendering path compounds this by caching each box's
Pango text layout on the model object and never invalidating it.

## What Changes

- Deleting a text slice (Delete button, or accepting an emptied slice) removes
  it from the scene graph, so it stops being drawn on the page and is absent
  from the hOCR that gets embedded in the saved PDF/DjVu.
- Correcting a text slice repaints the page, so the text shown over the page
  image matches the text that will be saved.
- After a correction or a deletion, navigation continues from the correct
  position, and the slice being edited is never a slice that no longer exists.
- Deleting the last slice of a line no longer leaves an empty line box behind in
  the serialised hOCR.
- The three parallel structures are given one owner for structural change, so
  the scene graph, the navigation indices and the serialised output cannot
  silently drift apart again.
- The annotation layer, which shares the same editor and the same scene-graph
  code, gains the same behaviour. Its delete is broken today for the same
  reason.

### Non-goals

- Undo/redo for text layer edits. `ocr-recognition` already requires the OCR
  *operation* to be undoable; making individual slice edits undoable is a
  separate concern with a different mechanism and is deliberately left alone
  here.
- Line-versus-word granularity of a click hit test. Pre-existing and unchanged.

## Capabilities

### New Capabilities

- `layer-editing`: The control bar and editor that correct, add, copy and delete
  individual text or annotation slices over a page, including how those actions
  commit to the page, advance navigation, and update what the user sees.

### Modified Capabilities

- `canvas-widget`: `delete_box` currently only guarantees the word disappears
  "from the display"; it must guarantee removal from the scene graph and
  absence from `hocr()` output. `update_box` currently promises the displayed
  text changes; it must guarantee the box is repainted. Position reordering and
  index maintenance after a structural change become explicit requirements
  rather than incidental behaviour.

## Impact

- `src/scantpaper/canvas.py`: `Bbox.get_children` (returns a filtered copy
  rather than the live child list), `Bbox.delete_box`, `Bbox.update_box`,
  `Bbox.to_hocr`, `Canvas._draw_bbox` (stale `pango_layout` cache),
  `Canvas.add_box`, `ListIter`, `TreeIter`.
- `src/scantpaper/layer.py`: `LayerEditor.ok`, `LayerEditor.delete`, and the
  navigation wiring in `_connect_controls`.
- `src/scantpaper/bboxtree.py`: `_prune_empty_branches` is currently only
  reachable on import; removing empty ancestor boxes after a delete may reuse or
  move it.
- Tests: `tests/test_7_canvas.py` and `tests/test_layer.py` assert on navigation
  and on mock call counts, which cannot observe this class of bug. New tests
  must assert on `canvas.hocr()` content and on scene-graph membership.
- No new dependencies. No change to the on-disk format, the saved PDF/DjVu
  format, or the SQLite schema.