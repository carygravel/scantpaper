# change-lifecycle Specification

## Purpose

Keeps the OpenSpec change tree valid and current: every active change
validates in strict mode, a change whose tasks are all ticked is archived
rather than left active, and archiving leaves the main specs strict-valid.

## Requirements

### Requirement: Every active change is validated strictly

A push SHALL validate every change under `openspec/changes/` in strict mode,
and SHALL fail when any change reports a strict-mode finding. A change that is
strict-valid SHALL not affect the result.

#### Scenario: An over-long requirement fails the push

- **WHEN** an active change modifies or adds a requirement whose description
  exceeds the length the validator accepts
- **THEN** the validation SHALL fail
- **AND** the failure SHALL name the offending change

#### Scenario: A change with no delta fails the push

- **WHEN** an active change declares a capability but contains no delta
- **THEN** the validation SHALL fail

#### Scenario: Valid active changes leave the push green

- **WHEN** every active change is strict-valid
- **THEN** the validation SHALL pass

### Requirement: A completed change is archived before it is pushed

A push SHALL fail when a change whose tasks are all ticked is still under
`openspec/changes/`, naming each such change. A change with at least one
unticked task SHALL remain allowed to be active, and a newly created change
with no tasks SHALL NOT be reported as complete.

#### Scenario: Every task ticked but not archived

- **WHEN** a change has every task ticked and is still under
  `openspec/changes/`
- **THEN** the push SHALL fail
- **AND** the failure SHALL name that change

#### Scenario: Several completed changes are reported together

- **WHEN** more than one completed change is still active
- **THEN** the failure SHALL name every one of them

#### Scenario: An open task keeps a change active

- **WHEN** a change has at least one unticked task
- **THEN** the gate SHALL NOT fail because of that change

#### Scenario: A change with no tasks is not complete

- **WHEN** a change has no tasks recorded yet
- **THEN** the gate SHALL NOT treat it as a completed change

### Requirement: Archiving leaves the main specs strict-valid

A push that archives one or more changes SHALL validate the main specs in
strict mode after their deltas are applied, so a delta that would leave a spec
invalid fails the push instead of landing a build that fails on the next
change.

#### Scenario: An archived delta exceeds the requirement length

- **WHEN** archiving a change would push a main-spec requirement past the
  accepted length
- **THEN** the main-spec validation SHALL fail
- **AND** the change SHALL be split into requirements that each state one
  behaviour before it is archived

#### Scenario: Archived deltas leave the specs valid

- **WHEN** every archived delta leaves its main spec strict-valid
- **THEN** the main-spec validation SHALL pass
