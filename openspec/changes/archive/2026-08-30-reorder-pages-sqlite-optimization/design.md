# Reorder pages with a dedicated SQLite operation — Design

## Context

See proposal.md — Why. The relevant machinery lives in `scantpaper/docthread.py`:

- `page_order` rows are `(action_id, row_id, page_id, initial_page_id)`; the
  current document state is the set of rows where `action_id == self._action_id`.
- `_take_snapshot()` (docthread.py:659) copies the current `page_order` +
  selection into a fresh `action_id` (clearing redo) — this is the undo buffer.
  Every mutating op calls it once.
- Today a drag = `clone_pages` (docthread.py:571) then `delete_pages`
  (docthread.py:451). Each calls `_take_snapshot()` and rewrites rows, and the
  clone also reads+rewrites image blobs and runs `_shift_row_ids`
  (docthread.py:354), a per-row `UPDATE` loop with a nested subquery.

## Goals / Non-Goals

**Goals:**
- One worker-thread `reorder_pages` operation that rewrites `page_order` row ids
  in a single pass, with exactly one `_take_snapshot()`.
- No image-blob reads or writes during reorder.
- Keep `clone_pages` for genuine copy/paste; only the drag path changes.

**Non-Goals:**
- A main-thread in-memory reorder (gscan2pdf-style instant feel). The chosen
  scope is the SQLite clone-path optimisation, ~3-5x on the worker thread for
  large documents. The async round-trip and model rebuild remain.
- Changing undo semantics, image storage format, or session format.

## Decisions

### D1: New `reorder_pages` message + `do_reorder_pages` handler
Add a `reorder_pages` request handled by `do_reorder_pages` on the worker
thread, mirroring `clone_pages`/`delete_pages`. It takes the moved `page_ids`,
the target `dest` row id, and the drop `how`.

### D2: Reorder is a read-then-rewrite, not incremental shifts
`do_reorder_pages`:
1. `_check_write_tid()` then `_take_snapshot()` (one snapshot).
2. `SELECT initial_page_id, row_id FROM page_order WHERE action_id = ? ORDER BY row_id`
   → the current ordered page list.
3. Remove the moved ids from that list, splice them back at `dest` (adjusting
   for `how`, as `paste_selection` does at basedocument.py:385-389).
4. Rewrite the whole list with a single
   `executemany("UPDATE page_order SET row_id = ? WHERE initial_page_id = ? AND action_id = ?", rows)`.
5. `commit()`, then return the moved pages' thumbnails (and new positions) so
   the main thread can update `self.data` and reselect — same shape as the
   clone response.

This avoids `_shift_row_ids`' per-row subquery loop and touches no `image`
table. One pass in, one pass out.

### D3: Suppress the `drag-data-delete` deletion for internal reorder
The DnD drop still fires `drag-data-delete` (basedocument.py:88) after a MOVE,
which today triggers `delete_selection`. If a reorder also deletes, we'd move
then delete the page. Mitigation: the drop handler sets a flag
(e.g. `tree._suppress_delete`) before dispatching the reorder, and
`delete_selection` (basedocument.py:405) checks it and clears it instead of
sending `delete_pages`. This keeps undo as exactly one step (the reorder
snapshot), per the spec.

### D4: UI path becomes a single `reorder_pages` send
In `drag_data_received_callback` (basedocument.py:653), the `ID_PAGE` branch
now computes moved ids from the selection plus `dest`/`how` from
`get_dest_row_at_pos`, sets the suppress flag, and calls
`thread.send("reorder_pages", ...)` instead of `copy_selection` +
`paste_selection`. The Edit-menu copy/paste path (edit_menu_mixins.py) is
untouched and keeps using `clone_pages`.

### D5: One snapshot, matching undo model
`_take_snapshot()` is called exactly once per reorder, so the drag is one undo
step. The redo buffer is still cleared by the snapshot, preserving existing
undo/redo behaviour.

**Alternatives considered:**
- Single `UPDATE ... CASE` statement: fewer round-trips, but the mapping is
  error-prone for block moves and hard to read; the executemany rewrite is
  clearer and still O(pages).
- In-memory main-thread reorder: instant feel but a bigger architectural
  change; explicitly a non-goal here.

## Risks / Trade-offs

- **Drag deletes the moved page** (drag-data-delete still fires) → Set the
  suppress flag in D3 and have `delete_selection` honour it; test explicitly.
- **Row-id collisions during a naive incremental rewrite** → D2 rewrites the
  full 0..n ordering in one `executemany`, so no transient collisions.
- **Selection lost after reorder** → Return the moved pages' positions from the
  response and reselect them, matching `paste_selection`'s
  `select_new_pages` behaviour.
- **Spec "no image duplication" could regress if a future path reuses clone for
  reorder** → `reorder_pages` simply never touches the `image` table; covered
  by tests asserting image row count is unchanged.
- **Double-drop callback** (known quirk, basedocument.py:653) → The reorder send
  is idempotent per drop via the existing `tree.drops` time-dedup guard.

## Migration Plan

Pure internal change; session/DB format unchanged. No data migration. Rollback:
revert the drop handler to clone+delete. No config or dependency changes.

## Open Questions

None — the spec, approach, and task breakdown are stable.