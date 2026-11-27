# Spec Delta

## Purpose

Defines how the project measures the strength of its tests with mutation
testing: which shipped code is mutated, how each mutant is classified, how
survivors are triaged, and how the scheduled report is published without
gating normal development.

## ADDED Requirements

### Requirement: Mutation testing targets shipped application code

The check SHALL mutate only modules that ship in the `scantpaper` package.
It SHALL NOT mutate `dev/` scripts, test modules, generated files, or
third-party code.

#### Scenario: A shipped module is mutated

- **WHEN** a target manifest names a module under `src/scantpaper`
- **THEN** the run generates mutants for that module
- **AND** the report identifies the module and the mutated lines

#### Scenario: Developer tooling is not mutated

- **WHEN** the target manifest is inspected or a run starts
- **THEN** no module under `dev/` is treated as a mutation target

### Requirement: Every generated mutant has an explicit outcome

A run SHALL report every generated mutant as killed, survived, no-test,
error, or timeout. It SHALL NOT silently drop a mutant. A mutant with no
selected test SHALL be reported as no-test and SHALL NOT be counted as
killed.

#### Scenario: A mutant has no selected test

- **WHEN** no collected test exercises a mutated line
- **THEN** the report lists the mutant as no-test
- **AND** the run summary shows the no-test count separately from killed
  and survived

#### Scenario: The tool cannot classify a mutant

- **WHEN** a mutant produces an execution error rather than a test result
- **THEN** the report lists it as an error
- **AND** the run does not count it as a survivor or a kill

### Requirement: The tool version is pinned outside shipping dependencies

The mutation-tool version SHALL be recorded in one repository file, and
every local or CI run SHALL install exactly that version. The tool SHALL be
a development-only dependency and SHALL NOT be added to the runtime
dependencies or the `[test]` extra.

#### Scenario: CI installs the pinned version

- **WHEN** the mutation workflow runs
- **THEN** it installs the version recorded in the pin file
- **AND** the report records that version

#### Scenario: A normal package install is unaffected

- **WHEN** a user installs `scantpaper` or its `[test]` extra
- **THEN** the mutation tool is not installed as a dependency

### Requirement: A mutation run is independent of the coverage gate

The runner SHALL neutralise the normal coverage threshold and SHALL NOT
write to the coverage data consumed by the coverage gate. A mutation run
over a single target SHALL succeed even though that target's tests do not
meet the package-wide coverage threshold.

#### Scenario: A single-target run is not failed by coverage

- **WHEN** the runner mutates one module with only that module's tests
- **THEN** the package-wide coverage threshold does not fail the run

#### Scenario: Existing coverage data is preserved

- **WHEN** a mutation run finishes
- **THEN** the coverage data used by the coverage gate is unchanged

### Requirement: Survivors are triaged with a recorded reason

A surviving mutant SHALL either remain visible in the report or be
suppressed by an inline pardon that records a reason (`equivalent`,
`untestable`, or `out_of_scope`) and a justification. Blanket file or
package exclusions SHALL NOT be used to hide survivors. The report SHALL
show the pardon count.

#### Scenario: An equivalent mutant is pardoned with a reason

- **WHEN** a survivor is judged equivalent
- **THEN** the source records an inline pardon with the equivalent reason
  and a justification

#### Scenario: An unexplained survivor remains visible

- **WHEN** a survivor has no pardon
- **THEN** the report lists it as survived
- **AND** the run summary includes it in the survivor count

### Requirement: The target set is recorded in one place

The repository SHALL record the source targets used by the scheduled run in
one manifest. Adding or removing a target SHALL be a change to that
manifest only and SHALL NOT require editing the workflow.

#### Scenario: A target is added to the manifest

- **WHEN** a module is added to the target manifest
- **THEN** the next scheduled run mutates it
- **AND** no workflow file changes

#### Scenario: The manifest is empty or invalid

- **WHEN** the manifest is missing, empty, or names no shipped module
- **THEN** the run fails and reports the manifest problem
- **AND** it does not report a clean mutation score

### Requirement: The scheduled report is advisory

A scheduled or manually dispatched workflow SHALL run the recorded targets,
upload a machine-readable report and an HTML report, and record a run
summary. It SHALL file or update at most one issue for findings. It SHALL
NOT gate pull requests. A run that completes with survivors SHALL exit
successfully; a run that cannot complete SHALL exit non-zero.

#### Scenario: Survivors do not fail the job

- **WHEN** a run completes and reports survivors
- **THEN** the job exits successfully
- **AND** the summary and issue name the survivor count

#### Scenario: A run failure fails the job

- **WHEN** the tool cannot start, the baseline suite fails, or a report
  cannot be read
- **THEN** the job exits non-zero
- **AND** no issue is filed that reads like a completed result

#### Scenario: Findings are reported in one issue

- **WHEN** a run produces findings and an open mutation-testing issue exists
- **THEN** the existing issue is updated instead of a second issue being
  opened

### Requirement: A report identifies its environment

Every report SHALL record the mutation-tool version, the Python version,
and the versions of the external tools that affect the tested behaviour.
A report from one environment SHALL NOT be presented as comparable with a
report from a different environment.

#### Scenario: The report records the environment

- **WHEN** a mutation run finishes
- **THEN** its report names the tool, Python, OCRmyPDF, and Ghostscript
  versions used

#### Scenario: Scores are compared within an environment

- **WHEN** two reports are compared
- **THEN** the comparison is only made when their recorded environments
  match
