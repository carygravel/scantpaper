# test-coverage Specification

## Purpose

Defines what the coverage gate measures, how test code is audited for
unexecuted statements, and where tests live, so the gate produces the
same result on a developer machine, in GitHub Actions and in Debian
autopkgtest.

## Requirements

### Requirement: Coverage gate reports shipped application code

The coverage gate SHALL report only the `scantpaper` application package
and SHALL fail when combined statement and branch coverage of that code is
below 99%. Test modules SHALL NOT contribute statements or branches to the
reported total.

#### Scenario: Test modules are absent from the report

- **WHEN** a coverage report is produced for the project
- **THEN** no module under the test tree contributes to the reported total

#### Scenario: Uncovered application code fails the gate

- **WHEN** application code loses coverage below the configured threshold
- **THEN** the gate fails regardless of how many tests were executed

#### Scenario: A skipped test does not move the application total

- **WHEN** a test is skipped because an optional tool is unavailable
- **THEN** the reported application coverage and the gate result are
  unchanged

### Requirement: Coverage result does not depend on the environment

Every environment that runs the test suite SHALL enforce the same coverage
threshold over the same application code. The result MUST NOT depend on
which optional test tooling is installed.

#### Scenario: Debian matches local and GitHub

- **WHEN** a revision passes the coverage gate locally and in GitHub Actions
- **THEN** the Debian autopkgtest run passes with the same application
  coverage percentage

#### Scenario: Optional tooling is absent

- **WHEN** an optional test dependency such as the `openspec` CLI is not
  installed
- **THEN** the coverage gate still passes on application coverage alone

### Requirement: Test code is audited in the complete environment

In the canonical test environment that installs every optional test
dependency, every test module SHALL be executed and SHALL contain no
unexecuted statements. The audit SHALL fail when a test module is absent
from the run data or has a missing statement. An environment that
legitimately lacks optional tools SHALL NOT run the audit.

#### Scenario: An unexecuted helper fails the audit

- **WHEN** a helper or test body in a test module is never executed
- **THEN** the audit fails and names the module and statement

#### Scenario: An uncollected module fails the audit

- **WHEN** a test module is not imported by the run
- **THEN** the audit fails and names the module

#### Scenario: A skip in the canonical environment fails the audit

- **WHEN** a test skips in the environment that installs all optional
  dependencies
- **THEN** its unexecuted statements make the audit fail

#### Scenario: An incomplete environment is not audited

- **WHEN** an environment lacks optional tooling, such as Debian without
  the `openspec` CLI
- **THEN** it runs the coverage gate but does not run the test-code audit

### Requirement: Test partial branches are ratcheted

The test-code audit SHALL report partial branches in test modules and SHALL
fail when their number exceeds the recorded baseline, so a newly dead branch
is visible without reclassifying existing defensive branches.

#### Scenario: The recorded baseline passes

- **WHEN** the partial-branch count equals the recorded baseline
- **THEN** the audit passes

#### Scenario: A new partial branch fails

- **WHEN** a change adds a partial branch in test code
- **THEN** the audit fails until the branch is exercised or the baseline is
  deliberately updated

### Requirement: Developer-tooling tests live with their tools

A test module whose sole subject is a script in `dev/` SHALL live under
`dev/tests/`. The default `pytest` invocation SHALL collect and run those
modules alongside the application tests. A module that also validates
shipped artifacts SHALL remain in the application test tree.

#### Scenario: Default run collects dev tests

- **WHEN** `pytest` runs from the repository root
- **THEN** the modules under `dev/tests/` are collected and executed

#### Scenario: Mixed modules stay with the application

- **WHEN** a module validates both a developer script and shipped data
- **THEN** it remains under the application test tree
