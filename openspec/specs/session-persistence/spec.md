# session-persistence Specification

## Purpose
Define the lifecycle of session data: temporary storage for an unsaved
session, in-place editing of a session saved as a file and reopened, and what
counts as persisted work.
## Requirements
### Requirement: Reopened sessions are edited in place

Opening a session file SHALL make that file the working session database for
the document. Subsequent edits SHALL be persisted to that file without an
explicit save action. For a reopened session the temporary working copy made
during open SHALL NOT be the source of truth.

#### Scenario: Opening a session makes the file the working database

- **WHEN** the user opens a valid session file
- **THEN** the opened file SHALL become the document's working database
- **AND** subsequent edits SHALL be written to that file

#### Scenario: Edits survive exit without an explicit save

- **WHEN** the user opens a session, makes an edit, and exits without choosing
  Save
- **THEN** reopening the same file SHALL show the edit

#### Scenario: Save As writes a copy

- **WHEN** the user chooses Save As with a different filename
- **THEN** the session at that moment SHALL be written to the chosen file
- **AND** the document SHALL keep editing in its existing working database (the
  opened file, or the temporary session database of a never-saved document)

### Requirement: An in-place session is not offered as a crashed session

Opening a session file SHALL NOT leave a temporary snapshot of that session
that crash recovery could offer for restoration. The opened file is the source
of truth for the work.

#### Scenario: Crash after opening a session offers no stale snapshot

- **WHEN** the user opens a session file and continues editing
- **AND** the application later crashes
- **THEN** the next start SHALL NOT offer a temporary snapshot of that session
  for restoration
- **AND** the opened session file SHALL remain the persisted copy of the work

### Requirement: Unsaved session data lives only in temporary storage

An unsaved session's data SHALL reside in a temporary location. On a normal
exit the temporary session data SHALL be removed; after a crash it SHALL
survive so that it can be offered for restoration on the next start.

#### Scenario: Normal exit removes unsaved session data

- **WHEN** the application exits normally with an unsaved session
- **THEN** the temporary session data SHALL be removed

#### Scenario: Crash preserves unsaved session data

- **WHEN** the application crashes with an unsaved session
- **THEN** the temporary session data SHALL survive
- **AND** the next start SHALL offer to restore it

### Requirement: The unsaved-work warning reflects persisted work

Before quitting, or before clearing all pages, the application SHALL warn only
when the current work is not persisted. Work SHALL be considered persisted
while the working database is a session file the user opened or saved, and
after the pages have been written to an output file (including a session
file), until a page's content is edited again. A content edit SHALL return
the edited page to unpersisted. Work in a temporary document SHALL be
considered unpersisted until it is written to a file.

#### Scenario: Quitting an unsaved temporary document warns

- **WHEN** the document is temporary and no output has been written
- **AND** the user quits
- **THEN** the application SHALL warn that pages may be unsaved

#### Scenario: Quitting after saving the session does not warn

- **WHEN** the user saves the document as a session file and quits without
  further edits
- **THEN** no unsaved-pages warning SHALL be shown

#### Scenario: Quitting a reopened session after edits does not warn

- **WHEN** the user opens a session file, edits it, and quits
- **THEN** no unsaved-pages warning SHALL be shown

#### Scenario: Clearing a temporary document warns

- **WHEN** the document is temporary and no output has been written
- **AND** the user starts a new document
- **THEN** the application SHALL warn before clearing the pages

#### Scenario: Editing a saved page re-enables the warning

- **WHEN** the pages of a temporary document have been written to an output
  file and the user then edits a page's content
- **AND** the user quits
- **THEN** the application SHALL warn that pages may be unsaved

#### Scenario: Undoing an edit restores the saved state

- **WHEN** a page's content is edited, the edit is undone, and no other
  edit follows
- **THEN** the page SHALL be considered persisted exactly as it was
  before the edit

### Requirement: Opening a session restores its latest action

Opening a session SHALL restore the document to the latest action recorded in
the session. The latest action SHALL be used even when it contains no pages.
A session with no recorded actions SHALL open at the start of history, and
action state SHALL NOT carry over from a previously open document.

