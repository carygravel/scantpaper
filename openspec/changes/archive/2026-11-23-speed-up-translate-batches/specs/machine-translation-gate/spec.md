# Spec Delta

## ADDED Requirements

### Requirement: One entry's independent proposals are elicited concurrently

A batch SHALL request the independent proposals for one entry concurrently,
without waiting for one proposal before starting the next, and SHALL return
them in the configured proposer order. The recorded proposals, checks and
evidence of a concurrent elicitation SHALL be the same as a serial one.

#### Scenario: Two independent proposers answer

- **WHEN** a gate run requests proposals from two independent families for one
  entry
- **THEN** the two requests overlap and the proposals are returned in the
  configured proposer order with identical content to a serial run

#### Scenario: A single proposer path

- **WHEN** only one deployment is configured to propose
- **THEN** it is requested once and concurrency is not engaged

#### Scenario: A proposer fails

- **WHEN** a proposer request fails at the transport layer
- **THEN** the run fails as it does today and makes no approval

### Requirement: A judge that exceeds its deadline becomes an abstention

A batch SHALL accept a judge deadline and SHALL bound the judge call by it. A
judge that does not answer within the deadline, or whose transport request
fails, SHALL be recorded as an abstention with a reason, the entry SHALL
remain fuzzy and SHALL be retried by a later batch, and the batch SHALL
continue. A missing credential SHALL remain a hard error.

#### Scenario: A judge answers within its deadline

- **WHEN** the judge answers before the deadline
- **THEN** the entry is decided exactly as it is without the deadline

#### Scenario: A judge exceeds its deadline

- **WHEN** the judge call does not complete within the deadline
- **THEN** the entry is recorded as abstained with a reason naming the
  deadline, the batch continues, and the entry stays fuzzy for a later batch

#### Scenario: A judge transport request fails

- **WHEN** the judge's model request fails at the transport layer
- **THEN** the entry is recorded as abstained rather than aborting the run

#### Scenario: A credential is missing

- **WHEN** the judge deployment's key environment variable is unset
- **THEN** the run reports the missing variable and fails, and is not treated
  as an abstention

### Requirement: A batch report names judge-timeout abstentions

A batch report SHALL count the entries that were abstained because the judge
exceeded its deadline or failed at the transport layer, separately from other
abstentions, in both the human and JSON forms.

#### Scenario: A judge is bounded

- **WHEN** a batch defers one or more entries because their judge exceeded the
  deadline or failed
- **THEN** the report names that count alongside the abstained total

#### Scenario: No judge is bounded

- **WHEN** a batch completes with no judge-timeout abstention
- **THEN** the report shows none and records no count for it
