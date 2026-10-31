# Proposal

## Why

A crashed session that is restored from the startup picker is opened in place
and never consumed. Normal quit deletes only the new startup session, so the
same `/tmp/scantpaper-XXXXXXXX.sdb` is offered again on every start, even after
its pages have been deleted. The picker also has no way to discard an unwanted
snapshot, and **File → Open crashed session** opens a folder chooser that cannot
select the `.sdb` file it is meant to open.

## What Changes

- Restore a crashed snapshot into the document's current temporary session
  instead of opening the snapshot in place. The snapshot, its `-wal`/`-shm`
  sidecars and its session directory are removed only after the restored
  document has opened successfully; a failed restore leaves the snapshot
  intact.
- Treat restored work as an ordinary unsaved temporary document. A normal exit
  removes it, so a restored snapshot cannot be offered again from the same
  location.
- Add a **Discard** action to the crashed-session picker, with confirmation,
  that deletes selected snapshots and their session directories. Discarding is
  the explicit way to remove a snapshot without restoring it.
- Keep listing empty crashed sessions. A cleared snapshot may still hold
  recoverable undo history, so the picker does not hide it; the user discards
  it instead.
- Reserve snapshots listed in the picker for the lifetime of the dialog so a
  second instance cannot offer or restore the same snapshot concurrently.
- Replace the broken **File → Open crashed session** folder chooser with the
  same picker used at startup, so both entry points list detected snapshots
  and offer Restore, Discard and Cancel.
- Correct the stale `async-open-session` contract: a normal session open is
  in place; only crash recovery copies a snapshot into the current temporary
  database.
- Update the README, changelog and translation catalog for the new behaviour
  and strings.

Not in scope: saved `.sdb` files opened through **File → Open** keep their
in-place editing semantics, and the session database schema does not change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `session-persistence`: restoring a snapshot consumes it into temporary
  storage; snapshots can be discarded; discovery and the picker are shared by
  startup and the File menu; listed snapshots are reserved while the picker is
  open.
- `async-open-session`: the normal open contract is corrected to in-place
  opening, and crash restore gains its own asynchronous copy-then-open chain
  with failure recovery.

## Impact

- `src/scantpaper/session_mixins.py`: discovery, locking, picker buttons and
  discard/restore dispatch.
- `src/scantpaper/file_menu_mixins.py`: **File → Open crashed session** uses
  the shared picker; quit cleanup remains scoped to the current temporary
  session.
- `src/scantpaper/basedocument.py` and `src/scantpaper/docthread.py`: a crash
  restore request that copies the snapshot into the current scratch database
  on the worker thread, then opens it.
- `src/scantpaper/app_window.py`: startup keeps calling the shared picker.
- `src/scantpaper/tests/`: session discovery, discard, restore success/failure,
  lock reservation, in-place open regression, menu and cleanup tests.
- `README.md`, `changelog.md` and `po/scantpaper/*.po` / the generated
  template.