#### Scenario: A session with pages reopens at its latest action

- **WHEN** a session with pages is opened
- **THEN** its pages SHALL be shown in their saved order
- **AND** the restored action SHALL be the latest action recorded in the
  session

#### Scenario: An empty session reopens as an empty document

- **WHEN** a session with no pages and no recorded actions is opened
- **THEN** the document SHALL show no pages
- **AND** the document SHALL be at the start of its undo history

#### Scenario: A session whose latest action removed every page reopens empty

- **WHEN** a session whose latest recorded action removed every page is opened
- **THEN** the document SHALL show no pages
- **AND** pages present in an earlier recorded action SHALL NOT be shown

#### Scenario: A newly opened session starts its own history

- **WHEN** a session is open and the user opens a different session with no
  recorded actions
- **THEN** the second document SHALL be at the start of its own history
- **AND** the first session's actions SHALL NOT be available to it

### Requirement: A reopened session continues its undo history

After a session is opened, edits SHALL continue from the restored action. The
first edit SHALL record exactly one new action, and undo and redo availability
SHALL reflect the restored position.

#### Scenario: The first page after reopening an empty session is one undo step

- **WHEN** a page is added to a session reopened with no pages
- **THEN** the page SHALL be added successfully
- **AND** exactly one undo step SHALL be recorded
- **AND** undoing it SHALL return the document to empty

#### Scenario: Undo after reopening a cleared session restores its pages

- **WHEN** a session whose latest action removed every page is reopened
- **AND** the user triggers undo once
- **THEN** the pages removed by that action SHALL be restored

#### Scenario: A reopened empty session offers neither undo nor redo

- **WHEN** a session with no recorded actions is opened
- **THEN** undo SHALL NOT be available
- **AND** redo SHALL NOT be available

### Requirement: Restoring a crashed session consumes its snapshot

Restoring a crashed session SHALL copy its data into the document's current
temporary session and SHALL open that temporary database. The snapshot
database, its sidecars and its session directory SHALL be removed only after
the restored document has opened successfully. If the copy or open fails, the
snapshot SHALL remain intact and SHALL be offered again. Restored work SHALL be
treated as unsaved temporary work until it is written to a file.

#### Scenario: A successful restore consumes the snapshot

- **WHEN** the user restores a crashed snapshot
- **AND** the restored document opens successfully
- **THEN** the snapshot database, its sidecars and its session directory SHALL
  be removed
- **AND** the restored pages SHALL be shown
- **AND** the next start SHALL NOT offer that snapshot again

#### Scenario: A failed restore preserves the snapshot

- **WHEN** the user restores a crashed snapshot
- **AND** the snapshot cannot be copied or the restored database cannot be
  opened
- **THEN** the snapshot database, its sidecars and its session directory SHALL
  remain intact
- **AND** the next start SHALL offer it again

#### Scenario: Restored work is removed on a normal exit

- **WHEN** the user restores a crashed snapshot and quits normally without
  writing the work to a file
- **THEN** the temporary session containing the restored work SHALL be removed
- **AND** the next start SHALL NOT offer the restored work for recovery

#### Scenario: A crash after restoring offers the restored work once

- **WHEN** the user restores a crashed snapshot and the application crashes
  again before the work is written to a file
- **THEN** the next start SHALL offer the current temporary session, including
  the restored work
- **AND** the original snapshot SHALL NOT be offered separately

#### Scenario: Save As keeps restored work in the saved file

- **WHEN** the user restores a crashed snapshot and chooses Save As with a
  filename
- **THEN** the restored session SHALL be written to that file
- **AND** a normal quit SHALL remove the temporary session
- **AND** the saved file SHALL remain

### Requirement: Crashed snapshots can be discarded

The crashed-session picker SHALL let the user discard one or more listed
snapshots without restoring them. Discarding SHALL require confirmation and,
once confirmed, SHALL remove the selected snapshot database, its sidecars and
its session directory. A snapshot in use by a running instance SHALL NOT be
discarded.

#### Scenario: Discarding a selected snapshot removes it

