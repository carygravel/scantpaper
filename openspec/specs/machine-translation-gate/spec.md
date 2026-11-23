# machine-translation-gate

## Purpose

Defines the evidence-based gate that decides whether a machine-produced
translation may ship, and how that approval is recorded, audited and revoked.

## Requirements

### Requirement: Proposals come from independent model families

The gate SHALL obtain at least two proposals from different model families and
SHALL judge them with a family that produced neither. Two deployments of the
same release are one family, however many providers serve it. The judge SHALL
see the source, the proposals and the deterministic check results without
being told which family produced which. A run that cannot satisfy this
separation SHALL produce no approval.

#### Scenario: Independent proposals are judged blindly

- **WHEN** two different model families propose a translation and a third
  family judges both
- **THEN** the verdict is recorded with the proposal and judge families, and
  neither proposal is identified to the judge by family

#### Scenario: Only one family is available

- **WHEN** the gate can obtain a proposal from only one model family
- **THEN** it approves nothing and leaves the string fuzzy

#### Scenario: Two providers serve one release

- **WHEN** the gate is offered two deployments of the same release as its two
  proposers
- **THEN** they count as one family and no approval is produced

### Requirement: Approval requires deterministic and semantic evidence

The gate SHALL approve a string only when every deterministic check passes
for the source and the translation and the semantic evidence agrees. Semantic
evidence SHALL include either a blind judge verdict or, when every passing
proposal has the same text and at least two independent families proposed it,
the agreement of those families. For a sentence, a back-translation that
preserves meaning SHALL still be required. A failing or missing piece of
evidence SHALL block approval.

#### Scenario: All evidence agrees

- **WHEN** both proposals pass the deterministic checks, the judge prefers one
  of them, and any back-translation preserves meaning
- **THEN** the string is approved and every piece of evidence is recorded

#### Scenario: Identical proposals are a tie

- **WHEN** every passing proposal has the same text, at least two independent
  families proposed it, and every deterministic check passes
- **THEN** the gate approves without a judge call, records the tie as the
  semantic verdict, and still back-translates a sentence

#### Scenario: Differing proposals are judged

- **WHEN** the passing proposals do not all have the same text
- **THEN** the gate calls the blind judge before approving

#### Scenario: A placeholder check fails

- **WHEN** the preferred proposal fails a placeholder, plural, markup or
  render check even though the judge prefers it or the proposals tie
- **THEN** the string is not approved

#### Scenario: Back-translation changes meaning

- **WHEN** a sentence proposal back-translates to a meaning that differs from
  the source
- **THEN** the string is not approved

### Requirement: Abstention is a valid outcome

A string that does not clear the gate SHALL remain fuzzy and fall back to
English. The gate SHALL report the string as abstained with a reason, and
SHALL NOT clear the fuzzy flag to improve a coverage number.

#### Scenario: The gate abstains

- **WHEN** a proposal fails any required evidence
- **THEN** the entry stays fuzzy, the reason is reported, and users see the
  English source text

#### Scenario: Evidence is unavailable

- **WHEN** a model, judge or translation-memory lookup cannot be completed
- **THEN** the string is reported as abstained rather than approved

### Requirement: Every approval records a provenance class

The approval ledger SHALL record exactly one provenance class for each
approved string: `human-historical`, `human-review`, `in-project-rebase`,
`tm-consensus`, `machine-strong` or `machine-weak`. It SHALL also record the
language, context, msgid, msgstr, an evidence digest and compact evidence
summary, model release, deployment and approval date. The full evidence SHALL
be stored in a content-addressed evidence store.

#### Scenario: A machine approval records its class and evidence

- **WHEN** the gate approves a string as `machine-strong`
- **THEN** the approval contains the class, an evidence digest and summary,
  and the full proposals, judge verdict and check results are retrievable
  from the evidence store by that digest

#### Scenario: Evidence remains retrievable

- **WHEN** an audit resolves an approval's evidence digest
- **THEN** it reads the full evidence from the store, or reports the evidence
  as unavailable when the store is absent, without invalidating the approval

#### Scenario: An unknown class is rejected

- **WHEN** a ledger entry names a provenance class outside the six defined
  classes
