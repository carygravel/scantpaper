## Purpose

Lets operations that are applied to several pages at once be reverted as a
single undoable unit rather than one step per page.

## ADDED Requirements

### Requirement: Multi-page operations form a single undo step
When a page operation is applied to more than one page in a single user
action (for example rotating a selection of pages or cropping a page range),
the whole action SHALL be recorded as ONE undoable step. Undoing that step
SHALL revert every affected page, and redoing it SHALL re-apply the
operation to every affected page.

#### Scenario: Undo reverts the entire multi-page operation
- **WHEN** the user applies an operation to N selected pages and then
  triggers undo once
- **THEN** all N pages SHALL be restored to their pre-operation state

#### Scenario: Single undo press reverts all pages
- **WHEN** the user applies a multi-page operation and inspects the undo
  history
- **THEN** the operation SHALL consume exactly one undo step, not one step
  per page

#### Scenario: Redo re-applies the whole operation
- **WHEN** the user undoes a multi-page operation and then triggers redo
  once
- **THEN** the operation SHALL be re-applied to all N affected pages
