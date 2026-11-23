# Spec Delta

## MODIFIED Requirements

### Requirement: A batch report names judge-timeout abstentions

A batch report SHALL count the entries that were abstained because the judge
exceeded its deadline or failed at the transport layer, separately from other
abstentions, in both the human and JSON forms. It SHALL count an entry
abstained because its back-translation judge call could not be completed
separately from one whose back-translation genuinely changed the meaning, and
SHALL name both alongside the judge-timeout count.

#### Scenario: A judge is bounded

- **WHEN** a batch defers one or more entries because their judge exceeded the
  deadline or failed
- **THEN** the report names that count alongside the abstained total

#### Scenario: A back-translation is unavailable

- **WHEN** a batch defers an entry because its back-translation judge call
  failed at the transport layer
- **THEN** the report counts it under an unavailable-bucket distinct from the
  changed-meaning bucket and from the judge-timeout bucket

#### Scenario: A back-translation changes meaning

- **WHEN** a batch defers an entry because its back-translation differs from
  the source
- **THEN** the report counts it under the changed-meaning bucket, not the
  unavailable bucket

#### Scenario: No judge is bounded

- **WHEN** a batch completes with no judge-timeout abstention
- **THEN** the report shows none and records no count for it

## ADDED Requirements

### Requirement: A back-translation judge failure abstains the entry

A back-translation judge call that fails at the transport layer SHALL abstain
that one entry with a distinct reason naming the unavailability, SHALL leave
the entry fuzzy for a later batch, and SHALL NOT abort the batch or the
remaining entries. The failed call SHALL NOT be recorded as a completed call.

#### Scenario: The singular back-translation leg fails

- **WHEN** the back-translation judge call for a sentence cannot be completed
- **THEN** that entry is abstained with an unavailability reason, stays fuzzy,
  and the batch continues with the next entry

#### Scenario: A plural form's back-translation leg fails

- **WHEN** the back-translation judge call for one form of a plural entry
  cannot be completed
- **THEN** the plural entry is abstained with an unavailability reason, stays
  fuzzy, and the batch continues

#### Scenario: The failed call is not appended to the evidence

- **WHEN** a back-translation judge call fails at the transport layer
- **THEN** the entry's evidence records no completed call for that attempt

### Requirement: Qualification reports its progress live

A `qualify` run SHALL persist one state file per release, keyed so parallel
runs of different releases for the same language never collide, replacing it
atomically and recording the selection, completed count, matches so far, bare
score against the qualification tolerance, spend, rate, estimate and the
model call in flight. The file SHALL be advisory: a missing or stale file
SHALL NOT change the outcome.

#### Scenario: A qualification has made progress

- **WHEN** a `qualify` run for one release has completed some selections
- **THEN** its state file reports the completed count, matches so far and a
  bare score so an operator can see how far above the tolerance it is

#### Scenario: Two releases qualify in parallel

- **WHEN** two `qualify` runs for different releases of the same language run
  concurrently
- **THEN** each writes a distinct state file and neither overwrites the other

#### Scenario: A qualification state file is stale

- **WHEN** the recorded process is gone and the state file is old
- **THEN** `status` reports the qualification as abandoned without a
  completion estimate

### Requirement: Drift probes report their progress live

A `drift` run SHALL persist one state file per deployment, keyed so parallel
probes never collide, replacing it atomically and recording the selection,
completed count, matches so far, bare score against the drift threshold,
spend, rate, estimate and the model call in flight. The file SHALL be
advisory: a missing or stale file SHALL NOT change the outcome.

#### Scenario: A drift probe has made progress

- **WHEN** a `drift` run for one deployment has evaluated some probe items
- **THEN** its state file reports the completed count, matches so far and a
  bare score so an operator can see how far above the threshold it is

#### Scenario: Two deployments probe in parallel

- **WHEN** two `drift` runs for different deployments of the same language run
  concurrently
- **THEN** each writes a distinct state file and neither overwrites the other

#### Scenario: A drift state file is stale

- **WHEN** the recorded process is gone and the state file is old
- **THEN** `status` reports the probe as abandoned without a completion
  estimate

### Requirement: `status` reports qualification and drift records

The `status` command SHALL report live qualification and drift runs from their
state files with the same freshness and waiting/stall signals as a translate
batch, SHALL mark them as live or inferred exactly as it does for a batch, and
SHALL offer them in the JSON form without a model credential.

#### Scenario: A qualification is running

- **WHEN** `status` runs while a `qualify` for a language is in flight
- **THEN** it reports the qualification with its completed count, bare score,
  age and any waiting model call

#### Scenario: A drift probe is stalled

- **WHEN** a `drift` run has a model call in flight longer than its recent
  median
- **THEN** `status` names the waiting role and reports the probe as stalled

#### Scenario: No credential is present

- **WHEN** `status` runs with no model credential configured while a
  qualification or drift is active
- **THEN** it reports those runs and exits zero without naming a missing key
