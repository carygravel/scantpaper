# Spec Delta

## MODIFIED Requirements

### Requirement: Saving to an existing file asks for confirmation

When the user confirms a save destination whose file already exists, the
file chooser SHALL ask the user to confirm overwriting before any writing
happens, for every output type offered by the Save flow (session, PDF, DjVu,
TIFF, text, hOCR, Postscript). This SHALL also apply when the extension was
appended automatically to the name the user typed.

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
