## 1. Document the session lifecycles

- [x] 1.1 Rewrite the README "Sessions" section to distinguish an unsaved
  session (temporary directory, removed on exit, restorable after a crash)
  from a session saved as `.sdb` and reopened (edited in place; Save As writes
  a copy; overwriting prompts first; quitting does not warn about unsaved
  pages).
- [x] 1.2 Add a bullet to the unreleased 3.0.22 section of `changelog.md`
  noting that a reopened `.sdb` is edited in place, that crash recovery no
  longer offers a stale snapshot of it, and that saved or reopened sessions
  are no longer reported as unsaved on quit.

## 2. Open in place without a stale snapshot

- [x] 2.1 In `BaseDocument.open_session()`, confirm the chosen file exists
  before changing anything, preserving the current "Unable to read" error
  dialog for a missing path while not creating an empty database at it.
- [x] 2.2 Replace the `shutil.copy(...)` snapshot with removing the temporary
  scratch database and its `-wal`/`-shm` sidecars after `thread.close()`, then
  open the chosen file in place.
- [x] 2.3 Update `test_basedocument.py` tests that assume the copy (notably
  `test_open_session_error_copy`) and add a regression test that opening a
  session makes the opened file the working database and leaves no restorable
  temporary snapshot.

## 3. Make the saved-work warning reflect persisted work

- [x] 3.1 In `DocThread`, remember the temporary scratch database path and add
  a predicate for whether the working database is that scratch database.
- [x] 3.2 Make `pages_saved()` return `True` when the working database is not
  the temporary scratch database.
- [x] 3.3 In the `sdb` branch of the save flow, mark the document's pages
  saved after the session is written.
- [x] 3.4 Add tests: an unsaved temporary document warns; a session saved as a
  file does not warn; a reopened session edited in place does not warn; and
  `pages_saved()` short-circuits for a persistent database.

## 4. Remove the dead `delete` keyword

- [x] 4.1 Drop the ignored `delete=False` keyword from the crash-restore call
  in `file_menu_mixins.py` and the corresponding handling in `open_session()`.

## 5. Verify

- [x] 5.1 Run `ruff format` and `ruff check`; fix any findings without adding
  suppressions.
- [x] 5.2 Run `ty check .` and clear all diagnostics.
- [x] 5.3 Run `pytest` and confirm the uncovered/partially-covered line counts
  are the same or better.
- [x] 5.4 Run `openspec validate session-inplace-editing --strict`.
