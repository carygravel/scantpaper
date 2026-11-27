# Spec Delta

## ADDED Requirements

### Requirement: Generated instruction files match the pinned CLI

The repository SHALL keep the instruction files the pinned CLI generates, and
a push SHALL fail when regenerating them with that CLI would change a file
inside the repository. A change to the CLI's own global configuration SHALL
NOT fail the push.

#### Scenario: A pin bump without refreshed files fails

- **WHEN** the pin names a release that generates different instruction files
  and those files are not refreshed in the same push
- **THEN** the push SHALL fail
- **AND** the failure SHALL name each repository file that would change

#### Scenario: Refreshed files pass

- **WHEN** regenerating the instruction files with the pinned CLI would change
  no file inside the repository
- **THEN** the push SHALL pass

#### Scenario: The global configuration is ignored

- **WHEN** regeneration would only add or update the CLI's own configuration
  outside the repository
- **THEN** the push SHALL NOT fail

## MODIFIED Requirements

### Requirement: Update state is reported as one living issue

The scheduled check SHALL keep at most one open issue for OpenSpec updates,
labelled `openspec-update`, whose title states whether the candidate is safe
to upgrade or blocked. Its adoption instructions SHALL name every step of a
bump, including regenerating the instruction files the CLI generates.

#### Scenario: An update is available

- **WHEN** the check classifies a newer release as safe or blocked
- **THEN** it opens an issue, or updates the open one, with the versions, the
  validation result, the failing command's output when blocked, and the
  command to bump the pin

#### Scenario: The adoption instructions include the refresh step

- **WHEN** the issue states how to adopt the reported release
- **THEN** the instructions SHALL include regenerating the instruction files
- **AND** they SHALL include running the validation commands CI runs

#### Scenario: The state changes between runs

- **WHEN** an open issue exists and a later run reaches a different state
- **THEN** the existing issue is updated in place rather than a second issue
  being opened

#### Scenario: The pin catches up

- **WHEN** the pin matches the registry's `latest` and an update issue is
  open
- **THEN** the issue is closed, so an outdated recommendation does not
  linger
