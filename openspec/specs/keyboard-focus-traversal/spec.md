# keyboard-focus-traversal Specification

## Purpose
Keeps every dialog and editing control fully operable from the keyboard, so a
user can move focus out of a text view with Tab and reach a dialog's action
buttons without using a pointer.

## Requirements

### Requirement: Text views release the Tab key

A text view used for typing in a dialog or as an editing control SHALL let the
Tab key move focus to the next widget, and SHALL NOT insert a tab character.

#### Scenario: Advanced OCR parameters field

- **WHEN** the OCR dialog is open and the user edits the "Advanced Tesseract
  engine parameters" field
- **THEN** pressing Tab moves focus out of the field to the next control
- **AND** no tab character is inserted into the field

#### Scenario: Reaching the OCR confirm button by keyboard

- **WHEN** keyboard focus is in the OCR advanced parameters field
- **THEN** the user can reach the OK button using the Tab key alone

#### Scenario: Text-layer editing control

- **WHEN** the text-layer editing text view has focus
- **THEN** pressing Tab moves focus to the next control
- **AND** no tab character is inserted

#### Scenario: Control-Tab still moves focus

- **WHEN** keyboard focus is in a text view that accepts typed input
- **THEN** pressing Ctrl+Tab moves focus to the next widget
- **AND** pressing Ctrl+Shift+Tab moves focus to the previous widget

### Requirement: The parameter list is operable from the keyboard

Opening the engine parameter list SHALL place keyboard focus in its filter
entry. The arrow keys SHALL move the list selection and the Enter key SHALL
activate the insert action for the selected entry. Closing the list SHALL
return focus to the advanced parameters field.

#### Scenario: Focus starts in the filter

- **WHEN** the engine parameter list opens
- **THEN** keyboard focus is in the filter entry

#### Scenario: Arrow keys move the selection

- **WHEN** the list has focus and the user presses the Down or Up arrow key
- **THEN** the selection moves to the next or previous entry

#### Scenario: Enter inserts the selected entry

- **WHEN** an insertable entry is selected and the user presses Enter
- **THEN** that entry is inserted and the list closes

#### Scenario: Closing the list returns focus

- **WHEN** the engine parameter list closes, with or without an insertion
- **THEN** keyboard focus is in the advanced parameters field
