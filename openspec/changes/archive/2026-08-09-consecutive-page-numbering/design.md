## Context

See proposal.md — the stored `page_number` is redundant and its gaps are
surprising and unreliable. Verified in the code:

- `page_order` already carries `row_id`, which is kept in lockstep with
  `page_number` by `add_page`, `clone_pages`, and `delete_pages`
  (docthread.py:308, 585-623, 409-418). `row_id` IS the order key.
- In stored DBs, `ORDER BY row_id` and `ORDER BY page_number` produce the same
  order (the Renumber dialog only mutates the in-memory `self.data` and never
  reaches the DB, so the DB rows always stay in insertion/clone order).
- Positional insertion already exists: `split_page` and `crop` insert a new
  page after an existing one via `add_page(new, number+1)` + `insert-after`
  (docthread.py:1268-1273, 1442-1456). Scanning is the one flow that assigns
  raw numbers instead.

## Goals / Non-Goals

**Goals:**
- Page numbers always `1..n`, derived from position, never persisted.
- Scanning inserts positionally: append (single-sided / facing), insert-after
  (reverse pass, extended mode), all reusing the existing `insert-after`
  primitive.
- Rotation decided by the side being scanned, not number parity.
- Legacy sessions load and are renumbered on open.

**Non-Goals:**
- No new scanning capabilities (ADF, duplex hardware, batch). Only how new
  pages are placed.
- No "scanned so far / saved so far" counters.
- No change to save/export formats — the number never reached those anyway.

## Decisions

### 1. `row_id` becomes the position; `page_number` is dropped

`page_order` becomes `(action_id, row_id, page_id, initial_page_id)`. Display
order is `ORDER BY row_id`; the GUI derives the shown number as `index + 1`.

In memory, `self.data[i][0]` is renumbered to `i+1` after every mutation, so
the existing column-based code keeps working with the number always equal to
position.

*Alternative considered:* keep `page_number` but enforce the `1..n` invariant.
Rejected — it keeps two columns encoding the same sequence forever, which is
exactly the redundancy being removed.

### 2. One canonical order mutation: insert-at-position-with-shift

A single thread-side helper inserts a row at a position and shifts subsequent
`row_id`s +1 (reverse-order updates to avoid collisions — the pattern already
in `clone_pages`, docthread.py:599-605). Reused by:

- append (position = end),
- `insert-after <uuid>` (find the page's position, insert after it),
- number-column move (move to position N).

`delete_pages` already compacts `row_id` to `1..n`; it just stops touching
`page_number`.

### 3. Scan flow passes an insertion target and a side, not a number

`new-scan` emits `(image, insert_after, side, xres, yres)` instead of
`(image, page_number, xres, yres)`. `_new_scan_callback`
(scan_menu_item_mixins.py:390) then:

- chooses rotation from `side` ("facing" → rotate-facing, "reverse" →
  rotate-reverse) — replacing the `page_number % 2` parity test at line 399,
- forwards `insert_after` (a page uuid, or None to append) through
  `do_import_page` → `add_page(page, insert_after=...)`.

This is the one behavior that silently breaks if missed: parity is only
meaningful for the *final* position, which a reverse page does not yet have at
scan time.

### 4. Reverse pass: immediate insert-after (option B)

The dialog tracks the current batch while `side_to_scan == "facing"`:
`batch_start` (position of the first facing page of the pass) and `n` (facing
count). On switch to reverse, these are fixed. Reverse scan k (backs scanned
sheet n → 1) is inserted after the front of sheet `(n - k + 1)`, i.e. the page
at position `batch_start + n - k`. The maximum reverse pages (`max_pages`) is
`n`.

Because each back is placed immediately after its front, the document is in
correct interleaved order at every instant, numbers stay `1..n`, and a
mid-pass save is correctly ordered.

*Alternative considered (option A):* assign temporary numbers `n+1..2n`, then
bulk-renumber into even slots on a side switch. Rejected — mid-pass saves
would cluster all backs after all fronts, and it needs a renumber trigger.

### 5. Extended mode = "insert before page N"

The existing extended-mode frame (`framex`, pagecontrols.py:261) keeps its two
spinboxes but re-labels their meaning:

- Start → "Insert before page N"
- Increment → "position advance per subsequent scan" (default 1; 0 = keep
  stacking before N)

Each scan inserts at position `P + (k-1) * step`. This covers jam recovery
("re-scan page 7" → insert before 7) and out-of-order assembly.

### 6. Number arithmetic machinery is removed

`pages_possible`, `index_for_page`, `valid_renumber`, `_index2page_number`,
`find_row_id_by_page_number`, and the scan dialog's `max_pages` computation
are deleted. The only remaining bound is the reverse pass (`max_pages = n`).

### 7. Number-column edit = move to position

`_on_row_changed` (basedocument.py:113) stops sorting+renumbering and instead
moves the edited page to index `(value - 1)` through the existing cut/paste
clone path — the same persistence route drag-and-drop uses, so reorders reach
the DB exactly once.

### 8. Renumber dialog is removed

`dialog/renumber.py`, the Edit-menu item, and `renumber_dialog` in
`edit_menu_mixins.py` are deleted along with their tests. Drag, paste, and the
number-column edit are the only reordering paths, all DB-backed.

### 9. Legacy sessions migrate on open

On `do_open`, detect the legacy `page_order` schema (has `page_number`); if
present, rebuild the table without it, preserving all `action_id` rows so
undo/redo history survives:

```
CREATE TABLE page_order_new (...);           -- no page_number
INSERT INTO page_order_new SELECT action_id, row_id, page_id, initial_page_id
  FROM page_order;
DROP TABLE page_order; ALTER TABLE page_order_new RENAME TO page_order;
```

Rows are ordered by `row_id` (proven equivalent to old `page_number` order in
stored DBs), then numbered `1..n` in memory.

*Alternative considered:* keep an inert `page_number` column. Rejected — it
perpetuates the redundancy and every insert would still have to write it.

## Risks / Trade-offs

- **Reverse-pass anchor depends on batch tracking.** If the user interleaves
  other edits mid-pass, the computed anchor may no longer match.
  → Recompute anchors from the current document state; extended mode remains
  available for manual slotting.
- **Per-scan insert shifts rows (O(n)).** Fine for realistic documents
  (tens/hundreds of pages, single UPDATE); same cost as the existing paste path.
- **Failed scans during a batch (jam).** A queued scan that errors must not
  advance the reverse-pass counter.
  → Count completed scans, not queued ones.
- **Legacy migration touches every stored session once.** Table rebuild is
  atomic in SQLite; tested against fixtures with gaps and with undo history.
- **Large test surface.** Renumber/pages_possible/scan-dialog tests change
  behavior. Coverage must not drop (AGENTS.md). Removed code paths reduce
  required lines; deleted dialogs drop their tests.

## Migration Plan

1. Schema: new CREATE TABLE omits `page_number`; `do_open` migrates legacy
   DBs (Decision 9).
2. No user-facing migration message needed — numbers were editorial and never
   survived save/export.
3. Rollback: keep the change behind the normal release cycle; legacy files
   remain readable by both old and new code.

## Open Questions

- Should file imports (not just scans) honor insert-after in the UI? Imports
  currently append; likely fine, but the dialog affordance is not specified
  here.
- Exact label wording for the extended-mode spinboxes ("Insert before page N").
