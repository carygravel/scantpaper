# Spec Delta

## ADDED Requirements

### Requirement: Qualification is runnable from the command line

The gate SHALL provide a `qualify` command that qualifies one configured
release for one language from that language's held-out human approvals,
writes the resulting record to the ledger, and reports the outcome. It SHALL
estimate the action and enforce an optional budget before making any model
call.

#### Scenario: A release qualifies

- **WHEN** the command runs for a configured release and a language whose
  held-out human approvals reproduce within tolerance
- **THEN** it writes a qualification record with the release, language,
  metric, tolerance, score, baseline size, drift baseline, cost and
  `qualified: true`, and exits successfully

#### Scenario: A release misses the tolerance

- **WHEN** the reproduced score is below the configured qualification
  tolerance
- **THEN** it writes the record with `qualified: false` and reports the score
  and tolerance

#### Scenario: No human baseline exists

- **WHEN** the language has no held-out human-origin approvals
- **THEN** it records an ineligible result with the reason
  `no held-out human entries`, makes no model call, and reports the outcome

#### Scenario: The budget is exceeded

- **WHEN** the estimated cost exceeds the optional budget
- **THEN** it makes no model call, writes no record and exits non-zero

#### Scenario: The release or catalog is invalid

- **WHEN** the release is not configured or the language catalog cannot be
  read
- **THEN** it reports the error, writes no record and exits non-zero

#### Scenario: A credential is missing

- **WHEN** the deployment's key environment variable is unset
- **THEN** it reports the variable name, writes no record and exits non-zero

#### Scenario: The command is re-run

- **WHEN** the command is run again for the same release and language
- **THEN** the ledger keeps one record for that pair, updated to the latest
  result

#### Scenario: JSON output is requested

- **WHEN** the command is run with the JSON option
- **THEN** it prints the qualification record as JSON
