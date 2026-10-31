# Spec Delta

## Purpose

Defines which page count the scan dialog selects when the scan source
changes, so that switching from an ADF to a flatbed never silently creates
an unbounded flatbed batch.

## ADDED Requirements

### Requirement: Flatbed source defaults to a finite page count

When the scan source changes to a flatbed, the dialog SHALL select one page
unless the user has explicitly selected `All` or a finite count while the
flatbed is the current source. A page count inherited from the ADF default
or from a saved profile SHALL NOT select `All` on a flatbed.

#### Scenario: ADF All does not follow the source to Flatbed

- **WHEN** the ADF default has selected `All` and the user changes the
  source to Flatbed
- **THEN** `# Pages` SHALL be one page
- **AND** the batch SHALL stop after one page unless the user chooses
  another count

#### Scenario: Saved profile All is refused on Flatbed

- **WHEN** a saved default scan-options value or profile containing an
  unbounded page count is applied while Flatbed is the selected source
- **THEN** `# Pages` SHALL remain one page

#### Scenario: Re-entering Flatbed starts from one page

- **WHEN** the user chooses a count on Flatbed, switches the source away,
  and then selects Flatbed again
- **THEN** `# Pages` SHALL be one page
- **AND** the previous flatbed count SHALL NOT be inherited

#### Scenario: Batch flatbed enabled still starts at one page

- **WHEN** "Allow batch scanning from flatbed" is enabled and the user
  changes the source to Flatbed
- **THEN** `# Pages` SHALL be one page
- **AND** the `# Pages` frame SHALL be sensitive so the user can choose a
  multi-page count

#### Scenario: Batch flatbed disabled ghosts the frame

- **WHEN** "Allow batch scanning from flatbed" is disabled and the user
  changes the source to Flatbed
- **THEN** `# Pages` SHALL be one page
- **AND** the `# Pages` frame SHALL be insensitive

### Requirement: Explicit unbounded flatbed batch is identified

When the user selects `All` while Flatbed is the current source, the dialog
SHALL identify the batch as unbounded before scanning starts, so that
scanning until Cancel is a deliberate choice.

#### Scenario: All on Flatbed shows the unbounded indication

- **WHEN** the user selects `All` while Flatbed is the current source
- **THEN** the dialog SHALL show that the batch has no page limit and
  continues until the user cancels
- **AND** the indication SHALL be visible before the user starts the scan

#### Scenario: Finite count clears the unbounded indication

- **WHEN** the user changes from `All` to a finite count on Flatbed
- **THEN** the unbounded indication SHALL be hidden

#### Scenario: All on ADF is not an unbounded flatbed batch

- **WHEN** the user selects `All` while an ADF is the current source
- **THEN** the dialog SHALL NOT show the unbounded-flatbed indication
- **AND** the batch SHALL end when the feeder reports no more documents

### Requirement: ADF default remains All

When the source changes to an ADF and the ADF default preference is
enabled, the dialog SHALL select `All`, preserving the existing
feeder-batch behaviour.

#### Scenario: Flatbed to ADF selects All

- **WHEN** `# Pages` is one page on Flatbed and the user changes the
  source to an ADF with the ADF default enabled
- **THEN** `# Pages` SHALL be `All`
