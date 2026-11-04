# Spec Delta

## ADDED Requirements

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
