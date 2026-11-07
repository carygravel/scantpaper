# Spec Delta

## ADDED Requirements

### Requirement: Applying an approval writes the approved text

The gate SHALL apply an approved decision by writing the decision's
translation into the catalog entry and clearing its fuzzy flag before
recording the approval. It SHALL reject an approved decision whose
translation is missing.

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

### Requirement: Batch translation applies approved missing entries

The gate SHALL provide a `translate` command that selects missing entries for
one language, runs the gate for each, and applies each approved decision. An
abstained entry SHALL remain fuzzy and SHALL be reported.

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

### Requirement: Batch translation refuses an unqualified or paused language

The batch SHALL refuse to run when any proposer or judge release is not
qualified for the language, or when a release is paused for drift. It SHALL
name the missing qualification or pause and make no model call.

#### Scenario: An unqualified release blocks the batch

- **WHEN** a proposer or judge release has no qualified record for the
  language
- **THEN** the batch reports the release and language, makes no call and exits
  non-zero

#### Scenario: A paused language blocks the batch

- **WHEN** a drift excursion for the release and language is paused
- **THEN** the batch reports the pause, makes no call and exits non-zero

#### Scenario: A qualified, unpaused path proceeds

- **WHEN** every role release is qualified for the language and no pause exists
- **THEN** the batch proceeds

#### Scenario: A dry run reports the blockers

- **WHEN** a dry run encounters an unqualified or paused path
- **THEN** it reports the blocker without calling a model or writing a catalog

### Requirement: Batch translation honors a total budget

The batch SHALL estimate the selected entries before any model call and refuse
a run whose high estimate exceeds the optional total budget. It SHALL stop
before an entry whose high estimate would exceed the remaining budget.

#### Scenario: The estimate exceeds the budget

- **WHEN** the high estimate for the selected batch exceeds the total budget
- **THEN** no model call is made, no catalog or ledger write occurs, and the
  command exits non-zero

#### Scenario: The budget is reached mid-run

- **WHEN** accumulated spend plus the next entry's high estimate exceeds the
  budget
- **THEN** the batch stops before that entry, reports its progress, and leaves
  the remaining entries fuzzy

#### Scenario: No budget is supplied

- **WHEN** the batch runs without a total budget
- **THEN** it proceeds without a cap

### Requirement: Batch translation skips unsupported entries

The batch SHALL skip entries with plural forms or a message context and report
each skip with a reason. It SHALL leave them unchanged. A dry run SHALL list
the selected and skipped entries, report the estimate and write nothing.

#### Scenario: A plural entry is skipped

- **WHEN** a selected entry has a `msgid_plural`
- **THEN** the batch reports it as unsupported and leaves it unchanged

#### Scenario: A context entry is skipped

- **WHEN** a selected entry has a `msgctxt`
- **THEN** the batch reports it as unsupported and leaves it unchanged

#### Scenario: A dry run writes nothing

- **WHEN** the batch runs in dry-run mode
- **THEN** it lists the selected and skipped entries and their estimate, and
  writes no catalog or ledger change
