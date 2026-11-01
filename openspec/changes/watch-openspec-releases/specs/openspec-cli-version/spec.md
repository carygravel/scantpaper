# Spec Delta

## Purpose

Keeps the OpenSpec CLI that CI installs current and trustworthy: records the
pinned release in one place, detects newer releases, proves a candidate passes
this repository's validation before recommending it, and reports that state
where the maintainer will see it.

## ADDED Requirements

### Requirement: Pinned CLI version is recorded in one place

The repository SHALL record the OpenSpec CLI version that CI installs in a
single file, and every CI job that runs the CLI SHALL install exactly that
version.

#### Scenario: CI installs the recorded version

- **WHEN** the pin file contains `1.16.0` and CI runs
- **THEN** CI installs `@fission-ai/openspec@1.16.0` and validates with it

#### Scenario: A bump changes what CI installs

- **WHEN** the pin file is edited to a different release
- **THEN** the next CI run installs and validates with that release, without
  any other workflow change

### Requirement: A newer release is detected from the package registry

The check SHALL compare the pinned version with the release the npm registry
reports as `latest`, and SHALL report the pinned, installed and latest
versions together.

#### Scenario: A newer release exists

- **WHEN** the pin is `1.14.3` and the registry reports `1.16.0`
- **THEN** the check reports that an update is available and names both
  versions

#### Scenario: The pin is current

- **WHEN** the pin matches the registry's `latest`
- **THEN** the check reports that no update is needed

#### Scenario: Reports are machine-readable

- **WHEN** the check is asked for JSON or Markdown output
- **THEN** it emits a single report containing the versions, the state, and
  the validation results, without ANSI colour or interactive prompts

### Requirement: A candidate release is validated before it is recommended

Before recommending an update, the check SHALL run the same validation
commands that CI runs against the candidate release, and SHALL classify the
outcome as safe or blocked.

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

### Requirement: Update state is reported as one living issue

The scheduled check SHALL keep at most one open issue for OpenSpec updates,
labelled `openspec-update`, whose title states whether the candidate is safe
to upgrade or blocked.

#### Scenario: An update is available

- **WHEN** the check classifies a newer release as safe or blocked
- **THEN** it opens an issue, or updates the open one, with the versions, the
  validation result, the failing command's output when blocked, and the
  command to bump the pin

#### Scenario: The state changes between runs

- **WHEN** an open issue exists and a later run reaches a different state
- **THEN** the existing issue is updated in place rather than a second issue
  being opened

#### Scenario: The pin catches up

- **WHEN** the pin matches the registry's `latest` and an update issue is
  open
- **THEN** the issue is closed, so an outdated recommendation does not
  linger

### Requirement: Every run records its conclusion

Each scheduled or manual run SHALL record the pinned, installed and latest
versions and the resulting state on the run summary page, whether or not an
issue is filed.

#### Scenario: The pin is current

- **WHEN** a run finds no newer release than the pin
- **THEN** the summary states that the pin is current, and no issue is filed
  or updated

#### Scenario: The candidate is blocked

- **WHEN** a run classifies the newer release as blocked
- **THEN** the summary names the failing command, in addition to the issue
  that carries its full output

#### Scenario: The state cannot be determined

- **WHEN** the pin file or registry cannot be read
- **THEN** the run fails with the underlying error instead of recording a
  summary that reads like a clean result

### Requirement: An undeterminable state fails loudly

The check SHALL distinguish "no update" from "could not tell": an unreadable
pin file, registry, or candidate version SHALL exit non-zero without filing
an issue, while a detected update SHALL exit successfully.

#### Scenario: The registry is unreachable

- **WHEN** the npm registry cannot be read
- **THEN** the check exits non-zero, files no issue, and reports the
  underlying error

#### Scenario: An update is merely available

- **WHEN** the check detects and validates a newer release
- **THEN** it exits successfully, because a finding is not a failure
