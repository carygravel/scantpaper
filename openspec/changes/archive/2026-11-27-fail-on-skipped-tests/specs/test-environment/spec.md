# Spec Delta

## Purpose

Defines how a test run reports tests that were skipped because their
environment is incomplete, and the opt-in mode that turns those skips
into a failure.

## ADDED Requirements

### Requirement: Strict mode is opt-in

A test run SHALL treat every skipped test as a failure only when
`SCANTPAPER_FAIL_ON_SKIP=1` is set or `--fail-on-skip` is passed. The
flag and the variable SHALL select the same behavior. With neither
switch, a skipped test SHALL retain pytest's normal skipped outcome.

#### Scenario: The environment variable enables strict mode

- **WHEN** `SCANTPAPER_FAIL_ON_SKIP=1` is set and a test is skipped
- **THEN** the session exits non-zero

#### Scenario: The command-line flag enables strict mode

- **WHEN** `pytest --fail-on-skip` runs and a test is skipped
- **THEN** the session exits non-zero

#### Scenario: Neither switch leaves the default run

- **WHEN** neither switch is set and a test is skipped
- **THEN** the skip is reported as skipped
- **AND** the session exits successfully when no test failed

#### Scenario: A strict run with no skips succeeds

- **WHEN** a strict switch is set and no test skips
- **THEN** the session exit status reflects the normal pass/fail result

### Requirement: Every skipped test is reported

A strict run SHALL report every skipped test by node id and skip reason
before exiting, including skips caused by a marker, a fixture, or an
import guard.

#### Scenario: Multiple skips are all listed

- **WHEN** a strict run skips tests for different reasons
- **THEN** every skipped node id and its reason appear in the session
  output

#### Scenario: An environment skip keeps its reason

- **WHEN** a strict run skips a locale-dependent test because the locale
  is absent
- **THEN** the report names the missing locale

### Requirement: Strict mode does not force execution

Strict mode SHALL NOT change which tests are collected or executed. A
test whose guard finds the environment incomplete SHALL remain
unexecuted; the session SHALL nonetheless fail and name the test.

#### Scenario: A guarded test remains unexecuted

- **WHEN** a strict run reaches a test guarded by a missing dependency
- **THEN** the test body does not run
- **AND** the session fails and names the test

### Requirement: Expected failures are not skips

A test reported as xfailed or xpassed SHALL NOT be treated as a skipped
test in a strict run.

#### Scenario: An expected failure does not fail the strict run

- **WHEN** a strict run reports an xfailed test
- **THEN** the session does not fail because of the expected failure

### Requirement: Deselection is not a skip

A test excluded by a selection or ignore option such as `-m`, `-k`,
`--deselect` or `--ignore` SHALL NOT be treated as a skipped test in a
strict run.

#### Scenario: A deselected marker does not fail

- **WHEN** a strict run excludes the `slow` marker with
  `-m "not slow"`
- **THEN** strict mode does not fail because of the deselected tests

#### Scenario: An ignored module does not fail

- **WHEN** a strict run ignores a module with `--ignore`
- **THEN** strict mode does not fail because of the ignored tests

### Requirement: Canonical environment dependencies are documented

The testing documentation SHALL name every environment dependency that
the suite probes for, including at least the `de_DE.utf8` locale, the
external OCR, DjVu, PDF and packaging tools, a display, and the
`openspec` CLI, and SHALL document both strict-mode switches.

#### Scenario: A packager can find the full dependency list

- **WHEN** a packager reads the testing documentation
- **THEN** it names the locale, tools, display and optional CLI that the
  suite probes for
- **AND** it names `--fail-on-skip` and `SCANTPAPER_FAIL_ON_SKIP`
