# Spec Delta

## ADDED Requirements

### Requirement: Drift probes are runnable from the command line

The gate SHALL provide a `drift` command that runs the fixed probe for one
configured deployment and language, infers the release from the deployment,
estimates the action and enforces an optional budget before any model call,
and records a paused excursion when the score is below the drift threshold.

#### Scenario: A probe passes

- **WHEN** the probe score meets or exceeds the configured drift threshold
- **THEN** it reports the score, threshold, call count and cost, records no
  pause, and exits successfully

#### Scenario: A probe detects drift

- **WHEN** the probe score is below the configured drift threshold
- **THEN** it records a paused excursion for the release, deployment and
  language with the score, cost and audit-window start, leaves existing
  approvals untouched, and exits successfully

#### Scenario: The audit window start is recorded

- **WHEN** a pause is recorded
- **THEN** the ledger stores the supplied audit-window start, or the run date
  when none is given

#### Scenario: The default probe is used

- **WHEN** the command runs without an explicit probe path
- **THEN** it reads `po/drift-probe/<language>.json`

#### Scenario: The probe is run without recording

- **WHEN** the command runs in dry-run mode
- **THEN** it reports the score and writes nothing to the ledger

#### Scenario: The deployment or probe is invalid

- **WHEN** the deployment is not configured or the probe file cannot be read
- **THEN** it reports the error, writes no pause and exits non-zero

#### Scenario: The budget is exceeded

- **WHEN** the estimated cost exceeds the optional budget
- **THEN** it makes no model call, writes no pause and exits non-zero

#### Scenario: A credential is missing

- **WHEN** the deployment's key environment variable is unset
- **THEN** it reports the variable name, writes no pause and exits non-zero

#### Scenario: JSON output is requested

- **WHEN** the command is run with the JSON option
- **THEN** it prints the probe result as JSON
