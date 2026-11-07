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
evidence SHALL include a blind judge verdict and, for sentences, a
back-translation that preserves meaning. A failing or missing piece of
evidence SHALL block approval.

#### Scenario: All evidence agrees

- **WHEN** both proposals pass the deterministic checks, the judge prefers one
  of them, and any back-translation preserves meaning
- **THEN** the string is approved and every piece of evidence is recorded

#### Scenario: A placeholder check fails

- **WHEN** the preferred proposal fails a placeholder, plural, markup or
  render check even though the judge prefers it
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
language, context, msgid, msgstr, evidence, model release, deployment and
approval date.

#### Scenario: A machine approval records its class and evidence

- **WHEN** the gate approves a string as `machine-strong`
- **THEN** the ledger contains the class, both proposals, the judge verdict,
  the check results, and the release and deployment used

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
