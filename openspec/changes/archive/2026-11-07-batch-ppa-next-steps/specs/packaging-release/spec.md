# Spec Delta

## ADDED Requirements

### Requirement: PPA next steps are printed together

The PPA tool SHALL collect the next-step commands for every selected series
as it goes and SHALL print them in a single `Next steps:` block after
processing, in selection order. A series that fails SHALL be omitted, while
series that finished before it SHALL keep their commands.

#### Scenario: Several series produce one block

- **WHEN** the PPA tool processes several selected series successfully
- **THEN** it prints one `Next steps:` block after the last series' progress
  line, with one `dput` command per series in selection order

#### Scenario: Earlier series keep their commands after a failure

- **WHEN** a later selected series fails after earlier series have built
- **THEN** the tool still prints the block with the earlier series' `dput`
  commands, omits the failed series, and exits non-zero

#### Scenario: No series finishes

- **WHEN** the first selected series fails
- **THEN** no `Next steps:` block is printed

#### Scenario: Dry run prints the same block

- **WHEN** the PPA tool runs with `--dry-run`
- **THEN** it prints the same single block using the predicted `.changes`
  paths
