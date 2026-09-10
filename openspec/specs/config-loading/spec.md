# config-loading

## Purpose

Ensures users keep their configuration when the settings file is damaged or
partially invalid: valid settings are rescued instead of discarded, backups are
preserved, and the user is told what happened.

## Requirements

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

### Requirement: Do not silently overwrite an unrescued config file

The system SHALL NOT write a fully defaulted configuration over `scantpaperrc`
immediately after a failed parse, because that permanently destroys the user's
settings. When the config failed to load and was rescued or defaulted, the next
save SHALL wait until the user has been informed, and SHALL NOT replace the
backup file.

#### Scenario: Closing the app after a failed load

- **WHEN** the config failed to parse at startup, settings were rescued, and the
  user quits without making further changes
- **THEN** the original broken file remains available as `scantpaperrc.old`
- **AND** the write that happens on quit does not silently overwrite the
  original with defaults before the user has acknowledged the problem

### Requirement: Keep recognised settings with wrong value types

When the config file parses but contains a value of an unexpected type for a
recognised key (e.g. a string where an integer is expected), the system SHALL
normalise the value to a usable form when one exists, otherwise preserve the raw
setting for inspection rather than silently replacing it with the default.

#### Scenario: String value where an integer is expected

- **WHEN** the config contains `"rotate facing": "270"` (a string instead of an
  integer)
- **THEN** the rotation setting is still applied as 270 degrees
- **AND** the application does not silently fall back to the default of 0

### Requirement: Valid config files load and round-trip unchanged

Fully valid config files SHALL be parsed with no behaviour change from before
this capability. Rescuing SHALL only activate when parsing fails or a value is
wrongly typed; a valid file SHALL take exactly the same effect as it does today.

#### Scenario: Unmodified valid config at startup

- **WHEN** `scantpaperrc` is valid JSON with `"rotate facing": 90` and
  `"rotate reverse": 270`
- **THEN** the application starts with those values in the scan dialog
- **AND** no backup file is created and no user notification is shown

#### Scenario: Round-trip after a normal session

- **WHEN** the user changes rotation settings and quits cleanly
- **THEN** the settings are written back with the same values the application
  used during the session
- **AND** the file remains valid JSON readable on the next start