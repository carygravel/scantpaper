# Spec Delta

## ADDED Requirements

### Requirement: Version-keyed migrations skip an unknown version

When the saved config carries a version string that contains no digits, the
system SHALL treat it as current for version-keyed migrations and SHALL NOT
re-run them. A missing version SHALL continue to mean a legacy config whose
migrations apply.

#### Scenario: Unknown version is not migrated

- **WHEN** the config contains `"version": "unknown"` and
  `"threshold tool": 20`
- **THEN** the threshold setting remains 20

#### Scenario: Missing version is treated as legacy

- **WHEN** the config contains `"threshold tool": 60` and no `version` key
- **THEN** the threshold setting is migrated to 40

#### Scenario: Old version is migrated

- **WHEN** the config contains `"version": "3.0.15"` and
  `"threshold tool": 80`
- **THEN** the threshold setting is migrated to 20

#### Scenario: Current version is not migrated

- **WHEN** the config contains `"version": "3.0.16"` and
  `"threshold tool": 20`
- **THEN** the threshold setting remains 20
