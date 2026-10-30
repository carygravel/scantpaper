# Design

## Context

See `proposal.md` - Why.

Session state is one SQLite database (`src/scantpaper/docthread.py`). The undo
history is recorded in two tables:

- `page_order` stores the page set for each action. A snapshot copies the rows
  of the previous action, so older actions remain available for undo.
- `selection` stores one row per action. `_take_snapshot()` writes it before
  the caller adds page rows, so the row exists even when the action's page set
  is empty.

`DocThread.open()` currently recovers the current action with
`SELECT MAX(action_id) FROM page_order` and assigns it whenever the query
returns a row. Because `MAX()` always returns a row, a session with no
recorded actions assigns `NULL` to `_action_id` (the `cast("int", ...)` is a
runtime no-op), and the first edit fails at `_action_id += 1`.

The same query is also behind: after an action removes every page, that action
has no `page_order` rows, so the maximum is an older action that still has
pages. Reopening such a session shows a superseded page set.

`can_redo()` already treats both tables as the history (the maximum of the two
maxima), while `open()` uses only one.

## Goals / Non-Goals

**Goals:**

- Derive the restored action from the complete recorded history, with an
  explicit default for a session that has no actions.
- Keep `open()` and `can_redo()` on the same definition of "latest action".
- Keep the change inside the open path and the existing session format.

**Non-Goals:**

- Persisting the last-viewed action when a user undoes, then saves, and
  reopens. Reopening will still land on the latest recorded action; undo and
  redo steps remain in the file. Fixing this needs the current action stored
  in the session database, which is a schema change.
- Changing the crash-recovery dialog or filtering empty crashed sessions.
  That is UX mitigation, not the state invariant, and can be a separate
  change.
- Any change to how snapshots are recorded or pruned.

## Decisions

### Decision: The restored action is the maximum across both history tables

Compute the latest action as the maximum of `MAX(page_order.action_id)` and
`MAX(selection.action_id)`, treating a missing maximum as no action. Assign
the result to `_action_id` unconditionally on open, using `0` when both tables
are empty.

Rationale: `selection` is the action ledger. It has a row for every snapshot,
including actions whose page set is empty, so it is the only table that can
identify the latest action after a clear. `page_order` says which pages an
action shows, not which actions exist.

Alternatives considered:

- `MAX(page_order.action_id) or 0` - fixes the crash but still restores an
  older action after a clear, resurrecting deleted pages.
- Keeping the class attribute default and assigning only when a maximum is
  present - leaves a reused `DocThread` with the previous document's counter,
  because `open()` can run on the same object after `close()`.

### Decision: One definition of "latest action" for open and redo

Put the two-table maximum in a helper used by both `open()` and `can_redo()`.
Keep `can_undo()` on its existing minimum-across-both rule.

Rationale: the bug exists because two methods disagreed about what the latest
action is. Sharing the expression prevents them from drifting again. Redo
already depends on the same invariant to decide whether a later action exists.

Alternative considered: duplicate the two-table maximum in both methods.
Smaller diff, but leaves the same failure mode for the next edit.

### Decision: Make the no-history case explicit instead of casting it away

Convert the query result to an `int` only after establishing that it is one,
and use `0` for an empty history. Do not keep `cast("int", row[0])` as the
only guard: it tells `ty` what the code wants, not what SQLite returned.

Rationale: the unchecked assertion is why static checking could not see this.
The explicit branch also documents the initial state of an empty document.

### Decision: No schema change

The information needed is already stored. Existing sessions open under the
same `USER_VERSION`; `save_as()` remains a `VACUUM INTO` copy. Sessions saved
with a cleared latest action now reopen empty, which is the recorded state.

Rationale: the defect is in reading the history, not in recording it. A
migration would add risk without adding capability.

### Decision: Regression tests at the DocThread boundary

Cover the observable contract from the delta spec with real SQLite databases:
reopen an empty session and add a page; reopen a session cleared by a delete;
open a second empty session after a populated one; and check undo and redo
availability after reopening. Exercise `save_as()` plus `open()` rather than
mocking the queries, so the tests fail against the current code for the same
reason the user's session did.

## Risks / Trade-offs

- **Restored state changes for cleared sessions** -> Sessions whose latest
  action removed every page now reopen empty instead of showing superseded
  pages. This is the intended correction; the earlier actions are intact, so
  undo still restores them.
- **A session saved after an undo still reopens at the latest action** ->
  Unchanged from today and documented as a non-goal. The alternative is a
  schema change to store the current action.
- **Stale action state on a reused thread** -> Assigning the counter
  unconditionally removes the old value. A regression test opens a second
  empty session to pin this down.
- **Empty crashed sessions are still offered** -> Restoring one is now
  harmless: it opens an empty, usable document. Filtering it out is left to
  a separate UX change.

## Migration Plan

No data migration. Ship as a normal code update and add a 4.0.2 changelog
entry. Rolling back restores the previous read behaviour; no session file is
modified by the fix. Existing session files remain readable in both
directions because the format is unchanged.

## Open Questions

- Should the crash-recovery dialog skip sessions with no pages, or offer a
  cancel option? Deferrable; it does not change this spec or approach.
- Should a session persist where the user was in the undo history, so an
  undone edit stays undone after save and reopen? Deferrable; it needs a
  schema change and its own spec.
