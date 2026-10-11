# ocr-recognition

## ADDED Requirements

### Requirement: Clearing the OCR text layer is persisted and undoable
When the user clears the OCR text layer of one or more selected pages, the
clear SHALL be dispatched through the worker thread so that the removal is
written to the stored session, SHALL be recorded as an undoable document
action, and SHALL NOT modify any stored page image. The page SHALL keep its
existing image id and the stored image bytes SHALL remain unchanged.

#### Scenario: Clearing a single page's text layer
- **WHEN** the user selects a single page that has an OCR text layer and
  activates Clear OCR
- **THEN** the page's text layer is removed from the stored session
- **AND** the page's stored image id and image bytes are unchanged

#### Scenario: Undo restores a cleared text layer
- **WHEN** the user clears the OCR text layer of a page and then triggers
  undo once
- **THEN** the page's text layer returns to its pre-clear state
- **AND** the page's stored image is unchanged

#### Scenario: Redo removes the text layer again
- **WHEN** the user undoes a clear-OCR action and then triggers redo once
- **THEN** the page's text layer is removed again

#### Scenario: Clearing multiple selected pages is one undo step
- **WHEN** the user selects N pages and clears their OCR text layers in a
  single action
- **THEN** all N text layers are removed
- **AND** the action consumes exactly one undo step, not one step per page
