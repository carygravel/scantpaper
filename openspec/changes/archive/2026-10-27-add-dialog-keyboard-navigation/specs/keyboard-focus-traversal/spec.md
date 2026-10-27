# Spec Delta

## Purpose

Keeps every dialog and editing control fully operable from the keyboard, so a
user can move focus out of a text view with Tab and reach a dialog's action
buttons without using a pointer.

## ADDED Requirements

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
