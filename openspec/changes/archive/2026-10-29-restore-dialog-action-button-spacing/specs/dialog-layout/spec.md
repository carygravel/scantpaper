# Spec Delta

## ADDED Requirements

### Requirement: Dialog action buttons are inset from the window edge

The action area of a dialog that presents separate action buttons SHALL be
inset from the dialog's edges by a non-zero, consistent margin, so the buttons
do not touch the window border. Where the dialog's content is inset, the
action area SHALL use the same inset.

#### Scenario: A tool or scan dialog's action buttons are inset

- **WHEN** a dialog opened from the Tools menu, or the scan dialog, is shown
- **THEN** its action buttons have a non-zero margin on all four sides

#### Scenario: A file chooser's action buttons are inset

- **WHEN** an open, save or import file chooser is shown
- **THEN** its action buttons have a non-zero margin on all four sides

#### Scenario: Action buttons line up with the content

- **WHEN** a dialog with an inset content area is shown
- **THEN** the action area uses the same inset value as the content area

### Requirement: Dialog action buttons are spaced apart

Consecutive action buttons in a dialog that presents separate action buttons
SHALL be separated by a consistent, non-zero spacing, so the buttons do not
touch each other.

#### Scenario: Apply and Cancel do not touch

- **WHEN** a tool dialog with Apply or OK and Cancel buttons is shown
- **THEN** the gap between the buttons is a non-zero, consistent spacing

#### Scenario: File chooser buttons do not touch

- **WHEN** a file chooser with Cancel and Open or Save buttons is shown
- **THEN** the gap between the buttons is a non-zero, consistent spacing

### Requirement: A joined message-dialog bar stays joined

A dialog whose action buttons are presented as a single joined bar SHALL keep
that presentation, with no added gap between the buttons and no added inset
around the bar.

#### Scenario: Warning, error and info dialogs keep a joined bar

- **WHEN** a warning, error or info message dialog is shown
- **THEN** its action buttons remain adjacent and joined to the dialog edge

#### Scenario: Joined buttons do not gain spacing

- **WHEN** a message dialog is shown
- **THEN** the spacing between its action buttons remains zero