- **THEN** validation rejects the entry rather than treating it as approved

### Requirement: An approval is bound to its exact text

An approval SHALL be valid only for the language, context, msgid and msgstr
it was recorded for. A change to any of them SHALL invalidate the approval, so
the string returns to fuzzy until it is approved again.

#### Scenario: The translation is edited

- **WHEN** an approved entry's msgstr is edited
- **THEN** its approval no longer applies and the entry is not shipped until
  it is approved again

#### Scenario: The source string changes

- **WHEN** an approved entry's msgid changes
- **THEN** its approval no longer applies, even if the msgstr is unchanged

### Requirement: Machine approvals are provisional and revocable

Machine-origin approvals SHALL be revocable by language, by deployment or by
model release without editing every catalog. Revoking a deployment SHALL
demote only the approvals it produced; revoking a release SHALL demote
approvals from every deployment of that release. Revocation SHALL take effect
at the next build and SHALL be recorded in the ledger.

#### Scenario: A language is revoked

- **WHEN** machine approvals for one language are revoked
- **THEN** only that language's machine-approved strings fall back to English
  at the next build

#### Scenario: A deployment is revoked

- **WHEN** approvals produced by one provider deployment are revoked
- **THEN** only that deployment's approvals are demoted and other deployments
  of the same release keep theirs

#### Scenario: A release is revoked

- **WHEN** approvals from one model release are revoked
- **THEN** every approval from every deployment of that release is demoted

### Requirement: Model identity has a release and a deployment

A model SHALL be identified by a release (family, model id and revision) and
by a deployment (provider, endpoint, quantization, prompt template and
decoding configuration). A qualification SHALL attach to a release and a
language. An approval SHALL record both the release and the deployment that
produced it.

#### Scenario: A deployment changes its configuration

- **WHEN** a provider changes the quantization, prompt template or decoding
  configuration of a deployment
- **THEN** it becomes a different deployment and does not retain the earlier
  conformance

#### Scenario: The same release is served elsewhere

- **WHEN** two providers serve the same release identity
- **THEN** they are two deployments of one release for qualification and
  independence purposes

### Requirement: Models are qualified per language and release

A model release SHALL propose or judge for a language only after it reproduces
held-out entries from that language's reviewed catalog within a recorded
tolerance. A language with no qualified release SHALL receive no machine
approval and SHALL stay on English fallback.

#### Scenario: A release passes the held-out baseline

- **WHEN** a model release reproduces the held-out reviewed entries for a
  language within the configured tolerance
- **THEN** it becomes eligible to propose or judge for that language

#### Scenario: A different release needs its own qualification

- **WHEN** a new release or a fine-tune is offered for a language
- **THEN** it does not inherit the earlier release's qualification

#### Scenario: No baseline exists

- **WHEN** a language has no reviewed entries to form a held-out baseline
- **THEN** no release is qualified for it and its strings stay English

### Requirement: A deployment inherits a release qualification after conformance

A deployment of an already-qualified release SHALL inherit the release's
qualification only after its serving configuration is declared equivalent and
it passes a conformance probe against the release's drift baseline. A
deployment that fails conformance SHALL require full qualification. A model
that is merely similar to a qualified release SHALL NOT inherit.

#### Scenario: A second provider passes conformance

- **WHEN** a new deployment declares an exact release identity, equivalent
  serving configuration and a probe score within tolerance
- **THEN** it inherits the release's qualification for every qualified
  language without a second full qualification

#### Scenario: A deployment fails conformance

- **WHEN** a new deployment's conformance probe falls outside tolerance
- **THEN** it does not inherit and must qualify on its own

#### Scenario: A similar model is not the same release

- **WHEN** a candidate model cannot be tied to the qualified release's
  identity
- **THEN** it is treated as a different model and full qualification is
  required

### Requirement: Model drift is detected by a fixed probe

A versioned set of human-translated strings SHALL be re-run against a
qualified model before a batch. A score below the configured drift threshold
SHALL pause new approvals for that release and language, trigger
re-qualification, and mark approvals produced since the last good probe for
audit. The probe SHALL NOT demote existing approvals by itself.

#### Scenario: A probe detects drift

