# Spec Delta

## Purpose

Tracks the ruff and ty releases that CI installs: records the pinned versions
in one place, detects newer releases from PyPI, proves a candidate still
passes this repository's lint and type checks before recommending it, and
reports the per-tool state where the maintainer will see it.

## ADDED Requirements

### Requirement: Pinned lint-tool versions are recorded in one place

The repository SHALL record the ruff and ty versions that CI installs in a
single file, and every CI job that installs either tool SHALL install exactly
the recorded version.

#### Scenario: CI installs the recorded versions

- **WHEN** the pin file contains `ruff=0.16.7` and `ty=0.0.85` and CI runs
- **THEN** every job installs `ruff==0.16.7` and `ty==0.0.85` and validates
  with those tools

#### Scenario: A bump changes what CI installs

- **WHEN** the pin file is edited to different releases
- **THEN** the next CI run installs and validates with those releases,
  without any other workflow change

### Requirement: A newer release is detected per tool from the package registry

The check SHALL compare each pinned version with the release PyPI reports as
latest for the same tool, and SHALL report the pinned, installed and latest
versions for every tool.

#### Scenario: A newer release exists

- **WHEN** the ruff pin is `0.16.7` and PyPI reports `0.17.0`
- **THEN** the check reports that a ruff update is available and names both
  versions

#### Scenario: The pins are current

- **WHEN** the ruff and ty pins each match the latest release PyPI reports
- **THEN** the check reports that no update is needed for either tool

#### Scenario: Reports are machine-readable

- **WHEN** the check is asked for JSON or Markdown output
- **THEN** it emits a single report containing each tool's versions, state,
  and validation results, without ANSI colour or interactive prompts

### Requirement: A candidate release is validated before it is recommended

Before recommending an update for a tool, the check SHALL run the same
commands CI runs against that tool's candidate release, and SHALL classify
each tool's update as safe or blocked independently.

#### Scenario: Candidate passes validation

- **WHEN** a candidate release passes every configured command
- **THEN** the check classifies that tool's update as safe to upgrade

#### Scenario: Candidate fails validation

- **WHEN** a candidate release fails any configured command
- **THEN** the check classifies that tool's update as blocked and records
  which command failed and its output

#### Scenario: Tools are classified independently

- **WHEN** the ruff candidate passes but the ty candidate fails
- **THEN** the check reports ruff as safe and ty as blocked in the same
  report

#### Scenario: Validation does not modify the repository

- **WHEN** the check validates a candidate
- **THEN** it reads the repository only, and no change, spec, or pin file is
  written

### Requirement: Config-migration warnings are surfaced

The check SHALL report warnings a candidate emits about obsolete
configuration or rule names, so an update that also needs a `pyproject.toml`
change is distinguishable from one that is a pure pin bump.

#### Scenario: A candidate warns about removed settings

- **WHEN** a candidate passes with exit code zero but prints a warning about
  an obsolete setting or rule name
- **THEN** the check reports the warning alongside the safe result

#### Scenario: A candidate fails on newly added rules

- **WHEN** a candidate fails because a newly added lint rule fires
- **THEN** the check reports the failure with the offending rule in the
  recorded output

### Requirement: Update state is reported as one living issue

The scheduled check SHALL keep at most one open issue for lint-tool updates,
labelled `lint-update`, whose title states the state per tool.

#### Scenario: An update is available

- **WHEN** the check classifies a newer release for either tool as safe or
  blocked
- **THEN** it opens an issue, or updates the open one, with each tool's
  versions, the validation results, the failing command's output when
  blocked, and the command to bump the pins

#### Scenario: The state changes between runs

- **WHEN** an open issue exists and a later run reaches a different state
- **THEN** the existing issue is updated in place rather than a second issue
  being opened

#### Scenario: The pins catch up

- **WHEN** both pins match the latest releases and an update issue is open
- **THEN** the issue is closed, so an outdated recommendation does not
  linger

### Requirement: Every run records its conclusion

Each scheduled or manual run SHALL record each tool's pinned, installed and
latest versions and the resulting state on the run summary page, whether or
not an issue is filed.

#### Scenario: The pins are current

- **WHEN** a run finds no newer release than the pins
- **THEN** the summary states that the pins are current, and no issue is
  filed or updated

#### Scenario: A tool is blocked

- **WHEN** a run classifies one tool's newer release as blocked
- **THEN** the summary names the failing command, in addition to the issue
  that carries its full output

#### Scenario: The state cannot be determined

- **WHEN** the pin file or a registry cannot be read
- **THEN** the run fails with the underlying error instead of recording a
  summary that reads like a clean result

### Requirement: An undeterminable state fails loudly

The check SHALL distinguish "no update" from "could not tell": an unreadable
pin file, registry, or candidate version SHALL exit non-zero without filing
an issue, while a detected update SHALL exit successfully.

#### Scenario: The registry is unreachable

- **WHEN** PyPI cannot be read for a tool
- **THEN** the check exits non-zero, files no issue, and reports the
  underlying error

#### Scenario: An update is merely available

- **WHEN** the check detects and validates newer releases
- **THEN** it exits successfully, because a finding is not a failure
