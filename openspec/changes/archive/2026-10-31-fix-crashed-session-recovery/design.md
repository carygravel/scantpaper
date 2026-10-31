# Design

## Context

See `proposal.md` — Why. The current pieces that shape the approach:

- A session is a directory `TMPDIR/scantpaper-XXXXXXXX/` plus a sibling
  database `TMPDIR/scantpaper-XXXXXXXX.sdb`.
- `BaseDocument.open_session()` removes the current scratch database and then
  opens the chosen file in place (`basedocument.py`). That is correct for a
  saved session, but crash recovery currently reuses it, so the snapshot
  becomes the working database and is never cleaned up.
- `DocThread._temp_db` records the scratch database created at startup.
  `db_is_temporary()` compares `_db` with `_temp_db`, so an in-place snapshot
  is treated as persistent.
- `SessionMixins._find_crashed_sessions()` tests a session by opening its
  `lockfile` and calling `fcntl.lockf(..., LOCK_EX)`, then discards the file
  handle. That call blocks while another instance holds the lock and does not
  reserve the snapshot after discovery.
- `File → Open crashed session` is a `SELECT_FOLDER` chooser even though
  `open_session()` requires a file.

## Goals / Non-Goals

**Goals:**

- Make a restored crash snapshot a temporary document again, so normal exit
  cleanup applies to it.
- Give the user an explicit way to remove a snapshot they do not want.
- Use one picker and one discovery path for startup and the File menu.
- Make lock probing non-blocking and hold the lock while a snapshot is listed
  or restored.
- Keep saved `.sdb` files on the existing in-place path.

**Non-Goals:**

- Changing the session database schema or `USER_VERSION`.
- Filtering empty snapshots out of the picker.
- Automatically deleting a snapshot that was not restored or discarded.
- Repointing the working database on Save As.
- Making restore cancellable.

## Decisions

### D1: Restore copies into the current scratch database

`BaseDocument.restore_session()` will ask `DocThread` to copy the snapshot
into `_temp_db`, then open that copy through the normal open/page-table chain.
The snapshot is never adopted as `_db`.

The copy uses SQLite's online backup API on the worker thread:

1. Validate that the snapshot exists and `PRAGMA application_id` matches.
2. Close the worker's existing database connections.
3. Copy the snapshot to `<scratch>.restore` so a failed copy never touches the
   current scratch database.
4. Remove stale `-wal`/`-shm` files for the scratch database.
5. Atomically replace the scratch database with the copy.
6. Open the scratch database through the existing `open()` validation and
   migration path.

Alternatives considered:

- **Open the snapshot in place and track it as temporary.** Smaller change, but
  it spreads a second temporary location across `_can_quit()`,
  `pages_saved()` and Save As, and it leaves the snapshot directory behind.
- **Move the snapshot into the scratch path.** Cheap on the same filesystem,
  but a crash between moving the main file and its WAL sidecars can lose the
  most recent committed pages.
- **Open the snapshot read-only and `VACUUM INTO` the scratch path.** Correct,
  but duplicates the backup/validation sequencing and gives less control over
  the destination file.

### D2: Consume the snapshot only after the page table is usable

Deletion happens after `page_number_table` succeeds, not immediately after the
database opens. The chain is:

```
restore request
  -> copy snapshot to scratch.restore
  -> replace scratch database
  -> open scratch database
  -> page_number_table
  -> populate document
  -> remove snapshot db, -wal, -shm and snapshot session directory
```

If any step before the final removal fails, the snapshot remains intact and
the error callback reports the failure. The scratch database copy may remain
on disk; it is the current temporary session and will be cleaned on the next
normal exit. A crash between a successful page table and removal can leave the
snapshot for one more offer; that is a duplicate recovery, never data loss.

The snapshot database is unlinked before its directory is removed, so a
directory removal failure cannot make the snapshot appear again.

### D3: Lock snapshots non-blockingly and keep the handles

