# Tasks

## 1. Worker-thread snapshot restore

- [x] 1.1 Add a `restore_snapshot` request to `DocThread` that validates the
  snapshot's `application_id`, copies it with SQLite's backup API into a
  `<scratch>.restore` file, atomically replaces the scratch database, and opens
  the copy. Verify `test_docthread.py` covers a valid copy, a non-scantpaper
  database, an unreadable snapshot and stale `.restore` files.

- [x] 1.2 Add `BaseDocument.restore_session()` that sends the restore request
  and chains `page_number_table` only after the copy has opened. Verify
  `test_basedocument.py` covers success, copy failure, open failure and that
  the page table is not requested after a failure.

- [x] 1.3 Add snapshot consumption in the restore completion path: unlink the
  snapshot database first, then its `-wal`/`-shm` sidecars, then remove its
  session directory, and only after the page table has populated the document.
  Verify tests cover a successful consume, a consume failure that leaves the
  snapshot, and an orphaned snapshot with no session directory.

- [x] 1.4 Show the existing post-process progress bar in pulse mode while the
  restore request runs, and finish it on success or error. Verify a test asserts
  the progress bar starts and finishes on both outcomes.

- [x] 1.5 Verify a restored document is treated as temporary: `_db` equals
  `_temp_db`, `db_is_temporary()` is true, and `pages_saved()` uses the page
  flags rather than the in-place shortcut. Add regression tests in
  `test_docthread.py` and `test_basedocument.py`.

- [x] 1.6 Keep the normal `open_session()` path unchanged: it still removes the
  scratch database and opens the selected `.sdb` in place, without copying.
  Verify `test_basedocument.py` and `test_file_menu_mixins.py` cover an
  in-place open and that no snapshot is created.

## 2. Discovery, locking and the shared picker

- [x] 2.1 Replace the blocking lock probe with a non-blocking helper that keeps
  the lock handle and uses `<db>.lock` for a snapshot without a session
  directory. Verify tests show a locked session is skipped without blocking,
  the handle stays held, and orphan snapshots get a separate lock file.

- [x] 2.2 Split discovery from the dialog: return the list of snapshots,
  skipping the current session and sessions whose lock cannot be taken, and
  keep including empty and orphaned snapshots. Verify `test_session_mixins.py`
  covers current-session skipping, in-use skipping, empty snapshots and
  orphans.

- [x] 2.3 Build one picker with **Restore**, **Discard** and **Cancel** and use
  it from startup and from **File → Open crashed session**. Verify tests assert
  both entry points use the same dialog, the File menu no longer constructs a
  folder chooser, and the File menu reports when the list is empty.

- [x] 2.4 Implement **Discard**: confirm the action, delete every selected
  snapshot and its session directory, and keep the picker usable after a
  cancelled confirmation. Use `ngettext` for the count-dependent message.
  Verify `test_session_mixins.py` covers one snapshot, several snapshots,
  cancellation and an empty selection.

- [x] 2.5 Ask the existing unsaved-work question before a File-menu restore
  replaces a non-empty document, and skip it at startup. Verify
  `test_file_menu_mixins.py` covers both paths.

- [x] 2.6 Release every picker lock on Cancel, Discard, Restore and unexpected
  dialog destruction. Verify tests exercise each path and assert the lock
  handles are closed exactly once.

## 3. Lifecycle integration and user documentation

- [x] 3.1 Add an end-to-end test with real SQLite files: restore a snapshot,
  populate the page table, verify the snapshot and directory are gone, quit
  normally, and verify the restored temporary session is cleaned up and is not
  offered on the next discovery. Verify the test fails against the old
  in-place restore.

- [x] 3.2 Add an end-to-end test for a crash after a successful restore: the
  next discovery offers the current temporary session once and does not offer
  the original snapshot. Verify the test uses the same discovery helper as
  startup.

- [x] 3.3 Update `README.md` with the restore-and-consume lifecycle, the
  sibling `scantpaper-XXXXXXXX.sdb` layout, manual cleanup after quitting, the
  Discard action, the non-blocking reservation and the corrected File menu
  route; update `changelog.md`. Verify the documented menu labels and cleanup
  behaviour match the implementation.

- [x] 3.4 Regenerate the translation template with
  `PYTHONPATH=src python3 dev/generate_pot.py`, seed new catalog entries as
  `#, fuzzy`, and run `PYTHONPATH=src python3 dev/check_po.py`. Verify it
  reports no catalog errors and the new strings are fuzzy.

## 4. Integration checks

- [x] 4.1 Run `pytest` and confirm every test passes, including the new
  discovery, restore, discard and lifecycle tests.

- [x] 4.2 Run `ruff format --check`, `ruff check` and `ty check .` with no
  diagnostics or new suppressions.

- [x] 4.3 Compare coverage with the baseline and confirm the number of
  uncovered and partially covered lines is the same or lower; only
  `TYPE_CHECKING` imports may remain newly uncovered.

## Workflow follow-up

- Archive the change after review and a green CI run.
