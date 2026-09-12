## ADDED Requirements

### Requirement: Normalise legacy default scan options missing a frontend key

When the config file contains default scan options written by pre-v3
gscan2pdf in the backend-only shape (`{"backend": [{"mode": "Binary"}, ...]}`
without a `frontend` key), the system SHALL treat the options as having an
empty frontend option set and SHALL apply the stored backend options to the
scan dialog on startup. Normalised default scan options SHALL be stored with
both `frontend` and `backend` keys on the next config write, with their
option values preserved.

#### Scenario: Startup applies a legacy default scan options block

- **WHEN** the user starts the application after upgrading from gscan2pdf 2.x
  and the config contains `default-scan-options` stored as
  `{"backend": [{"mode": "Binary"}, {"resolution": 600}]}` with no `frontend`
  key
- **THEN** the application starts successfully
- **AND** the scan dialog shows the stored backend option values
  (mode `Binary`, resolution `600`) rather than the device defaults

#### Scenario: Legacy default scan options survive the session

- **WHEN** the user quits cleanly after starting with backend-only legacy
  default scan options
- **THEN** the written config contains `default-scan-options` with both a
  `frontend` key and a `backend` key
- **AND** the backend option values that were applied during the session are
  written back unchanged

#### Scenario: Legacy scan options are not silently wiped on load

- **WHEN** the user starts the application and a legacy backend-only
  `default-scan-options` block is present
- **THEN** loading and applying it SHALL NOT replace the stored backend
  options with an empty list before the session has changed them

#### Scenario: Well-formed default scan options are unaffected

- **WHEN** the config contains `default-scan-options` stored with both
  `frontend` and `backend` keys (the shape written by the application itself)
- **THEN** the options load exactly as before with no change to their values