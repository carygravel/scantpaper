## MODIFIED Requirements

### Requirement: Rescue valid settings when the config file fails to parse

When `scantpaperrc` cannot be parsed as JSON, the system SHALL salvage as many
recognised settings as possible instead of resetting the entire configuration to
defaults. Settings that are present and correctly typed SHALL be preserved and
put into effect. The unreadable file SHALL be backed up to `scantpaperrc.old`
before the rescued settings are used.

#### Scenario: Config file contains a single bad line

- **WHEN** the user starts the application and the config file fails to parse
  as JSON, but otherwise contains recognisable keys such as
  `"rotate facing": 90` and `"rotate reverse": 270`
- **THEN** the application starts with those values in effect
- **AND** the unreadable file is preserved as `scantpaperrc.old`

#### Scenario: Notifying the user of a failed parse

- **WHEN** the config file fails to parse as JSON and settings are rescued or
  defaulted
- **THEN** the user is shown a message that the settings file could not be read
  in full, which settings were kept, and that a backup was made
- **AND** the notification is also written to the log

### Requirement: Keep recognised settings with wrong value types

When the config file parses but contains a value of an unexpected type for a
recognised key (e.g. a string where an integer is expected), the system SHALL
normalise the value to a usable form when one exists, otherwise preserve the
raw setting for inspection rather than silently replacing it with the default.

A lossless conversion SHALL be written to the log and SHALL NOT be shown to the
user in the message dialog. Only a value that cannot be made usable SHALL
produce a user-visible warning; that warning SHALL also be written to the log.

#### Scenario: String value where an integer is expected

- **WHEN** the config contains `"rotate facing": "270"` (a string instead of an
  integer)
- **THEN** the rotation setting is still applied as 270 degrees
- **AND** the conversion is written to the log
- **AND** no message dialog is shown for the conversion

#### Scenario: Unusable value kept raw and flagged

- **WHEN** the config contains a value that cannot be normalised to its
  expected type (e.g. `"thumb panel": "garbage"`)
- **THEN** the raw value is kept
- **AND** the user is shown a message that the value could not be used and was
  left unchanged
- **AND** the warning is also written to the log