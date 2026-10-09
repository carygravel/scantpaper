## Context

See `proposal.md` for motivation. The relevant current state:

- `open_session()` copies the chosen file to the temporary session location
  and then opens the chosen path itself as the working database
  (`basedocument.py:649` copy, `basedocument.py:687` open).
- `DocThread.open()` adopts the path it is given (`docthread.py:254`), so all
  later writes go to the opened file.
- The temporary copy is never re-opened while editing. It is deleted on exit
  (`file_menu_mixins.py:980`) and is only consulted by crash recovery
  (`session_mixins.py:99`), where it appears as a restorable crashed session.
- `DocThread.pages_saved()` queries the per-page `saved` flag
  (`docthread.py:981`). Edits clear the flag (`docthread.py:1172` and
  following). A session save (`basedocument.py:626`) never sets it, so
  `_pages_saved()` (`file_menu_mixins.py:1021`) can warn even when the session
  is current.

The copy-then-open-original pattern dates from the first session
implementation and predates the async rewrite, so the in-place behaviour is
long-standing but has never been specified.

## Goals / Non-Goals

**Goals:**

- Make "a reopened `.sdb` is edited in place" an explicit, tested contract.
- Stop crash recovery from offering a stale snapshot of an in-place session.
- Make the unsaved-work warning agree with what is actually persisted.
- Make the README describe both lifecycles accurately.

**Non-Goals:**

- Changing how unsaved (temporary) sessions are recovered.
- Making Save As repoint the working database to the newly saved file (see
  Open Questions).
- Reworking the per-page `saved` flag itself.

## Decisions

### D1: Bless in-place editing rather than restore the temp-copy model

Treat the observed behaviour as intended. Alternative considered: open the
temporary copy so edits never touch the user's file until an explicit Save.
That restores the current README's mental model but removes the convenience
the user relies on, and it introduces a loss window where edits live only in
temp storage. In-place editing keeps the file itself as the single source of
truth.

### D2: Capture the contract in a new `session-persistence` capability

The contract spans temporary storage, in-place editing, crash recovery and
the saved-work warning, so it does not belong in `async-open-session`, which
is about the asynchronous open mechanics. One capability describes the whole
session lifecycle.

### D3: Discard the temporary scratch database instead of snapshotting

`open_session()` will remove the temporary scratch database (and its `-wal`
and `-shm` sidecars) after `thread.close()` and before opening the chosen
file, rather than copying the chosen file onto it. The opened file is then
the only copy of the work, so crash recovery cannot offer a stale snapshot.

Alternatives considered:

- **Keep the snapshot but tag it so crash recovery skips it.** More state,
  still leaves dead bytes and a misleading file on disk.
- **Keep the snapshot and make it the live database.** That is D1's rejected
  temp-copy model.

Guard: the current `shutil.copy` also acts as a readability check and reports
"Unable to read" for a missing file. Since `sqlite3.connect()` would happily
create an empty file at a bad path, `open_session()` must confirm the chosen
path exists before discarding the scratch database, preserving today's error
behaviour.

### D4: Track whether the working database is the temporary one

`DocThread` will remember the path of the scratch database it was created
with, and expose whether the current working database is that scratch
database. `pages_saved()` returns `True` when it is not: work in a persistent
database is written to that file as it happens, so it is always persisted.

Alternatives considered:

- **Mark every page saved when a session is opened.** Edits clear the flag, so
  later edits would falsely look unsaved again for an in-place session.
- **Have edits on a persistent database re-mark pages saved.** Spreads the
  concern across every edit handler.

### D5: Mark pages saved when a session is saved

The `sdb` branch of the save flow will mark the document's pages saved after
the session is written, so a session saved from a temporary document is
treated as persisted. Later edits clear the flag again through the normal edit
handlers, so the warning returns only when the saved file really is behind.

### D6: Remove the ignored `delete` keyword

The crash-restore call passes `delete=False` (`file_menu_mixins.py:301`) which
`open_session()` ignores. Since the change already touches this path, drop the
dead keyword rather than leave it implying behaviour that does not exist.

## Risks / Trade-offs

- [Removing the snapshot means a crash during an in-place session relies only
  on the opened file] → SQLite's own WAL recovery covers partial writes, the
  file is the source of truth, and genuine unsaved sessions are still
  recovered; a crash cannot lose work that was already written to the opened
  file.
- [`pages_saved()` now reports a persistent session as saved, so the "New
  document" warning is suppressed for in-place sessions too] → New is an
  explicit, undoable action and the data is already in the opened file; the
  trade-off is documented in the README.
- [Save As from a temporary document keeps editing the temporary database, so
  edits made after Save As are not in the saved file] → the per-page flag
  still catches those later edits and the warning returns; recorded as an open
  question below.
- [Changing `open_session()`'s error path could lose the "Unable to read"
  dialog] → D3 guards by checking the path exists first.

## Open Questions

- Should Save As repoint the working database to the newly saved file, so the
  document becomes an in-place session on the new file? That would make Save
  As behave like a typical editor but is a larger behaviour change; deferred.
