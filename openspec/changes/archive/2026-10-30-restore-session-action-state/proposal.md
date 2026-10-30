# Proposal

## Why

A session with no recorded pages cannot be reopened into a usable document.
Restoring an empty crashed session leaves the document's current undo action
unset, so the first scan fails with
`TypeError: unsupported operand type(s) for +=: 'NoneType' and 'int'` and the
imported page is lost. This is the failure reported against 4.0.1.

The same action-state recovery also misses the newest step when it removes
every page: a session saved with no pages reopens showing the pages that were
deleted, and undo/redo resume one step behind.

Both are one defect. Opening a session recovers the current action from a
source that can be absent or out of date, instead of restoring the action the
document actually ended on.

## What Changes

- Opening a session restores the document's current action state from its
  recorded history, defaulting to the start of history when the session has
  no actions. The counter is always reset on open and never inherited from
  the previously open document.
- A restored session with no pages is a usable empty document: scanning or
  importing the first page succeeds and records the first undo step.
- Reopening a session whose latest action removed every page keeps the
  document empty; pages removed by that action do not come back.
- Undo and redo availability after reopening reflects the restored action,
  with one definition of "latest action" shared by open and redo.
- Regression tests cover reopening an empty crashed session, opening an
  empty saved session, and reopening after deleting every page. A changelog
  entry records the user-visible fix.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `session-persistence`: the capability gains a requirement that reopening a
  session restores its current action state, including a session with no
  pages and a session whose latest action removed every page, and that
  subsequent edits continue from that state.

## Impact

- `src/scantpaper/docthread.py`: session open recovers the action state, and
  redo shares the same "latest action" rule.
- `src/scantpaper/tests/test_docthread.py`: new regression tests.
- `changelog.md`: 4.0.2 entry.
- No database schema change or migration; the stored session format is
  unchanged.
- No new dependencies. The crash-recovery selection dialog is unchanged.
