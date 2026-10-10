## Why

Undo and redo (the toolbar arrows) never revert text-layer or annotation
corrections. The snapshot chain versions only page *pointers*
(`page_order` and `selection`), while `set_text` and `set_annotations`
update the single shared `page` row in place, so every action id resolves
to the same post-edit content. A user who accidentally deletes a text box
and presses undo sees only the view snap back to full-page fit; the box
never comes back. The same in-place pattern in `set_resolution` (which
takes no snapshot at all) lets a later resolution change rewrite what an
*earlier* undo step restores.

## What Changes

- Text-layer and annotation corrections (accept, add, duplicate, delete)
  become real undo/redo steps: undo restores the previous layer and shows
  it on the page again, redo re-applies the edit.
- Every page-content mutator in the document thread (`set_text`,
  `set_annotations`, `set_resolution`, `set_mean_std_dev`) records an undo
  step and writes a fresh `page` row for the current action instead of
  updating the shared row, following the pattern `replace_page` already
  uses. Image rows are shared, never duplicated. No schema change and no
  migration.
- Applying a resolution change to a selection of pages from the Properties
  dialog stays a single undo step, wrapped in the existing batch
  mechanism that `multi-page-batch-operations` already requires.
- After the layer canvas is rebuilt - by undo, redo, or loading another
  page - the layer editor no longer keeps a slice from the old canvas
  focused, so a following accept or delete cannot silently act on a stale
  slice.
- Editing a page's content (text, annotations, resolution) now marks the
  page as unsaved, so quitting after editing a page that was previously
  saved offers to save it again. Rotation and cropping already did this;
  text editing silently lost this guarantee.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `async-undo-redo`: page content mutations are recorded as versioned
  undo steps, and undo restores prior content rather than only page
  structure and order.
- `layer-editing`: layer edits are undoable and redoable end to end, and a
  rebuilt layer clears the focused slice.
- `session-persistence`: a content edit after pages were marked saved
  returns those pages to unsaved, so the unsaved-work warning reflects
  further edits.

## Impact

- `src/scantpaper/docthread.py`: `do_set_text`, `do_set_annotations`,
  `do_set_resolution`, `do_set_mean_std_dev`, plus a private page-row
  versioning helper.
- `src/scantpaper/layer.py`: reset the focused slice when the canvas is
  rebuilt or emptied.
- `src/scantpaper/session_mixins.py`: route the page-load "no layer"
  branches through the editor so focus is reset with the canvas.
- `src/scantpaper/edit_menu_mixins.py`: batch the Properties dialog's
  per-page `set_resolution` sends.
- Tests: rewrite the SQL-asserting unit tests in `test_docthread.py` as
  round-trip behaviour tests, and extend `test_layer.py`,
  `test_session_mixins.py`, `test_edit_menu_mixins.py`.
- Unsaved-work warning: after an output file was written, a further
  content edit on a page now counts as unpersisted and re-enables the
  quit/new-file warning for it.
- Storage: one extra `page` row per content edit in the session database
  (text/annotation JSON and metadata only; image rows are shared).
  Redo-branch truncation can orphan those rows, which is the pre-existing
  TODO in `_take_snapshot`, unchanged in kind.
- No new dependencies, no change to the saved session format.