- **WHEN** a model's probe score falls below the configured threshold
- **THEN** new approvals for that release and language pause, and approvals
  from the affected window are queued for audit

#### Scenario: Drift is not confirmed

- **WHEN** re-qualification and the audit find no defect
- **THEN** approvals resume and the existing translations remain shipped

### Requirement: Retiring a model does not invalidate its approvals

Removing a release or deployment from the configuration SHALL NOT demote the
approvals it produced. Its approvals SHALL remain shipped and auditable, and
the retirement SHALL be reported as a loss of future translation capacity for
the affected languages.

#### Scenario: A release is retired

- **WHEN** a release is removed from the configuration
- **THEN** its existing approvals remain shipped and only future strings are
  affected

#### Scenario: Retirement is reported

- **WHEN** the capability report runs after a retirement
- **THEN** it names the languages that no longer have a qualified release

### Requirement: A capability report names languages without a machine path

The gate SHALL report, per language, which releases and deployments are
currently qualified for future work. It SHALL name every language with no
qualified release, so the maintainer can see where new strings will stay in
English until a human or a replacement model is available.

#### Scenario: A language has no qualified release

- **WHEN** the capability report runs for a language with no qualified release
- **THEN** it names that language as having no machine path without flagging
  its existing translations

#### Scenario: A language has multiple qualified deployments

- **WHEN** two deployments of a qualified release are available for a language
- **THEN** the report lists both and the gate may use either

### Requirement: High-impact strings need strong evidence

Menu actions, destructive verbs and data-loss error messages SHALL ship only
with human-origin evidence or a `machine-strong` approval. Human-origin
evidence is an unchanged pre-2026 translation, a mechanical rebase of one, a
dominant cross-project match, or English/German review. Without it the string
SHALL remain English.

#### Scenario: An unchanged pre-2026 translation ships

- **WHEN** a high-impact string still carries its unchanged pre-2026
  Launchpad translation
- **THEN** it ships as `human-historical` without a new reviewer

#### Scenario: No evidence exists

- **WHEN** a high-impact string is new and no evidence source covers it
- **THEN** it stays English unless the strict machine gate approves it

#### Scenario: The strict gate approves provisionally

- **WHEN** the strict gate approves a high-impact string as `machine-strong`
- **THEN** the string ships provisionally and can be demoted through the
  user-report kill switch

### Requirement: In-project mechanical rebase is limited

A translation may be rebased from an existing human translation in the same
project only when the change is limited to a keyboard mnemonic, a placeholder,
punctuation or whitespace. A rebase that changes translated words SHALL
require the full gate.

#### Scenario: A mnemonic-only change is rebased

- **WHEN** a new msgid differs from a human-translated msgid only by the
  keyboard mnemonic and the checks pass
- **THEN** the existing translation is approved as `in-project-rebase`

#### Scenario: A word change is not a rebase

- **WHEN** a new msgid changes a translated word rather than only its mnemonic
  or placeholder
- **THEN** the existing translation is not reused and the string requires the
  full gate

### Requirement: Cross-project translation memory is evidence, not permission

A cross-project translation-memory match SHALL contribute evidence to the
gate but SHALL NOT approve a string by itself. The gate SHALL require a
dominant match and the remaining evidence, because dominant matches disagree
with this project's human translations in 25-35% of cases.

#### Scenario: A dominant match alone is insufficient

- **WHEN** the translation memory has one dominant translation for a string
  but the remaining gate evidence is absent
- **THEN** the string is not approved from the match alone

#### Scenario: A dominant match completes the evidence

- **WHEN** a dominant translation-memory match is combined with passing
  deterministic checks and the required semantic evidence
- **THEN** the string may be approved as `tm-consensus`

### Requirement: Translation-memory entries record provenance and licence

The translation-memory index SHALL record each entry's project, language and
licence, and SHALL exclude a catalog whose licence is incompatible with
GPL-3.0-only. Individual Launchpad string translations are BSD, but a
project-group derivative work stays under that project's licence.

#### Scenario: An incompatible catalog is excluded

- **WHEN** a candidate catalog is licensed GPL-2.0-only
- **THEN** it is not indexed as evidence for this GPL-3.0-only project

#### Scenario: A compatible catalog is indexed

