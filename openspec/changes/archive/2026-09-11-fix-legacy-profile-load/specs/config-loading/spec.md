## ADDED Requirements

### Requirement: Normalise legacy profiles missing frontend options

When the config file contains a scan profile written by pre-v3 gscan2pdf that
lacks a `frontend` key (a backend-only profile), the system SHALL treat that
profile as having an empty frontend option set and SHALL NOT crash when opening
the scan dialog. Normalised profiles SHALL be stored with both `frontend` and
`backend` keys on the next config write, matching the structure written for
newly created profiles.

#### Scenario: Startup with a legacy backend-only profile

- **WHEN** the user starts the application after upgrading from gscan2pdf 2.x
  and the migrated config contains a profile stored as
  `{"backend": [{"resolution": 300}]}` with no `frontend` key
- **THEN** the application starts successfully
- **AND** the scan dialog lists the profile with its backend options intact

#### Scenario: Legacy profile survives the session

- **WHEN** the user quits cleanly after starting with a legacy backend-only
  profile
- **THEN** the written config contains the profile with both a `frontend` key
  and a `backend` key
- **AND** the profile's backend options are unchanged

#### Scenario: Well-formed profiles are unaffected

- **WHEN** the config contains a profile stored with both `frontend` and
  `backend` keys
- **THEN** the profile loads exactly as before with no change to its options