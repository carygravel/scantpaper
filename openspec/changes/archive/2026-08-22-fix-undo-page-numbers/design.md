# Design: fix-undo-page-numbers

## Context

Two numbering conventions coexist. The `page_order` table stores 0-based
`row_id`s (first append into an empty document is 0; deletion renumbers
survivors from 0). The frontend convention is 1-based positions, maintained by
`Document.renumber()` after every add/delete/paste and on session open.
Undo/redo are the only bulk-restore paths that bypass `renumber()`:
`Document.undo()`/`unundo()` assign the worker's snapshot to `self.data`
verbatim with signals blocked (document.py `_undo_finished`/`_redo_finished`),
so raw `row_id`s reach the display column.

`_get_snapshot()` is the single producer of undo/redo snapshots; its only
callers are `do_undo` and `do_redo`.

## Goals / Non-Goals

**Goals:**

- Restored states display page numbers 1..n immediately, with no frontend
  fix-up pass.
- Fix the whole visible bug class reachable through undo/redo restore,
  including redo of deletions and odd/even selection parity after restore.

**Non-Goals:**

- Changing stored `row_id`s to 1-based (storage-contract renumbering).
- Migrating existing session files (none needed; nothing persisted changes).
- Auditing `clone_pages` destination coordinates or other latent
  coordinate-space mixing not reachable through the reported bug.

## Decisions

### Convert at the boundary inside `_get_snapshot()`

Each returned row's first element becomes `row[0] + 1`. Undo and redo share
this one code path, so both are fixed at once and no future caller of the
snapshot path can regress.

Alternatives considered:

- *Frontend `renumber()` after restore* — equally small, but leaves the
  thread emitting storage coordinates as "page numbers", so any new consumer
  of snapshots regresses; also spreads knowledge of the convention mismatch
  across modules.
- *Storage-wide 1-based `row_id`s* — cleaner invariant but requires a session
  migration across every `action_id` in each saved undo chain and reworking
  `clone_pages` destination semantics; disproportionate to the symptom
  (see proposal scope note).

The DB keeps its 0-based internal `row_id`; only the wire format of the
snapshot changes. This matches how `do_delete_pages` already reports removed
rows in UI terms rather than storage terms.

### Update tests to the corrected contract, add regression coverage

`test_db` currently asserts `snapshot[0][0] == 0` after undo and redo — the
bug enshrined. These become `== 1` / position-consistent assertions, plus a
dedicated regression test mirroring the reproduction: scan three pages, delete
one via `delete_pages`, undo, assert numbers are exactly `[1, 2, 3]`.

## Risks / Trade-offs

- [Snapshot rows double as data for other fields] → Only element 0 changes;
  thumbnail and `initial_page_id` positions are untouched. Tests covering
  ghost-page regressions (issue #74) read row index 2, unaffected.
- [Selection semantics] → Undo restores selection as frontend indices, which
  are position-based and unchanged by this conversion.
- [Latent divergence remains elsewhere] (`clone_pages` dest, `renumber()`
  reliance) → Accepted for now; documented here as the seam a future
  storage-invariant change would close.
