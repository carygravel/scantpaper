## 1. Worker-side handlers

- [x] 1.1 Add `do_open()` method to `DocThread` in `docthread.py` — calls `self.open(request.args[0])` on the worker thread
- [x] 1.2 Add `do_page_number_table()` method to `DocThread` in `docthread.py` — moves existing `page_number_table()` logic into a handler that returns the rows list
- [x] 1.3 Remove synchronous `page_number_table()` method from `DocThread`

## 2. Main-thread open_session rewrite

- [x] 2.1 Rewrite `BaseDocument.open_session()` in `basedocument.py` to: copy file sync, call `thread.close()`, block `row_changed_signal`, then `send("open", db, finished_callback=on_open)`
- [x] 2.2 In `on_open` callback: `send("page_number_table", finished_callback=on_table)`
- [x] 2.3 In `on_table` callback: unblock `row_changed_signal`, set `self.data`, call `self.select(0)`
- [x] 2.4 Wire `error_callback` from kwargs to both `send()` calls

## 3. Tests

- [x] 3.1 Update tests that call `thread.page_number_table()` directly to use async dispatch
- [x] 3.2 Update tests that exercise `open_session()` if they assert on synchronous behavior
- [x] 3.3 Run `pytest` and verify all tests pass