Discovery will use `LOCK_EX | LOCK_NB`. A failed lock means another instance
is using the session, so the snapshot is skipped. Successful handles live on
the window until the picker action completes:

- Cancel: release every handle.
- Discard: delete the files, then release.
- Restore: keep the selected handle until the page table succeeds and the
  snapshot is consumed, then release.

For an orphaned `.sdb` without its session directory, use a sibling
`<db>.lock` file. The lock file itself is not the SQLite database, so this does
not conflict with SQLite's own locking. Stale lock files are harmless because
an unlocked file can be locked again; they are removed when the snapshot is
consumed or discarded.

Alternatives considered:

- **Keep the existing blocking `LOCK_EX`.** This can hang startup when another
  instance is running and does not reserve the snapshot after the picker is
  built.
- **Lock the `.sdb` file directly for orphans.** SQLite uses POSIX locks on its
  database file, so an application lock there could conflict with a restore.

### D4: One picker for startup and the File menu

Extract the discovery-and-dialog flow into a reusable method. Startup calls it
silently when the list is empty; **File → Open crashed session** calls it with
an explicit “no crashed sessions found” message. The dialog offers:

- **Restore**: restore the selected snapshot.
- **Discard**: ask for confirmation, then delete all selected snapshots.
- **Cancel**: close without changes.

The File menu action no longer constructs a file chooser, so it cannot pass a
directory to `open_session()`. The picker list uses multiple selection so
Discard can act on several snapshots at once.

Before replacing a non-empty current document from the File menu, the existing
unsaved-work question is asked. At startup the document is empty, so the
question is naturally skipped.

Alternatives considered:

- **Remove the File menu item** and rely on File → Open for `.sdb` files.
  Simpler, but it removes the only manual route to a snapshot whose startup
  dialog was dismissed.
- **Keep a file chooser for `.sdb` files.** That duplicates File → Open and
  would let a durable session file be consumed as if it were a crash snapshot.

### D5: Do not filter empty snapshots

The picker keeps a snapshot whose latest action has no pages. The latest action
is only the visible state; earlier actions may still hold the pages the user
wants to undo back to. The discard action is the explicit way to get rid of
such a snapshot.

Alternative considered: hide snapshots with zero pages in the latest action.
That would silently discard recoverable history and would require opening every
candidate database during startup.

### D6: Reuse the existing in-place open for saved sessions

`open_session()` keeps its current contract. Only `restore_session()` uses the
copy-then-open path. This keeps the `session-persistence` in-place requirement
unchanged and limits the new lifecycle to snapshots discovered by crash
recovery.

### D7: Progress and cancellation

The copy runs on the worker thread and shows the existing post-process progress
bar in pulse mode until the response arrives. Restore is not cancellable: it is
a bounded local copy with no external process, and a partial `<scratch>.restore`
file is deleted on failure. This matches the existing session Save As path.
A cancel button would add a second cancellation protocol for no user-visible
benefit.

## Risks / Trade-offs

- [A large session database makes restore slow] → The copy runs off the main
  thread and the progress bar shows activity; the snapshot remains intact until
  the copy and page table succeed.
- [A crash during restore leaves a `.restore` file or a duplicate snapshot] →
  Stale `.restore` files are removed on the next attempt; a duplicate snapshot
  is offered once more and can be discarded.
- [Discarding deletes user data] → The action requires explicit confirmation
  and only affects snapshots in the app-owned temporary directory.
- [Holding locks can make a snapshot unavailable after a picker is abandoned] →
  All lock handles are released in a `finally` path; process exit releases the
  OS locks even if the dialog is destroyed unexpectedly.
- [The File menu action replaces a document] → It asks the existing
  unsaved-work question before restoring; the startup path has an empty
  document.
- [Switching discovery to `LOCK_NB` changes behaviour for permission errors] →
  A lock that cannot be taken is skipped and logged, never treated as a crash.

## Migration Plan

No schema or on-disk format change. Existing crash snapshots are restored by
the new copy path and removed after a successful restore. Rolling back leaves
any remaining snapshots readable by the current in-place code.
