# Spec Delta

## MODIFIED Requirements

### Requirement: A candidate release is validated before it is recommended

The check SHALL run a candidate release's spec, archive and change validation
rules against the repository, and SHALL classify the outcome as safe or
blocked. It SHALL NOT require the repository's generated instruction files to
match a candidate that is not the pin; that check runs after adoption.

#### Scenario: Candidate passes validation

- **WHEN** the candidate release validates every configured command
  successfully
- **THEN** the check classifies the update as safe to upgrade

#### Scenario: Candidate fails validation

- **WHEN** the candidate release fails any configured command
- **THEN** the check classifies the update as blocked and records which
  command failed and its output

#### Scenario: Validation does not modify the repository

- **WHEN** the check validates a candidate
- **THEN** it reads the repository only, and no change, spec, or pin file is
  written

#### Scenario: Generated files are not judged against the candidate

- **WHEN** the pin names an older release and the candidate would generate
  different instruction files
- **THEN** the check SHALL NOT classify the update as blocked for that reason

### Requirement: Update state is reported as one living issue

The scheduled check SHALL keep at most one open issue for OpenSpec updates,
labelled `openspec-update`, whose title states whether the candidate is safe
to upgrade or blocked. Its adoption instructions SHALL name every step of a
bump, including regenerating the instruction files and then verifying them
with the drift check.

#### Scenario: An update is available

- **WHEN** the check classifies a newer release as safe or blocked
- **THEN** it opens an issue, or updates the open one, with the versions, the
  validation result, the failing command's output when blocked, and the
  command to bump the pin

#### Scenario: The adoption instructions include the refresh step

- **WHEN** the issue states how to adopt the reported release
- **THEN** the instructions SHALL include regenerating the instruction files
- **AND** they SHALL include running the drift check after the refresh
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

### Requirement: Generated instruction files match the pinned CLI

The repository SHALL keep the instruction files the pinned CLI generates, and
a push SHALL fail when regenerating them with that CLI would change a file
inside the repository. A change to the CLI's own global configuration SHALL
NOT fail the push. The check SHALL judge only the release named by the pin:
when the CLI it runs is a different release, it SHALL report that it cannot
judge, naming both versions.

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

#### Scenario: A home-relative global configuration is ignored

- **WHEN** regeneration would only add or update a path the CLI reports
  relative to the home directory
- **THEN** the check SHALL resolve it against the home directory
- **AND** the push SHALL NOT fail

#### Scenario: The installed CLI is not the pin

- **WHEN** the check runs a CLI whose version differs from the pin
- **THEN** it SHALL exit non-zero
- **AND** it SHALL NOT report the files as current or stale
- **AND** it SHALL name the installed and pinned versions
