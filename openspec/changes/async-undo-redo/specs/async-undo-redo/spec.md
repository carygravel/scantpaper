## ADDED Requirements

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
