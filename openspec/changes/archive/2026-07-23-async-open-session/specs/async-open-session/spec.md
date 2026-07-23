## ADDED Requirements

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
`self.data` and select the first page.

#### Scenario: Successful session open
- **WHEN** `open_session(db=path)` is called
- **THEN** the session file SHALL be copied to the temp location (synchronous)
- **AND** `thread.close()` SHALL be called to close the main thread's connection
- **AND** `row_changed_signal` SHALL be blocked
- **AND** `send("open", ...)` SHALL be dispatched to the worker thread
- **AND** upon open completion, `send("page_number_table", ...)` SHALL be dispatched
- **AND** upon table completion, `self.data` SHALL be set, signals unblocked,
  and `self.select(0)` called

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
