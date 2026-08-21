## Purpose

Keeps the document state shown in the main window consistent with the document
state recorded by the background session store when the user starts a new file,
so that undo/redo history never resurrects pages cleared by "New File" except
by explicitly undoing that step.

## ADDED Requirements

### Requirement: New File clears the document through the session store
The "New File" action SHALL remove all pages by sending a delete-pages request
through the same message-passing path used for ordinary page deletion, so that
the frontend page list and the stored snapshot chain are updated by the same
operation. It SHALL NOT clear only the frontend list.

#### Scenario: Pages removed from both list and snapshot chain
- **WHEN** the document contains one or more pages and the user activates
  "New File" and confirms any unsaved-changes prompt
- **THEN** all pages are removed from the frontend page list
- **AND** the stored current-state snapshot contains no pages

#### Scenario: Thumbnails clear via the delete response
- **WHEN** the delete-pages request triggered by "New File" completes
- **THEN** the frontend removes the corresponding rows from its page list in
  response to the completion data, using the same callback mechanism as
  ordinary page deletion

### Requirement: Undo does not resurrect pages cleared by New File
After "New File", subsequent undo steps SHALL reflect only changes made after
the clear. Undoing an edit made to a page scanned after "New File" SHALL NOT
make pages that existed before the clear reappear.

#### Scenario: Regression for issue 74
- **WHEN** a page A is scanned, the document is saved, "New File" is activated,
  a page B is scanned, B is edited, and the user triggers a single undo
- **THEN** the edit to B is reverted
- **AND** page A is not present in the resulting page list

#### Scenario: Redo after undoing past the clear
- **WHEN** the user undoes back to or before the "New File" step and then
  redoes forward
- **THEN** redo replays the same sequence of states, including the cleared
  state, without duplicating pages

### Requirement: Undo can restore pages cleared by New File
The clear performed by "New File" SHALL be an ordinary undoable step: undoing
immediately after "New File" SHALL restore the pages that were present before
the clear, and redo SHALL clear them again.

#### Scenario: Undo immediately after New File
- **WHEN** the document contains pages and the user activates "New File", then
  triggers undo before any other document change
- **THEN** the pages present before the clear are restored

### Requirement: New File on an empty document is a no-op
When the document contains no pages, activating "New File" SHALL NOT send a
delete request and SHALL NOT create a new undo step.

#### Scenario: Empty document
- **WHEN** the page list is empty and the user activates "New File"
- **THEN** no delete-pages request is sent
- **AND** the set of undoable steps is unchanged

### Requirement: Unsaved-changes guard still applies
The "New File" action SHALL continue to prompt for confirmation when there are
unsaved pages, and SHALL proceed with the clear only if the user confirms.

#### Scenario: User cancels the unsaved-changes prompt
- **WHEN** there are unsaved pages and the user activates "New File" but
  cancels the confirmation dialog
- **THEN** no pages are deleted and the page list is unchanged

#### Scenario: View state resets after clear
- **WHEN** the clear triggered by "New File" completes
- **THEN** no page is displayed in the image view
- **AND** no text is shown on the text canvases
- **AND** no page is selected
