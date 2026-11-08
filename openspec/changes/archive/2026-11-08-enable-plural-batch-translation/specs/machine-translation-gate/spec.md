# Spec Delta

## MODIFIED Requirements

### Requirement: Applying an approval writes the approved text

The gate SHALL apply an approved decision by writing the decision's
translation into the catalog entry and clearing its fuzzy flag before
recording the approval. For an entry with `msgid_plural`, it SHALL write
every plural form into `msgstr_plural` and leave `msgstr` empty. It SHALL
reject an approved decision whose translation is missing or whose form set
does not match the entry.

#### Scenario: An empty entry is filled

- **WHEN** an approved decision is applied to an entry with an empty `msgstr`
- **THEN** the catalog stores the decision's translation, the fuzzy flag is
  cleared, and the approval is recorded

#### Scenario: A decision without a translation is rejected

- **WHEN** an approved decision has no translation
- **THEN** the catalog is not changed and the approval is not recorded

#### Scenario: A fuzzy proposal is replaced

- **WHEN** an approved decision is applied to an entry that already has a
  fuzzy proposal
- **THEN** the decision's translation replaces the proposal and the fuzzy flag
  is cleared

#### Scenario: A plural form set is written

- **WHEN** an approved decision for a plural entry carries every declared form
- **THEN** the catalog stores each form in `msgstr_plural`, leaves `msgstr`
  empty, clears the fuzzy flag, and records the approval

#### Scenario: A plural form set is incomplete

- **WHEN** an approved decision for a plural entry carries fewer forms than the
  entry declares
- **THEN** the catalog is not changed and the approval is not recorded

### Requirement: Batch translation applies approved missing entries

The gate SHALL provide a `translate` command that selects missing entries for
one language, runs the gate for each, and applies each approved decision. A
missing plural translation is an entry with an empty or absent form in
`msgstr_plural`. An abstained entry SHALL remain fuzzy and SHALL be reported.

#### Scenario: Missing entries are filled

- **WHEN** a batch runs over entries with empty translations and the gate
  approves proposals
- **THEN** those translations are written, their fuzzy flags are cleared, and
  the summary counts them as approved

#### Scenario: An abstention remains fuzzy

- **WHEN** the gate abstains on a selected entry
- **THEN** the entry keeps its fuzzy flag, is left unchanged, and is reported
  as abstained

#### Scenario: Existing translations are skipped

- **WHEN** a catalog entry already has a non-fuzzy translation
- **THEN** the batch does not call the gate for it

#### Scenario: Fuzzy proposals are opt-in

- **WHEN** the batch runs without the include-fuzzy option
- **THEN** entries that already have a non-empty fuzzy proposal are skipped;
  with the option they are reconsidered

#### Scenario: A limit caps the batch

- **WHEN** a limit is supplied
- **THEN** at most that many selected entries are processed

#### Scenario: JSON output is requested

- **WHEN** the batch runs with the JSON option
- **THEN** it prints the approved, abstained and skipped entries with their
  cost

#### Scenario: A plural entry is filled

- **WHEN** a batch selects a plural entry with missing forms and the gate
  approves a complete form set
- **THEN** every form is written to `msgstr_plural`, the fuzzy flag is
  cleared, and the summary counts the entry as approved

### Requirement: Batch translation skips unsupported entries

The batch SHALL skip entries with a message context and report each skip with
a reason. It SHALL also skip a plural entry whose catalog does not declare
`nplurals`, or whose form set does not match the declared count. It SHALL
leave them unchanged. A dry run SHALL list the selected and skipped entries,
report the estimate and write nothing.

#### Scenario: A context entry is skipped

- **WHEN** a selected entry has a `msgctxt`
- **THEN** the batch reports it as unsupported and leaves it unchanged

#### Scenario: A plural entry is skipped

- **WHEN** a selected plural entry has no `nplurals` header or a form count
  that does not match the header
- **THEN** the batch reports it as unsupported and leaves it unchanged

#### Scenario: A dry run writes nothing

- **WHEN** the batch runs in dry-run mode
- **THEN** it lists the selected and skipped entries and their estimate, and
  writes no catalog or ledger change

## ADDED Requirements

### Requirement: Plural entries are translated as a form set

A plural entry SHALL be translated as one complete form set. Each proposer
SHALL return exactly the number of forms the catalog header declares, in form
order. Every form SHALL pass the deterministic checks, and the blind judge
SHALL compare complete sets. A sentence form SHALL be back-translated, and a
meaning change in any form SHALL block approval.

#### Scenario: A valid plural entry is selected

- **WHEN** a plural entry's catalog declares `nplurals` and the entry has that
  many forms
- **THEN** the batch selects the entry instead of reporting it as unsupported

#### Scenario: A proposal has the wrong form count

- **WHEN** a proposer returns more or fewer forms than the catalog declares
- **THEN** that proposal fails and cannot be approved

#### Scenario: One form fails a deterministic check

- **WHEN** any form of a passing proposal changes a placeholder or format field
- **THEN** the whole proposal fails and cannot be approved

#### Scenario: The judge compares complete sets

- **WHEN** the passing proposals differ in any form
- **THEN** the blind judge receives each proposal as a complete ordered set and
  chooses one set

#### Scenario: Identical form sets are a tie

- **WHEN** every passing proposal has the same form tuple and at least two
  independent families proposed it
- **THEN** the gate approves without a judge call and records the tie

#### Scenario: A sentence form changes meaning

- **WHEN** any sentence form back-translates to a meaning that differs from
  its source
- **THEN** the whole form set is not approved
