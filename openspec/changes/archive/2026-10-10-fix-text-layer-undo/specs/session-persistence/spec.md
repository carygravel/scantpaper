## MODIFIED Requirements

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