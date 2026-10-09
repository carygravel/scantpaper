## Why

Reopening a saved `.sdb` session already continues editing the file in place:
the file itself becomes the working database, so changes are written straight
back to it without an explicit save, and a crash leaves the original intact.
A user testing the recent session-overwrite fix confirmed this is preferable
to the alternative (editing a temporary copy, then requiring a save).

But the behaviour is unspecified rather than intended, and two things around
it are inconsistent:

- `open_session()` makes a temporary copy of the file it opens but never uses
  it as the live database. If the application crashes, that copy is offered
  for restoration even though it is frozen at open time, so restoring it
  discards the edits already written to the opened file.
- The application warns "Some pages have not been saved" on quit (and when
  clearing all pages) even when the session has been saved as a file or is
  being edited in place, because a session save does not mark its pages saved.

## What Changes

- Document the two session lifecycles in the README: an unsaved session lives
  in a temporary directory removed on exit, while a session saved as `.sdb`
  and reopened is edited in place.
- Add a `session-persistence` capability spec covering both lifecycles.
- Open a session file in place without leaving a stale temporary snapshot, so
  crash recovery never offers a session that is already persisted to a file.
- Make the unsaved-work warning reflect what is persisted: do not warn while
  the working database is a session file the user opened or saved, and treat a
  session save as persisting its pages.
- Add regression tests and a changelog entry.

## Capabilities

### New Capabilities

- `session-persistence`: the lifecycle of session data — temporary storage for
  unsaved sessions, in-place editing of saved and reopened sessions, and what
  counts as persisted work.

### Modified Capabilities

None.

## Impact

- `README.md` — the Sessions section is rewritten to describe both lifecycles.
- `changelog.md` — a bullet under the unreleased 3.0.22 section.
- `openspec/specs/session-persistence/spec.md` — new capability.
- `src/scantpaper/basedocument.py` — `open_session()` no longer snapshots the
  opened file; it discards the temporary scratch database instead.
- `src/scantpaper/docthread.py` — track whether the working database is the
  temporary scratch database, and use that for the saved-work check.
- `src/scantpaper/file_menu_mixins.py` — mark pages saved after a session save;
  remove the ignored `delete` keyword from the crash-restore call.
- Tests across `test_basedocument.py`, `test_docthread.py` and
  `test_file_menu_mixins.py`.
