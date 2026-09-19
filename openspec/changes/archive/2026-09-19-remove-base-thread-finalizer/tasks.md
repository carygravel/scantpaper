## 1. Remove finalizer registrations

- [x] 1.1 Remove `self._finalizer = weakref.finalize(...)` from
      `basethread.py:131`. Keep the `weakref` import (still used by the
      `LiveThreads` WeakSet) and the `queue` import (still used by `queue.Queue`
      types and `queue.Empty`).
- [x] 1.2 Remove the now-unused `BaseThread.cleanup_thread` static method
      (`basethread.py:141-152`).
- [x] 1.3 Remove the `weakref.finalize` registration in
      `basedocument.py:54-56`, then remove the now-unused `import weakref`
      (basedocument doesn't use weakref anywhere else).
- [x] 1.4 Remove the `weakref.finalize` registration in `dialog/sane.py:49-51`,
      then remove the now-unused `import weakref` (sane.py doesn't use weakref
      anywhere else).

## 2. Harden the worker cleanup path

- [x] 2.1 In `BaseThread.run()` (`basethread.py:260-272`), call
      `self._release_sources()` from a `finally` block so GLib sources and pipe
      FDs are released however the loop exits (quit break, handler error, or
      unexpected exception).

## 3. Tests

- [x] 3.1 Delete `testcleanup_thread_exception_caught`
      (`test_083_basethread.py:473-478`), which only exercises the removed
      function.
- [x] 3.2 Add a test that a dropped, un-quit worker is still stopped by
      `BaseThread.quit_all_live_threads()`: start a `BaseThread`, drop all
      references to it, run `gc.collect()`, then assert
      `quit_all_live_threads()` ends it. This pins the invariant the design
      relies on (the `run()` frame keeps the worker visible to the WeakSet).
- [x] 3.3 Add/adjust a test that `run()` releases sources even when the loop
      exits on the error path (e.g. a handler raising): assert
      `GLib.source_remove` is called for the io watch and tick ids after the
      worker stops, mirroring the existing `test_release_sources_close_oserror`
      approach.
- [x] 3.4 Assert no `PytestUnraisableExceptionWarning` related to thread
      finalizers appears in a test run (manual check via `pytest -W error` on
      the basethread and user-defined test modules).

## 4. Quality gates

- [x] 4.1 Format and lint: `ruff format` then `ruff check` (no new
      suppressions without maintainer approval, per AGENTS.md).
- [x] 4.2 Run the full suite (`pytest`) and confirm the coverage threshold is
      still met and no new uncovered lines are introduced beyond the standing
      TYPE_CHECKING exception.
- [x] 4.3 Confirm no README update is needed (no user-visible behaviour change)
      and mark the change ready for review.