## Context

See proposal.md - Why for motivation. Current state that shapes the fix:

- Undo/redo is a snapshot chain over (`action_id`, `row_id`, `page_id`,
  `initial_page_id`) in `page_order` plus `selection`, advanced by
  `_take_snapshot()` (`docthread.py:805`), which copies only pointers,
  never page content.
- Operations that are undoable today go through `replace_page()`
  (`docthread.py:480`): take a snapshot, insert a NEW `page` row, repoint
  the current action's `page_order.page_id`. Undo then resolves the older
  action to the older row.
- `do_set_text` (`docthread.py:1054`) and `do_set_annotations`
  (`docthread.py:1088`) take a snapshot but then `UPDATE page SET ...`
  the row it just copied a pointer to, so the previous action - and every
  other action sharing that row - sees the new content. `do_undo`
  (`docthread.py:912`) steps the action id and returns identical content.
- `do_set_resolution` (`docthread.py:1115`) and `do_set_mean_std_dev`
  (`docthread.py:1145`) mutate in place with no snapshot at all, so a
  resolution change retroactively rewrites states recorded by other
  actions.
- All readers key off `initial_page_id` (getters in `docthread.py`,
  `Document`, the save flow, `EditMenuMixins`), never the physical `page`
  row id, so repointing a pointer needs no frontend change.
- The undo UI path already reloads the page and rebuilds the layer
  canvas: `Document.undo` (`document.py:351`) refills the list model
  (`simplelist.py:189`, model clear empties the selection) and re-selects,
  which fires selection-changed -> `_display_image` -> async `get_page` ->
  `_on_page_loaded` (`session_mixins.py:289`) -> `_text_editor.create`,
  which re-parses the page's layer. This is exactly the "focus reset to
  full-page split view" the reporter saw; with content versioned, the same
  reload will show the restored layer.

## Goals / Non-Goals

**Goals:**
- Undo and redo restore page content (text, annotations, resolution), not
  just page structure.
- Remove in-place mutation of shared `page` rows for content.
- One undo step for a multi-page Properties apply.
- The layer editor never keeps a slice focused after its canvas is rebuilt.
- A content edit returns the edited page to the unsaved state.
- No schema change, no new dependencies, no duplication of image blobs.

**Non-Goals:**
- Garbage-collecting `page` rows orphaned when a redo branch is truncated
  (pre-existing TODO at `docthread.py:852`).
- Batch mode for other multi-page flows (OCR, tools) - pre-existing, out
  of scope.
- Clearing a stale focused slice on the clear-OCR / New File canvas-clear
  paths (`edit_menu_mixins.py:222`, `file_menu_mixins.py:117`) - same
  staleness class, pre-existing, out of scope.

## Decisions

**1. Clone-and-repoint, mirroring `replace_page`.**

A private helper in `DocThread`, e.g. `_version_page(initial_page_id,
**overrides)`, SELECTs the row `page_order` currently points to for
`(initial_page_id, action_id)`, INSERTs a copy with overrides applied, and
repoints that action's `page_order.page_id`. Callers already call
`_take_snapshot()` first, so the merge order matches `replace_page`:
snapshot advances `action_id` and copies pointers, then the clone repoints
only the new action's row. The clone shares `image_id` - no image blob is
touched.

Alternatives considered and rejected:
- A content table keyed by (`action_id`, `initial_page_id`): cleaner
  normalisation but a schema migration and a change to every reader.
- An in-memory delta undo stack: contradicts the persisted-undo design,
  where history survives reopening a session.

**2. Guard against a missing page row.**

`UPDATE ... WHERE id = (SELECT ...)` today silently no-ops when nothing
matches. The helper keeps that: if no source row exists for the action,
return early after a warning. Avoid `INSERT .. SELECT` +
`last_insert_rowid()`, which would mis-repoint to an unrelated row when
nothing was inserted.

**3. Content edits dirty the page; all four content mutators use the helper.**

