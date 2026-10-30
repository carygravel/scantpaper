# Spec Delta

## Purpose

Defines how the scan dialog is constructed from saved settings, so it opens
with the postprocessing controls in the state those settings describe.

## ADDED Requirements

### Requirement: The scan dialog opens with saved postprocessing settings

When the scan dialog is opened, it SHALL be built successfully from every
valid saved postprocessing setting, including alternate rotation, image
clean-up and the user-defined tool being enabled or disabled, and it SHALL
show the controls in the saved state.

#### Scenario: Alternate rotation saved as enabled

- **WHEN** the saved settings enable alternate rotation and the user opens
  the scan dialog
- **THEN** the dialog opens
- **AND** the alternate-rotation control is active

#### Scenario: Image clean-up saved as enabled

- **WHEN** the saved settings enable image clean-up and the user opens the
  scan dialog
- **THEN** the dialog opens
- **AND** the clean-up control is active

#### Scenario: The clean-up tool is unavailable

- **WHEN** the clean-up tool is not installed and the user opens the scan
  dialog
- **THEN** the dialog opens
- **AND** the clean-up control is insensitive and inactive

#### Scenario: User-defined tool saved as enabled

- **WHEN** the saved settings enable the user-defined tool and the user
  opens the scan dialog
- **THEN** the dialog opens
- **AND** the user-defined-tool control is active

#### Scenario: No user-defined tools configured

- **WHEN** the saved user-defined-tool list is empty and the user opens the
  scan dialog
- **THEN** the dialog opens
- **AND** the user-defined-tool control is insensitive and inactive

### Requirement: Empty user-defined-tool list keeps the scan dialog usable

When the user applies Preferences with an empty user-defined-tool list while
the scan dialog exists, the scan dialog SHALL remain usable and its
user-defined-tool control SHALL become insensitive and inactive.

#### Scenario: Removing the last tool while the scan dialog exists

- **WHEN** the user removes the last user-defined tool, applies Preferences,
  and the scan dialog was already built
- **THEN** the Preferences dialog applies without error
- **AND** the scan dialog's user-defined-tool control is insensitive and
  inactive
