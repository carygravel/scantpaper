## ADDED Requirements

### Requirement: Page content edits are recorded as versioned undo steps

Every mutation of stored page content - the text layer, the annotations
layer, or the page resolution - SHALL record an undo step and SHALL be
written to a stored copy of the page belonging to that step, so that steps
which differ in that content never share one stored copy.

#### Scenario: Undo restores the previous text layer

- **WHEN** a page's text layer is edited and the user triggers undo once
- **THEN** the text layer read for that page SHALL be the one it had
  before the edit

#### Scenario: Redo re-applies the text layer edit

- **WHEN** a text layer edit is undone and the user triggers redo once
- **THEN** the text layer read for that page SHALL be the edited one

#### Scenario: An edit does not change what an earlier step restores

- **WHEN** a page's text layer is edited and the user triggers undo once,
  and then triggers undo again
- **THEN** both undos SHALL leave the text layer at the same pre-edit
  value

#### Scenario: Annotation edits undo like text layer edits

- **WHEN** a page's annotation layer is edited and the user triggers undo
  once
- **THEN** the annotations read for that page SHALL be the ones it had
  before the edit

#### Scenario: A resolution change is undoable

- **WHEN** a page's resolution is changed and the user triggers undo once
- **THEN** the resolution read for that page SHALL be the one it had
  before the change

#### Scenario: Editing content never duplicates the stored image

- **WHEN** a page's text layer, annotation layer, or resolution is edited
- **THEN** the stored image for that page SHALL remain unchanged

### Requirement: Undo restores content, not only page structure

Undo and redo SHALL restore the stored content of pages, not merely the
set and order of pages.

#### Scenario: Undo returns earlier content with the page order

- **WHEN** a page's content is edited and the user triggers undo once
- **THEN** the undo snapshot SHALL contain the same pages in the same
  order
- **AND** reading a page's edited content after the undo SHALL return the
  pre-edit value

#### Scenario: Redo returns later content with the page order

- **WHEN** an edit is undone and the user triggers redo once
- **THEN** the redo snapshot SHALL contain the same pages in the same
  order
- **AND** reading a page's edited content after the redo SHALL return the
  post-edit value