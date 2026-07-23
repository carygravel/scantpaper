## ADDED Requirements

### Requirement: Test helper for async get_page
The `get_page_sync()` helper SHALL wrap the async `send("get_page", ...)` in a
nested `GLib.MainLoop`, making it usable as a drop-in replacement for the former
synchronous `thread.get_page()` in tests.

#### Scenario: Helper blocks until response
- **WHEN** `get_page_sync(thread, id=page_id)` is called
- **THEN** a nested `GLib.MainLoop` SHALL be created and run
- **AND** the `finished_callback` SHALL quit the loop and store the result
- **AND** the helper SHALL return the `Page` object after the loop exits

#### Scenario: Helper forwards errors
- **WHEN** `get_page_sync(thread, id=invalid_id)` is called
- **AND** the worker thread raises a `ValueError`
- **THEN** the helper SHALL re-raise the exception after the loop exits

#### Scenario: Helper location
- **WHEN** the helper is created
- **THEN** it SHALL be placed in a shared test utilities module (e.g.,
  `scantpaper/tests/helpers.py` or added to `conftest.py`)
- **AND** all test files calling `thread.get_page()` SHALL import and use it
