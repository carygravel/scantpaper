# async-undo-redo

## Purpose

Dispatch undo and redo through the worker thread's message-passing mechanism so document snapshot restoration and selection don't block the GUI.

## Requirements

### Requirement: Async undo dispatch
`DocThread` SHALL handle undo requests via the `send("undo", ...)` message-passing
mechanism rather than synchronous method calls. The `do_undo()` handler SHALL execute
on the worker thread.

#### Scenario: Undo returns snapshot and selection atomically
- **WHEN** `send("undo", finished_callback=cb)` is called and the worker thread
  processes the request
- **THEN** the `finished_callback` receives a response whose `info` contains both
  `snapshot` (list of `[page_number, pixbuf, initial_page_id]`) and `selection`
  (list of selected row IDs)

#### Scenario: Undo when no undo steps available
- **WHEN** `send("undo", error_callback=err_cb)` is called but `can_undo()` is false
- **THEN** the `error_callback` SHALL be invoked with a `StopIteration` error message

### Requirement: Async redo dispatch
`DocThread` SHALL handle redo requests via the `send("redo", ...)` message-passing
mechanism. The `do_redo()` handler SHALL execute on the worker thread.

#### Scenario: Redo returns snapshot and selection atomically
- **WHEN** `send("redo", finished_callback=cb)` is called and the worker thread
  processes the request
- **THEN** the `finished_callback` receives a response whose `info` contains both
  `snapshot` and `selection`

#### Scenario: Redo when no redo steps available
- **WHEN** `send("redo", error_callback=err_cb)` is called but `can_redo()` is false
- **THEN** the `error_callback` SHALL be invoked with a `StopIteration` error message

### Requirement: Document undo uses async dispatch
`Document.undo()` SHALL use `thread.send("undo", ...)` with a `finished_callback`
that updates `self.data`, blocks/unblocks signals, and reselects pages.

#### Scenario: Undo updates page list
- **WHEN** user triggers undo and the async response arrives
- **THEN** `self.data` SHALL be set to the snapshot from the response
- **AND** `row_changed_signal` and `selection_changed_signal` SHALL be blocked
  during the update
- **AND** the selection SHALL be restored from the response's selection data

### Requirement: Document redo uses async dispatch
`Document.unundo()` SHALL use `thread.send("redo", ...)` with the same callback
pattern as undo.

#### Scenario: Redo updates page list
- **WHEN** user triggers redo and the async response arrives
- **THEN** `self.data` SHALL be set to the snapshot from the response
- **AND** signals SHALL be blocked during the update
- **AND** the selection SHALL be restored

### Requirement: Undo menu state management
The undo menu item SHALL be disabled immediately when undo is triggered and
re-evaluated after the async operation completes via `_update_uimanager()`.

#### Scenario: Undo button disabled during async operation
- **WHEN** user triggers undo
- **THEN** `_update_uimanager()` SHALL be called to refresh menu/button states
- **AND** `can_undo()` / `can_redo()` SHALL continue to work correctly during
  the async operation (they remain synchronous Tier 1 methods)

### Requirement: Undo and redo restore 1-based page numbering
The snapshots delivered by undo and redo SHALL carry page numbers that are
1-based positions in the restored order, identical to what the page list would
display for that order. Snapshot page numbers SHALL NOT expose internal
storage row identifiers or zero-based indices.

#### Scenario: Undoing a deletion restores consecutive numbering
- **WHEN** the first page of a three-page document is deleted and the
  deletion is undone
- **THEN** the restored pages SHALL be numbered 1, 2, 3

#### Scenario: Redo of a deletion keeps numbering consecutive
- **WHEN** a deletion is undone and then reapplied with redo
- **THEN** the remaining pages SHALL be numbered consecutively from 1

#### Scenario: Restored numbers always match positions
- **WHEN** any document state is restored via undo or redo
- **THEN** each restored page number SHALL equal its 1-based position in the
  restored order, with no gaps and no duplicates
