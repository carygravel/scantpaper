# Spec Delta

## ADDED Requirements

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
