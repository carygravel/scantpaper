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

