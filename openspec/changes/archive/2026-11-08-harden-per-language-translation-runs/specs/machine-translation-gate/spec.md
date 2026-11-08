# Spec Delta

## ADDED Requirements

### Requirement: Deterministic checks preserve the source line structure

The deterministic checks SHALL reject a translation whose leading or trailing
newline run differs from its source. A translation SHALL keep the same number
of leading newlines and the same number of trailing newlines as the source, so
text assembled around it keeps its layout and `msgfmt --check` does not fail.

#### Scenario: A trailing newline is dropped

- **WHEN** the source ends with a newline and the selected proposal does not
- **THEN** the string is not approved and the reason names the changed trailing
  newline

#### Scenario: A leading newline is added

- **WHEN** the source does not start with a newline and the selected proposal
  starts with one
- **THEN** the string is not approved

#### Scenario: The line structure is preserved

- **WHEN** the translation keeps the source's leading and trailing newline runs
- **THEN** this check reports no defect and the other deterministic checks
  decide the proposal

### Requirement: A scoped human-core audit preserves the whole report

When the human-core audit runs for a subset of languages, it SHALL update only
those languages. It SHALL merge each selected language's block, pending entries
and parked entries into the existing report, recompute the aggregate totals and
notes, and write only the selected languages' ledger files.

#### Scenario: A scoped run updates the selected block

- **WHEN** the audit runs with one language and writes the report
- **THEN** that language's block and pending entries are replaced, the totals
  and notes reflect the merge, and every other language is unchanged

#### Scenario: A scoped run leaves other ledgers untouched

- **WHEN** the audit runs with one language and writes the ledger
- **THEN** only that language's ledger file changes, and an unrelated language's
  file stays byte for byte identical

#### Scenario: A missing report is created

- **WHEN** the audit runs with one language and no report exists yet
- **THEN** the report is created from that language alone