- **WHEN** the user selects a crashed snapshot and chooses Discard
- **AND** confirms the discard
- **THEN** the snapshot database, its sidecars and its session directory SHALL
  be removed
- **AND** the next start SHALL NOT offer it again

#### Scenario: Cancelling a discard leaves the snapshot

- **WHEN** the user chooses Discard and cancels the confirmation
- **THEN** the snapshot SHALL remain unchanged
- **AND** it SHALL still be listed

#### Scenario: Discarding several snapshots removes each one

- **WHEN** the user selects several crashed snapshots and confirms Discard
- **THEN** every selected snapshot database, its sidecars and its session
  directory SHALL be removed

#### Scenario: A running session cannot be discarded

- **WHEN** a snapshot belongs to a session in use by another instance
- **THEN** it SHALL NOT be listed for discard

### Requirement: Crashed-session discovery and the picker are shared

Crashed-session discovery SHALL list the snapshot databases found in the
configured temporary directory that are not in use by a running instance. The
same picker SHALL be shown at startup and from **File → Open crashed session**,
and it SHALL offer Restore, Discard and Cancel. The File menu action SHALL NOT
use a folder chooser, and it SHALL report when no snapshots are found.

#### Scenario: Startup lists detected snapshots

- **WHEN** the application starts
- **AND** a crashed snapshot exists in the configured temporary directory
- **THEN** the picker SHALL list it

#### Scenario: The File menu shows the same picker

- **WHEN** the user chooses **File → Open crashed session**
- **THEN** the picker SHALL list the snapshots detected at that moment
- **AND** it SHALL offer Restore, Discard and Cancel

#### Scenario: The current session is not listed

- **WHEN** the picker is shown
- **AND** the current application's session database is in the temporary
  directory
- **THEN** the current session SHALL NOT be listed

#### Scenario: An orphaned snapshot is still listed

- **WHEN** a snapshot database exists without its session directory
- **THEN** the picker SHALL list it
- **AND** it SHALL be possible to restore or discard it

#### Scenario: No snapshots are found

- **WHEN** the user chooses **File → Open crashed session**
- **AND** no crashed snapshot exists
- **THEN** the application SHALL report that no crashed sessions were found
- **AND** no empty picker SHALL be left open

#### Scenario: Startup is silent when nothing is found

- **WHEN** the application starts
- **AND** no crashed snapshot exists
- **THEN** no picker SHALL be shown

### Requirement: Listed crashed snapshots are reserved for the picker

While the crashed-session picker is open, each listed snapshot SHALL be
reserved so that another instance does not list or restore it. A snapshot
already reserved by another instance SHALL NOT be listed. Reserving a snapshot
SHALL NOT block waiting for the other instance.

#### Scenario: Another instance skips a reserved snapshot

- **WHEN** a snapshot is reserved by an open picker
- **AND** another instance opens its picker
- **THEN** the other instance SHALL NOT list that snapshot

#### Scenario: Reservation does not block startup

- **WHEN** a snapshot is locked by another running instance
- **THEN** discovery SHALL skip it without waiting
- **AND** the application SHALL continue starting

#### Scenario: Reservation is released after the picker closes

- **WHEN** the picker is closed by Restore, Discard or Cancel
- **THEN** the reservations held by that picker SHALL be released

### Requirement: Empty crashed snapshots remain available

The picker SHALL list a crashed snapshot even when its latest recorded action
contains no pages. Restoring such a snapshot SHALL open an empty document, and
discarding it SHALL remove it.

#### Scenario: A cleared snapshot is listed

- **WHEN** a crashed snapshot's latest recorded action removed every page
- **THEN** the picker SHALL list it

#### Scenario: A cleared snapshot restores empty

- **WHEN** the user restores a crashed snapshot whose latest action removed
  every page
- **THEN** the document SHALL show no pages
- **AND** the snapshot SHALL be consumed

#### Scenario: A cleared snapshot can be discarded

- **WHEN** the user discards a crashed snapshot whose latest action removed
  every page
- **THEN** the snapshot SHALL be removed

