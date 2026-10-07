## MODIFIED Requirements

### Requirement: Chained open then page table
`BaseDocument.open_session()` SHALL send `"open"` first, then in its
`finished_callback` send `"page_number_table"`, then in that callback populate
`self.data` and select the first page. When the open was initiated by a file
import (File → Open of a session file), the import flow's completion SHALL be
signalled once the page table has been populated and the first page selected,
so the importing flow can finalise its state (e.g. release the thumbnail-only
display used during imports).

#### Scenario: Successful session open
- **WHEN** `open_session(db=path)` is called
- **THEN** the session file SHALL be copied to the temp location (synchronous)
- **AND** `thread.close()` SHALL be called to close the main thread's connection
- **AND** `row_changed_signal` SHALL be blocked
- **AND** `send("open", ...)` SHALL be dispatched to the worker thread
- **AND** upon open completion, `send("page_number_table", ...)` SHALL be dispatched
- **AND** upon table completion, `self.data` SHALL be set, signals unblocked,
  and `self.select(0)` called

#### Scenario: Session opened through File → Open completes the import
- **WHEN** a session file is opened through the File → Open import flow
- **AND** the page table has been populated and the first page selected
- **THEN** the import flow's completion callback SHALL be invoked
- **AND** the import flow SHALL finalise its state, including stopping any
  thumbnail-only display suppression and finishing its progress reporting