The invariant becomes: any handler that mutates `page` content takes a
snapshot, writes a new row, and marks that row unsaved (`saved = 0`).
`set_text`, `set_annotations`, `set_resolution`, `set_mean_std_dev` all
conform; `do_set_saved` and `mark_all_pages_saved` remain in-place because
their whole purpose is changing the flag. `set_mean_std_dev` has no
production caller, but leaving it in-place keeps the bug class alive.

`_version_page` writes `saved = FALSE` on the clone unconditionally, so a
page that was saved and then edited is no longer "persisted" - the
quit/new-file warning reappears for it. This matches `do_rotate` /
`do_crop`, which already set `page.saved = False` on their new row.
Undoing the edit restores the older row with its previous `saved` value,
so a fully reverted edit leaves the page considered saved again.
`do_set_saved` then marks the current row saved after a real save, so the
edit-then-save flow still cleans correctly.

One consequence: a resolution change in the Properties dialog is a content
edit, so it also dirties the affected pages (as rotation already does).

**4. Properties dialog batches, the message API stays one-per-page.**

`do_set_resolution` takes a snapshot per call; the dialog wraps its
per-page loop in `begin_undo_batch` / `end_undo_batch` (`document.py:405`),
so one Apply produces one action id and one undo step, satisfying
`multi-page-batch-operations`. Thread FIFO ordering guarantees the begin /
sends / end sequencing. This is the first production use of batch mode;
thread-level tests for it exist (`test_docthread.py:1525`).

Alternative rejected: making `set_resolution` accept a list of page ids
(like `do_set_saved`). It changes the message contract and its tests for
no gain over the specified, already-tested batch mechanism.

**5. Focus reset lives in the layer editor, triggered on rebuild.**

`LayerEditor.create()` clears focus (`_current_bbox = None` and an empty
control) before building the canvas; the finished-callback flows that
re-focus (e.g. `add()`'s "new layer" path, `layer.py:374`) still run
afterwards, so their focus survives. `_on_page_loaded`'s "no layer"
branches (`session_mixins.py:327,334`) switch from `t_canvas/a_canvas
.clear_text()` to an editor-level clear that also drops focus.

Alternatives rejected:
- Canvas emits a "tree replaced" signal the editor subscribes to: extra
  machinery for one consumer.
- Lazily validating `_current_bbox` before each action: every action pays
  and the control still shows stale text.

The reset only changes visible behaviour when focus was actually stale
(page switch, undo) - the control now empties instead of showing text from
another tree, consistent with the existing "no slice focused" semantics
used after deleting the last slice.

## Risks / Trade-offs

- [More `page` rows per session] Each content edit adds one row holding
  layer JSON and metadata; image blobs are shared. Acceptable; matches
  what `replace_page` already does for crop/rotate/OCR. Redo truncation
  can orphan rows - pre-existing TODO, unchanged in kind.
- [Tests assert the old in-place SQL] `test_do_set_text` /
  `test_do_set_annotations` / `test_do_set_resolution` /
  `test_do_set_mean_std_dev` mock `_execute` and assert the UPDATE string.
  They are rewritten as round-trip behaviour tests on a real in-memory DB
  (set -> undo -> old value, set -> redo -> new value), which are stronger.
- [First production use of batch mode] Mitigated by existing thread-level
  tests plus a new dialog-level assertion. If batching misbehaves, the
  fallback is per-page undo steps - still correct, just more steps.
- [Focus reset changes control behaviour on page switch] The control now
  empties rather than showing the previous page's text; new `layer-editing`
  scenario "Loading another page drops the previous page's slice" codifies
  the correct behaviour.
- [Undo's visual refresh depends on selection-changed firing] Verified
  deterministic: `Document.undo` refills the model (clearing the empty
  selection) and re-selects, so selection-changed always fires and
  `_on_page_loaded` always reloads the page and its layer.

## Migration Plan

None. No schema change and no change to the session file format; older
session files open unchanged and their shared rows behave as today until
the first content edit, after which subsequent states are versioned.
Rollback is a code revert.