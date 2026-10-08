## Purpose

Define how the save flow behaves when the chosen destination file already
exists: the user must be able to confirm or reject the overwrite, a confirmed
overwrite must actually replace the old file without ever destroying it
prematurely, and a failed save must be reported instead of vanishing.

## ADDED Requirements

### Requirement: Saving to an existing file asks for confirmation

When the user confirms a save destination whose file already exists, the
system SHALL ask the user to confirm overwriting before writing anything, for
every output type offered by the Save flow (session, PDF, DjVu, TIFF, text,
hOCR, Postscript). This SHALL also apply when the extension was appended
automatically to the name the user typed.

#### Scenario: Session save over an existing session file prompts

- **WHEN** the user confirms a session (`.sdb`) destination that already
  exists
- **THEN** an overwrite confirmation is shown before any writing happens

#### Scenario: Declining the overwrite leaves everything untouched

- **WHEN** the user declines the overwrite confirmation
- **THEN** the existing file is left unmodified
- **AND** no save is performed
- **AND** the file chooser stays open so the user can pick another name

#### Scenario: Non-PDF output prompts like PDF does

- **WHEN** the user confirms an existing destination for TIFF, text, hOCR,
  Postscript or DjVu output
- **THEN** an overwrite confirmation is shown, just as for PDF output

#### Scenario: Name typed without extension still prompts

- **WHEN** the user types a name without an extension, the suffixed file
  already exists, and the flow retries with the suffixed name
- **THEN** the overwrite confirmation is shown before any writing happens

### Requirement: A confirmed session save replaces the destination file

Once the user has confirmed an overwrite, saving a session SHALL replace the
contents of the existing destination file with the current session, and SHALL
succeed for any destination path the file chooser can select.

#### Scenario: Confirmed overwrite completes

- **WHEN** the user confirms overwriting an existing session file
- **THEN** the save completes and the destination file contains the current
  session database

#### Scenario: Failed save preserves the previous file

- **WHEN** writing the new session file fails part-way through
- **THEN** the previous destination file remains intact and readable

#### Scenario: Destination path contains quoting characters

- **WHEN** the destination path contains a single quote or other characters
  significant to SQL
- **THEN** the save succeeds

### Requirement: Session save failures are reported to the user

A failure while saving a session SHALL be surfaced to the user as an error
message rather than escaping as an unhandled exception, and the save dialog
SHALL be dismissed afterwards either way.

#### Scenario: Save fails with an error

- **WHEN** the session save raises an error after the user confirmed the
  destination
- **THEN** an error message dialog is shown describing the failure
- **AND** the application stays usable (no unhandled exception in the
  background)
- **AND** the file chooser dialog is dismissed

#### Scenario: Save succeeds

- **WHEN** the session save completes without error
- **THEN** the file chooser dialog is dismissed as it is today
