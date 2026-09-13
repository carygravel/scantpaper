## MODIFIED Requirements

### Requirement: Normalise recognised settings with wrong value types

When the config file parses but contains a value of an unexpected type for a
recognised key (e.g. a string where an integer is expected), the system SHALL
normalise the value to a usable form when one exists, otherwise preserve the
raw setting for inspection rather than silently replacing it with the default.

A lossless conversion SHALL be written to the log and SHALL NOT be shown to the
user in the message dialog. Only a value that cannot be made usable SHALL
produce a user-visible warning; that warning SHALL also be written to the log.

When a recognised setting holds a legacy `null` whose default offers a usable
str value (e.g. a gscan2pdf 2.x config with `"image type": null`), the system
SHALL migrate it to the recognised default for that setting at load time instead
of warning that it cannot be used. The migration SHALL be written to the log at
INFO level, SHALL NOT be shown to the user in the message dialog, and SHALL be
persisted on the next config write so the value is stored as the migrated
default rather than the raw `null`.

#### Scenario: A legacy null image type is migrated to the default

- **WHEN** the loaded config contains a recognised setting whose value is a
  legacy `null` and the setting's default offers a usable str value (e.g. a
  gscan2pdf 2.x config with `"image type": null`)
- **THEN** the value is migrated to the recognised default for that setting
  at load time
- **AND** the migration is written to the log at INFO level
- **AND** no user-visible warning is shown for that value
- **AND** the next config write stores the migrated value instead of the raw
  `null`

#### Scenario: A null image type left unchanged after migration

- **WHEN** the reporter starts cleanly after deleting the rc-file and
  accepting the migration of a legacy `null` image type
- **THEN** the migration does not re-fire on subsequent application starts
- **AND** the stored `image type` value is `"pdf"` and not `null`
