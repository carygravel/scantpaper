# Spec Delta

## ADDED Requirements

### Requirement: Focusing a slice gives the editing control keyboard focus

When the layer editor focuses a slice, its text control SHALL take keyboard
focus and SHALL select the slice's current text, so standard text-editing keys
act on the slice rather than on the page.

#### Scenario: Clicking a slice focuses and selects its text

- **WHEN** the user clicks a text slice on the page
- **THEN** the text control SHALL take keyboard focus
- **AND** the slice's text SHALL be selected
- **AND** pressing Delete SHALL clear the selected text from the control
- **AND** the page SHALL remain in the document

#### Scenario: Navigation focuses and selects the next slice

- **WHEN** the user activates the first, previous, next, or last navigation
  control
- **THEN** the text control SHALL take keyboard focus
- **AND** the newly focused slice's text SHALL be selected

#### Scenario: Adding or duplicating focuses the new slice

- **WHEN** the user adds or duplicates a slice
- **THEN** the text control SHALL take keyboard focus
- **AND** the new slice's text SHALL be selected

#### Scenario: Accepting a correction focuses the successor

- **WHEN** the user accepts a correction and the editor moves to another slice
- **THEN** the text control SHALL take keyboard focus
- **AND** the successor's text SHALL be selected

#### Scenario: Typing replaces the selected OCR text

- **WHEN** a slice is focused and its text is selected
- **AND** the user types replacement text
- **THEN** the typed text SHALL replace the selected text in the control

#### Scenario: No focused slice does not steal focus

- **WHEN** the editor has no slice focused
- **THEN** the text control SHALL NOT take keyboard focus

#### Scenario: Annotation slices follow the same rule

- **WHEN** the user clicks an annotation note
- **THEN** the annotation text control SHALL take keyboard focus
- **AND** the note's text SHALL be selected
