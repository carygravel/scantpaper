## 1. Worker-side handlers

- [ ] 1.1 Add `do_undo()` method to `DocThread` in `docthread.py` — decrements `_action_id`, calls `_get_snapshot()` and `get_selection()`, returns `{"snapshot": ..., "selection": ...}`
- [ ] 1.2 Add `do_redo()` method to `DocThread` in `docthread.py` — increments `_action_id`, calls `_get_snapshot()` and `get_selection()`, returns `{"snapshot": ..., "selection": ...}`
- [ ] 1.3 Remove synchronous `DocThread.undo()` and `DocThread.redo()` methods (now replaced by `do_undo` / `do_redo` handlers)

## 2. Main-thread callers

- [ ] 2.1 Convert `Document.undo()` in `document.py` to use `thread.send("undo", finished_callback=...)` — move signal blocking/unblocking and `self.data` assignment into the callback
- [ ] 2.2 Convert `Document.unundo()` in `document.py` to use `thread.send("redo", finished_callback=...)` — same callback pattern
- [ ] 2.3 Ensure `_update_uimanager()` is called in the finished callback to refresh menu states

## 3. Error handling

- [ ] 3.1 Wire `error_callback=self._error_callback` to both undo and redo `send()` calls — handles `StopIteration` when no undo/redo steps remain
- [ ] 3.2 Disable undo menu item immediately on undo trigger to prevent rapid double-click races

## 4. Tests

- [ ] 4.1 Update `test_document.py` test_undo to work with async undo (use nested `GLib.MainLoop` or callback pattern)
- [ ] 4.2 Update any other tests that call `thread.undo()` or `thread.redo()` directly
- [ ] 4.3 Run `pytest` and verify all tests pass
