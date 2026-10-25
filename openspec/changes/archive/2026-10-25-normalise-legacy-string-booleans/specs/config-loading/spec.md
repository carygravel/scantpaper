# Spec Delta

## ADDED Requirements

### Requirement: Normalise stringified legacy boolean settings

When a recognised boolean setting holds a string written by gscan2pdf 2.x,
the system SHALL convert it losslessly to the corresponding boolean at load
time. Accepted spellings are the empty string for false, and `"true"`,
`"false"`, `"1"` and `"0"`. The conversion SHALL
be logged at INFO and SHALL NOT be shown in the start-up message. The next
config write SHALL store the boolean so the conversion does not repeat. Any
other string SHALL keep the existing wrong-type behaviour.

#### Scenario: Legacy empty string means false

- **WHEN** the loaded config contains `"post_save_hook": ""` from a
  gscan2pdf 2.x config
- **THEN** the setting is `false` for the session and the post-save hook stays
  disabled
- **AND** the correction is written to the log at INFO level
- **AND** no start-up message is shown for that value
- **AND** the next config write stores `false`, not `""`

#### Scenario: Legacy stringified true from the same config

- **WHEN** the loaded config contains `"cache options": "1"` from a
  gscan2pdf 2.x config
- **THEN** the setting is `true` and no start-up message is shown
- **AND** the next config write stores `true`

#### Scenario: Other accepted spellings

- **WHEN** the loaded config stores `"TRUE"`, `"false"` or `"0"` in a boolean
  setting
- **THEN** the setting is converted to the matching boolean
- **AND** no start-up message is shown for that value

#### Scenario: Every boolean setting is covered

- **WHEN** the loaded config stores `""` in `close_dialog_on_save` or in any
  other setting whose default is a boolean
- **THEN** that setting is `false` and the correction is logged at INFO level
- **AND** no start-up message is shown for that value

#### Scenario: Unrecognised non-empty string still warns

- **WHEN** the loaded config contains `"post_save_hook": "evince %i"` or
  another non-empty string that is not a boolean spelling
- **THEN** the raw value is kept
- **AND** the start-up message reports that the value cannot be used as bool
