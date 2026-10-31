# async-open-session

## Purpose

Open a document session asynchronously through the worker thread so the database load and page snapshot don't block the GUI.

## Requirements

### Requirement: Async database open
`DocThread` SHALL handle open requests via the `send("open", ...)` message-passing
mechanism. The `do_open()` handler SHALL execute on the worker thread and call
the existing `self.open(db)` method.

#### Scenario: Database opened on worker thread
- **WHEN** `send("open", db_path, finished_callback=cb)` is called
- **THEN** the worker thread SHALL open the database at `db_path`
- **AND** perform PRAGMA checks and migrations
- **AND** invoke `finished_callback` on success

#### Scenario: Database open failure
- **WHEN** `send("open", invalid_path, error_callback=err_cb)` is called
- **AND** the database cannot be opened or validated
- **THEN** `error_callback` SHALL be invoked with the error details

### Requirement: Async page_number_table
`DocThread` SHALL convert `page_number_table()` from a synchronous method to a
`do_page_number_table()` handler invoked via `send()`.

#### Scenario: Page table returned via async response
- **WHEN** `send("page_number_table", finished_callback=cb)` is called
- **THEN** the worker thread SHALL query the page order, page, and image tables
- **AND** deserialize thumbnail pixbufs for each row
- **AND** invoke `finished_callback` with the rows list as `response.info`

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
- **THEN** `thread.close()` SHALL be called to close the main thread's
  connection
- **AND** the temporary scratch database and its sidecars SHALL be removed
- **AND** `row_changed_signal` SHALL be blocked
- **AND** `send("open", ...)` SHALL be dispatched to the worker thread with the
  selected file as the working database, in place
- **AND** upon open completion, `send("page_number_table", ...)` SHALL be
  dispatched
- **AND** upon table completion, `self.data` SHALL be set, signals unblocked,
  and `self.select(0)` called

#### Scenario: Session opened through File → Open completes the import
- **WHEN** a session file is opened through the File → Open import flow
- **AND** the page table has been populated and the first page selected
- **THEN** the import flow's completion callback SHALL be invoked
- **AND** the import flow SHALL finalise its state, including stopping any
  thumbnail-only display suppression and finishing its progress reporting

#### Scenario: Open fails, table not requested
- **WHEN** `open_session(db=invalid_path)` is called
- **AND** the `"open"` request fails
- **THEN** `error_callback` SHALL be invoked
- **AND** `page_number_table` SHALL NOT be sent

#### Scenario: Table fails after successful open
- **WHEN** `open_session(db=path)` is called
- **AND** `"open"` succeeds but `"page_number_table"` fails
- **THEN** `error_callback` SHALL be invoked
- **AND** `row_changed_signal` SHALL be unblocked

### Requirement: Crash restore copies a snapshot before opening

`BaseDocument` SHALL restore a crashed snapshot by copying it into the current
temporary session database on the worker thread and then opening that database
through the normal open and page-table chain. It SHALL NOT open the snapshot in
place. The copy SHALL target a temporary file so that a failed copy leaves the
current database and the snapshot intact. The snapshot SHALL be consumed only
after the restored page table has been populated.

#### Scenario: A snapshot is copied, opened and consumed

- **WHEN** a crash restore is requested for a valid snapshot
- **THEN** the worker thread SHALL copy the snapshot into the current temporary
  session database using a temporary file
- **AND** the copied database SHALL be opened through the normal open chain
- **AND** the page table SHALL be populated from the copied database
- **AND** only then SHALL the snapshot be removed

#### Scenario: A copy failure leaves the current document and snapshot intact

- **WHEN** a crash restore is requested
- **AND** the snapshot cannot be read or copied
- **THEN** the error callback SHALL be invoked
- **AND** the current database SHALL remain unchanged
- **AND** the snapshot SHALL remain intact
- **AND** `page_number_table` SHALL NOT be sent

#### Scenario: An open failure leaves the snapshot intact

- **WHEN** the snapshot is copied successfully
- **AND** the copied database cannot be opened
- **THEN** the error callback SHALL be invoked
- **AND** the snapshot SHALL remain intact
- **AND** `page_number_table` SHALL NOT be sent

#### Scenario: A non-scantpaper database is rejected before copying

- **WHEN** a crash restore is requested for a file that is not a scantpaper
  session
- **THEN** the restore SHALL fail with an error
- **AND** the current database SHALL remain unchanged
- **AND** the file SHALL NOT be consumed