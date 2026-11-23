# Spec Delta

## ADDED Requirements

### Requirement: A batch announces its selection and duration

A batch SHALL print a start banner before its first model request reporting
the selected, skipped and unsupported entry counts, the spend estimate and an
expected duration, and SHALL name the prior the duration came from.

#### Scenario: A batch starts with a qualified language

- **WHEN** a `translate` batch starts and every role release is qualified
- **THEN** it prints one banner line before the first model request naming
  the selected count and an expected duration

#### Scenario: No batch history exists for the language

- **WHEN** the language has no recorded gate runs to derive a duration from
- **THEN** the banner reports the cross-language prior as its basis

### Requirement: A batch reports one progress line per entry

A batch SHALL report progress after each processed entry to standard error
when progress is enabled, naming the entry position against the selection,
the approved and abstained counts so far, the spend to date, the observed
rate and the completion estimate. Progress SHALL NOT be written to standard
output.

#### Scenario: Progress is enabled in a terminal

- **WHEN** a batch runs with `--progress line`
- **THEN** one line per processed entry is written to standard error and the
  standard output is unchanged

#### Scenario: Progress and a JSON report are combined

- **WHEN** a batch runs with `--json` and `--progress line`
- **THEN** standard output parses as exactly one JSON document

#### Scenario: Progress is left to its default without a terminal

- **WHEN** standard error is not a terminal and progress is `auto`
- **THEN** no per-entry line is written

### Requirement: The completion estimate is a rounded band in local time

The batch SHALL express the completion estimate as a range rounded to five
minutes, derived from the spread of completed entries, and SHALL show the
expected completion time in the operator's local time zone.

#### Scenario: Several entries have completed

- **WHEN** at least five entries have been processed
- **THEN** the estimate is a five-minute-rounded range with a local
  completion time, not a single unqualified value

#### Scenario: Ledger timestamps are in UTC

- **WHEN** the machine's local time zone is not UTC
- **THEN** the displayed completion time is converted from the stored UTC
  timestamps to local time

### Requirement: Batch progress is persisted per language

A batch SHALL write one state file per language under the project's ignored
cache directory after each entry, replacing it atomically, recording the
process, start time, selection, completed, approved, abstained, spend,
progress weight, estimate and update time. The file SHALL be advisory: a
missing, unreadable or stale state file SHALL NOT change a batch's outcome.

#### Scenario: An entry completes

- **WHEN** a batch finishes an entry
- **THEN** its state file is replaced atomically and its update time advances

#### Scenario: A previous state file cannot be read

- **WHEN** the state file is missing or unparsable
- **THEN** the batch runs to completion without failing

#### Scenario: Two languages run at once

- **WHEN** two batches run for different languages
- **THEN** each writes only its own state file

### Requirement: `status` reports every language with a batch or recent activity

The gate SHALL provide a `status` command reporting, per language, the
selection, completed count, spend, rate, completion estimate and freshness.
It SHALL report a language from a live state file, SHALL infer one from
recent ledger gate runs when no state file exists, SHALL mark whether each
number is live or inferred, and SHALL offer a JSON form.

#### Scenario: A batch was started before this change

- **WHEN** a language has recent gate runs but no state file
- **THEN** `status` reports it with inferred numbers and a freshness age

#### Scenario: Two languages are in flight

- **WHEN** two batches run concurrently
- **THEN** `status` reports both, each with its own progress and age

#### Scenario: JSON output is requested

- **WHEN** `status --json` runs
- **THEN** it prints one object per language and exits zero

### Requirement: `status` needs no model credential

The `status` command SHALL read local files only and SHALL succeed when no
model credential is present in the environment.

#### Scenario: The environment has no key

- **WHEN** `status` runs with no model credential configured
- **THEN** it reports the batches and exits zero without naming a missing
  key

### Requirement: `status` separates a stalled batch from a slow one

The state file SHALL record the model call in flight, and `status` SHALL
report how long that call has been waiting. A batch with no completed entry
for longer than twice its own recent median entry duration SHALL be reported
as stalled, and one whose recorded process is gone SHALL be reported as
abandoned.

#### Scenario: A call outlives the recent median

- **WHEN** a call has been in flight for more than twice the recent median
  entry duration
- **THEN** `status` names the waiting role and reports the batch as stalled

#### Scenario: An abandoned batch is queried

- **WHEN** the recorded process is gone and the state file is old
- **THEN** `status` reports the batch as abandoned and prints no completion
  estimate

### Requirement: A batch can stop at a wall-clock budget

A batch SHALL accept a wall-clock budget, SHALL check it between entries,
SHALL stop before beginning an entry after the deadline, and SHALL report
the stop reason with the completed and remaining counts. It SHALL NOT abort
a request already in flight.

#### Scenario: The deadline passes between entries

- **WHEN** the deadline is reached after an entry completes
- **THEN** the batch stops before the next entry and reports the stop reason
  as a time budget with the completed and remaining counts

#### Scenario: Both budgets are set

- **WHEN** a batch has both a cost budget and a time budget
- **THEN** whichever is reached first stops the batch and its reason is
  reported

### Requirement: An interrupted batch reports and names its resume command

When an operator interrupts a batch, the gate SHALL report the entries
completed, the entries remaining, the spend and the command that resumes the
batch, without printing a traceback. Every approved entry SHALL remain
persisted.

#### Scenario: The operator interrupts a batch

- **WHEN** the operator sends an interrupt during a batch
- **THEN** the output names the resume command, the entries remaining and the
  spend

#### Scenario: The interrupted batch is resumed

- **WHEN** the reported resume command runs
- **THEN** entries already approved by the interrupted batch are not
  submitted to the gate again

### Requirement: Batch progress and catalog completion are reported separately

A batch report SHALL distinguish the entries the batch processed from the
catalog strings that remain untranslated, and SHALL state that abstained
entries are retried by a later batch.

#### Scenario: A batch abstains

- **WHEN** a batch abstains on an entry
- **THEN** the report shows the remaining untranslated strings separately
  from the batch's processed count and says those entries are retried
