# Spec Delta

## Purpose

Named, reusable sets of scan options that a user can create from the current
settings and apply again in a later session, so a recurring document type does
not have to be reconfigured each time.

## ADDED Requirements

### Requirement: Current scan options can be saved as a named profile

The scan dialog SHALL let the user save the current scan options under a name
and SHALL add that name to the profile selector once the profile is stored.

#### Scenario: Save opens the naming dialog

- **WHEN** the user activates Save in the Scan profiles frame
- **THEN** a dialog asking for the profile name is shown
- **AND** no error is reported and the scan dialog stays open

#### Scenario: Saving a new profile

- **WHEN** the user enters a non-empty name that is not already in use and
  confirms
- **THEN** the current scan options are stored under that name
- **AND** the name appears in the profile selector

#### Scenario: The saved profile holds the current options

- **WHEN** the user saves a profile and later selects it
- **THEN** the scan options that were current when it was saved are applied

### Requirement: A profile name is required

The naming dialog SHALL NOT create a profile from an empty or whitespace-only
name.

#### Scenario: Confirming an empty name

- **WHEN** the user confirms the naming dialog with an empty or whitespace-only
  name
- **THEN** no profile is created
- **AND** the naming dialog remains open for another attempt

#### Scenario: Cancelling the naming dialog

- **WHEN** the user cancels the naming dialog
- **THEN** no profile is created and the scan options are unchanged

### Requirement: Overwriting an existing profile needs confirmation

When the supplied name already exists, the scan dialog SHALL ask for
confirmation before replacing the stored profile.

#### Scenario: Confirming an overwrite

- **WHEN** the user enters the name of an existing profile and confirms the
  overwrite
- **THEN** the stored profile is replaced with the current scan options
- **AND** the profile selector still contains one entry with that name

#### Scenario: Cancelling an overwrite

- **WHEN** the user enters the name of an existing profile and cancels the
  overwrite
- **THEN** the stored profile is unchanged

### Requirement: Saved profiles persist across sessions

A profile saved during a session SHALL be available after the application is
closed normally and started again.

#### Scenario: Profile survives a restart

- **WHEN** the user saves a profile and closes the application normally
- **THEN** the profile is listed in the profile selector on the next start
