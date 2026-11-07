# Spec Delta

## Purpose

Defines how keyboard shortcuts are scoped to the focused control, so text entry
keeps its standard editing keys while page and view actions remain available
everywhere else.

## ADDED Requirements

### Requirement: Standard editing shortcuts stay with the focused text control

When a text control has focus, the standard editing shortcuts SHALL act on that
control and SHALL NOT trigger the corresponding page action.

#### Scenario: Cutting text does not cut pages

- **WHEN** a text control has focus with selected text and the user presses
  Ctrl+X
- **THEN** the selected text SHALL be removed from the control
- **AND** the selected pages SHALL remain in the document

#### Scenario: Copying and pasting text does not copy or paste pages

- **WHEN** a text control has focus and the user copies text with Ctrl+C and
  pastes it with Ctrl+V
- **THEN** the copied text SHALL be inserted into the control
- **AND** no page SHALL be copied to or pasted from the page clipboard

#### Scenario: Selecting all applies to the text

- **WHEN** a text control has focus and the user presses Ctrl+A
- **THEN** all text in the control SHALL be selected
- **AND** the page selection SHALL be unchanged

#### Scenario: Undo and redo apply to the text

- **WHEN** a text control has focus and the user presses Ctrl+Z or
  Ctrl+Shift+Z
- **THEN** the text edit SHALL be undone or redone
- **AND** the page undo history SHALL be unchanged

### Requirement: Printable zoom keys type in a text control

When a text control has focus, the `+` and `-` keys SHALL insert those
characters and SHALL NOT change the image zoom.

#### Scenario: Typing a minus sign

- **WHEN** a text control has focus and the user types `-12.5`
- **THEN** the control SHALL contain `-12.5`
- **AND** the image zoom SHALL be unchanged

#### Scenario: Typing a plus sign

- **WHEN** a text control has focus and the user types `+5`
- **THEN** the control SHALL contain `+5`
- **AND** the image zoom SHALL be unchanged

### Requirement: Window shortcuts still act outside text controls

When focus is not in a text control, the affected keys SHALL continue to
perform their page and view actions.

#### Scenario: Page clipboard shortcuts outside a text control

- **WHEN** focus is outside a text control and a page is selected
- **THEN** Ctrl+X, Ctrl+C and Ctrl+V SHALL cut, copy and paste pages as before

#### Scenario: Select all outside a text control

- **WHEN** focus is outside a text control and the user presses Ctrl+A
- **THEN** all pages SHALL be selected

#### Scenario: Undo and redo outside a text control

- **WHEN** focus is outside a text control and the user presses Ctrl+Z or
  Ctrl+Shift+Z
- **THEN** the page undo history SHALL be undone or redone

#### Scenario: Key zoom outside a text control

- **WHEN** focus is outside a text control and the user presses `+` or `-`
- **THEN** the image view SHALL zoom in or out

### Requirement: Menu and toolbar page actions remain reachable while editing

The page actions whose shortcuts are scoped to non-text focus SHALL remain
available from their menu items and toolbar controls while a text control has
focus.

#### Scenario: Activating a page action from the menu while editing text

- **WHEN** a text control has focus and the user activates Paste from the Edit
  menu with page data on the page clipboard
- **THEN** the page data SHALL be pasted into the document

### Requirement: Delete only deletes pages outside text controls

Plain Delete SHALL delete selected pages only when focus is outside a text
control. Modified Delete presses SHALL NOT be treated as a page delete.

#### Scenario: Delete in a text control edits the text

- **WHEN** a text control has focus and the user presses Delete
- **THEN** the character after the cursor SHALL be deleted
- **AND** no page SHALL be deleted

#### Scenario: Plain Delete outside a text control deletes pages

- **WHEN** focus is outside a text control, pages are selected, and the user
  presses Delete
- **THEN** the selected pages SHALL be deleted

#### Scenario: Modified Delete does not delete pages

- **WHEN** focus is outside a text control and the user presses Shift+Delete,
  Ctrl+Delete, or Alt+Delete
- **THEN** no page SHALL be deleted

### Requirement: Mouse-wheel zoom remains available while editing text

When the pointer is over the image view, the mouse wheel SHALL zoom that view
regardless of which widget has keyboard focus.

#### Scenario: Wheel zoom while a text control has focus

- **WHEN** a text control has focus and the pointer is over the image view
- **AND** the user turns the mouse wheel
- **THEN** the image view SHALL zoom in or out
