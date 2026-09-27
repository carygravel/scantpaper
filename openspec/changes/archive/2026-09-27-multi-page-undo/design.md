## Context

See proposal.md (Why) and the delta specs for requirements.

The undo model is append-only and lives in SQLite. Each page-editing
operation funnels through `DocThread.replace_page()`
(`src/scantpaper/docthread.py:467`), which:

1. calls `_take_snapshot()` — copies the current live `page_order` into a
   fresh `action_id` and clears any redo steps (`docthread.py:792`);
2. inserts a new page/image row and points the new `action_id`'s
   `page_order` at it.

So `action_id` always references the latest live state, and undo simply
decrements it to reveal the previous snapshot. Rotate and crop both go
through `replace_page`. The frontend dispatches multi-page operations as a
loop of single-page thread requests — `_rotate` (`tools_menu_mixins.py:78`)
and `crop_selection` (`tools_menu_mixins.py:419`) call `slist.rotate(...)` /
`slist.crop(...)` once per page — so each iteration takes its own snapshot,
producing N undo steps for N pages.

## Goals / Non-Goals

**Goals:**
- Make a multi-page operation a single atomic undo/redo step.
- Keep single-page operations and all other callers of `replace_page`
  behaving exactly as before.
- Localize the change to the worker-thread snapshot logic and the two
  multi-page loops the user reported (rotate, crop selection).

**Non-Goals:**
- Rewriting the undo storage model or migrating the SQLite schema.
- Batching operations the user did not report (e.g. post-process
  multi-page rotate, unpaper across a range) — the mechanism is reusable and
  can be applied later, but is out of scope here.
- Solving the known orphaned `page`/`image` row accumulation (existing TODO
  at `docthread.py:833`).

## Decisions

### Decision: A batch flag that gates `_take_snapshot` on the worker thread
Add a `_in_batch` flag to `DocThread`. `_take_snapshot()` returns early when
the flag is set, so page operations inside a batch stop recording individual
undo steps. Because every page-editing op already funnels through
`replace_page` → `_take_snapshot`, this single gate covers rotate, crop, and
any future page-replacing operation with no per-op changes.

- Rationale: minimal, localized, and future-proof. No schema or model
  changes.
- Alternative considered: a full transaction/commit API on the thread — more
  invasive and not needed; the existing snapshot mechanism already gives us
  atomicity if we just suppress intermediate snapshots.

### Decision: The batch takes its one snapshot lazily on the first page op
`do_begin_batch` sets `_in_batch` and arms `_batch_pending_snapshot`.
`_take_snapshot()` performs its normal work (redo cleanup, copy the live
`page_order` into a fresh `action_id`) only on the first page operation in
the batch, then disarms the flag; later operations in the batch return early
without a snapshot. `do_end_batch` clears the flag.

- Rationale: yields one undo step whose snapshot is the pre-batch state, so a
  single undo restores every page, and matches the existing snapshot
  semantics precisely (undo points at the pre-batch `action_id`).
- Refinement over the initial sketch: the snapshot is deferred to the first
  operation rather than taken eagerly in `do_begin_batch`, so an empty batch
  (e.g. rotate invoked with no selection) does not leave a spurious undo
  step behind.
- Alternative considered: taking the snapshot eagerly in `do_begin_batch` and
  at `end_batch` — more moving parts and leaves an empty undo step for
  empty batches.

### Decision: Batch begin/end are async thread requests
`begin_batch` / `end_batch` are sent via the thread's `send(...)` mechanism
so they run on the worker thread, honouring `_check_write_tid()` ordering
and the existing callback pattern (mirroring `rotate`/`crop` at
`docthread.py:1121`/`:1325`).

### Decision: Frontend exposes `begin_undo_batch` / `end_undo_batch`
`Document`/`BaseDocument` forward these to the thread. The multi-page loops
wrap their iteration in a `try/finally` so `end_undo_batch` always runs even
if an operation errors mid-loop, leaving a single (partial) undo step rather
than a stuck batch flag.

## Risks / Trade-offs

- **Error mid-batch leaves partial state under one step** → `try/finally`
  guarantees `end_undo_batch`; the begin-time snapshot remains the single
  undo point, so the partial batch is still coherently revertible.
- **Stuck `_in_batch` flag if a callback never fires** → `try/finally` in the
  frontend, plus the gate being thread-local to a request stream; low risk.
- **Orphaned `page`/`image` rows accumulate within a batch** → unchanged
  pre-existing behaviour (see Non-Goals); each batch still leaves only the
  final page rows referenced by the batch `action_id`.
- **Only rotate and crop-selection are batched now** → other multi-page
  loops remain one-step-per-page; documented as future work reusing the same
  gate.

## Migration Plan

No schema change and no persisted-state migration. The new batch API is
additive; existing session files and undo chains remain valid.

## Open Questions

None — the approach and task breakdown are unaffected by any deferrable
unknown.
