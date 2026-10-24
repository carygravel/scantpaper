# scan-device-selection Specification

## Purpose

Defines how the scan dialog presents the device selector: its placement as
the first control in the dialog, so the user chooses the scanning source
before adjusting scan options.

## Requirements

### Requirement: Device selector is the first scan dialog control

The scan dialog SHALL present the Device selector (its label and dropdown)
as the first control of the dialog's content area, above the scan-options
notebook.

#### Scenario: Opening the scan dialog

- **WHEN** the scan dialog is shown
- **THEN** the Device selector is the first control at the top of the
  dialog's content area, above the scan-options notebook

#### Scenario: Refreshing the device list keeps the selector first

- **WHEN** the device list is fetched or rescanned from the selector
- **THEN** the Device selector remains the first control of the dialog's
  content area while the list is populated
