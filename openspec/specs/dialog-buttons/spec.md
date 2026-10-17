# dialog-buttons Specification

## Purpose
Dialog action buttons present readable, localised text labels with keyboard
mnemonics, never raw GTK stock IDs, so every dialog is understandable and
translatable.
## Requirements
### Requirement: Dialog buttons show localised text labels

Every dialog action button SHALL display a localised text label and SHALL NOT
display a GTK stock ID.

#### Scenario: Scan dialog dismiss button

- **WHEN** the scan dialog is shown
- **THEN** its dismiss button is labelled with the localised word for
  "Close", not with a GTK stock ID

#### Scenario: Apply and cancel dialog buttons

- **WHEN** a tool dialog (threshold, unsharp, crop, unpaper, OCR, …) is
  shown
- **THEN** its confirm button is labelled with the localised word for
  "Apply" or "OK", and its cancel button with the localised word for
  "Cancel"

#### Scenario: No stock IDs are displayed

- **WHEN** any dialog is shown
- **THEN** no button label starts with the GTK stock ID prefix `gtk-`

#### Scenario: Labels are translatable

- **WHEN** the user runs the application in a language whose catalog
  translates one of these labels
- **THEN** the button displays the translation

### Requirement: Dialog buttons keep keyboard mnemonics

Dialog action buttons SHALL keep a keyboard mnemonic, so a button can be
activated without a pointer.

#### Scenario: Mnemonic activates a button

- **WHEN** a dialog is open and the user presses the mnemonic key shown on
  one of its buttons
- **THEN** that button is activated