- **WHEN** a candidate catalog is GPL-3.0-or-later or BSD
- **THEN** it is indexed with its project, language and licence recorded

### Requirement: The frozen human core is imported and audited

The pre-2026 Launchpad snapshot SHALL be imported as `human-historical`.
Entries the 2026 work added or changed SHALL NOT be imported as historical:
changed entries SHALL be compared with the old human text, and added entries
SHALL pass the gate before either is grandfathered.

#### Scenario: An unchanged pre-2026 entry is imported

- **WHEN** a shipped entry matches the pre-2026 snapshot exactly
- **THEN** it is imported as `human-historical`

#### Scenario: A model-changed entry is not grandfathered

- **WHEN** the 2026 work changed a pre-2026 entry
- **THEN** the entry is audited against the old human text before it receives
  a historical approval

### Requirement: Human corrections demote a language

A human correction of a machine-approved string SHALL be recorded as a false
positive. When a language's measured defect rate exceeds the configured
threshold, its machine approvals SHALL be demoted and the language rebuilt
with English fallback.

#### Scenario: A correction is recorded

- **WHEN** a human replaces a machine-approved translation
- **THEN** the ledger records a false positive for that approval's class,
  release and deployment

#### Scenario: The defect threshold is exceeded

- **WHEN** a language's measured defect rate exceeds the configured threshold
- **THEN** its machine approvals are demoted and affected strings fall back to
  English

### Requirement: A sample estimates the real error rate

The gate SHALL support a random native sample of machine-approved strings and
SHALL report the estimated error rate per language and provenance class. A
sample result SHALL NOT silently clear or approve strings.

#### Scenario: A sample is reported

- **WHEN** a random sample of a language's machine-approved strings is
  reviewed
- **THEN** the estimated error rate is reported for that language and class
  without changing any approval

### Requirement: Gate credentials never enter CI

Model calls and Launchpad authentication SHALL be maintainer-run. CI SHALL
run only deterministic checks and SHALL NOT require a model credential or an
OAuth token. Credentials SHALL come from the environment or a local credential
store, never from the repository.

#### Scenario: CI runs without credentials

- **WHEN** CI runs the translation checks in an environment with no model
  credential and no Launchpad token
- **THEN** the deterministic checks run and pass or fail on their own results

#### Scenario: A sync has no token

- **WHEN** an optional Launchpad sync is asked to run without a stored token
- **THEN** it reports that it is unauthenticated and does not fail the build

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

### Requirement: Drift probes are runnable from the command line

The gate SHALL provide a `drift` command that runs the fixed probe for one
configured deployment and language, infers the release from the deployment,
estimates the action and enforces an optional budget before any model call,
and records a paused excursion when the score is below the drift threshold.

#### Scenario: A probe passes

- **WHEN** the probe score meets or exceeds the configured drift threshold
- **THEN** it reports the score, threshold, call count and cost, records no
  pause, and exits successfully

#### Scenario: A probe detects drift

- **WHEN** the probe score is below the configured drift threshold
- **THEN** it records a paused excursion for the release, deployment and
  language with the score, cost and audit-window start, leaves existing
  approvals untouched, and exits successfully

#### Scenario: The audit window start is recorded

- **WHEN** a pause is recorded
- **THEN** the ledger stores the supplied audit-window start, or the run date
  when none is given

#### Scenario: The default probe is used

- **WHEN** the command runs without an explicit probe path
- **THEN** it reads `po/drift-probe/<language>.json`

#### Scenario: The probe is run without recording

- **WHEN** the command runs in dry-run mode
- **THEN** it reports the score and writes nothing to the ledger

#### Scenario: The deployment or probe is invalid

- **WHEN** the deployment is not configured or the probe file cannot be read
- **THEN** it reports the error, writes no pause and exits non-zero

#### Scenario: The budget is exceeded

- **WHEN** the estimated cost exceeds the optional budget
- **THEN** it makes no model call, writes no pause and exits non-zero

#### Scenario: A credential is missing

- **WHEN** the deployment's key environment variable is unset
- **THEN** it reports the variable name, writes no pause and exits non-zero

#### Scenario: JSON output is requested

- **WHEN** the command is run with the JSON option
- **THEN** it prints the probe result as JSON

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
