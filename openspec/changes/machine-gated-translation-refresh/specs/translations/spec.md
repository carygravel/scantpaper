# Spec Delta

## MODIFIED Requirements

### Requirement: Only non-fuzzy translations ship

Release builds SHALL include only non-fuzzy translations that carry a valid
approval in the translation ledger. Fuzzy entries SHALL never be compiled into
a released catalog, and a non-fuzzy entry without a valid approval SHALL fall
back to English.

#### Scenario: Release with fuzzy entries present

- **WHEN** a release is built while a catalog still contains fuzzy entries
- **THEN** the release is built successfully with those messages falling back
  to English, and the release is not blocked by the fuzzy entries

#### Scenario: Fuzzy entries never appear in released output

- **WHEN** a released catalog is inspected for a message that is fuzzy in the
  source catalog
- **THEN** the fuzzy translation is absent from the released output and the
  English fallback is used instead

#### Scenario: An unapproved non-fuzzy entry falls back

- **WHEN** a catalog contains a non-fuzzy translation with no valid ledger
  approval
- **THEN** the release uses the English source text for that message

### Requirement: Missing translations may be added as fuzzy

Missing translations SHALL be added as `#, fuzzy` proposals. A fuzzy entry
SHALL become shipped only when a human clears it or the machine gate approves
it under the standing policy; an unreviewed entry SHALL continue to fall back
to English.

#### Scenario: Translator confirms a fuzzy string

- **WHEN** a human translator reviews a fuzzy entry and clears its fuzzy flag
- **THEN** the entry becomes a shipped translation for the next release

#### Scenario: The machine gate approves a fuzzy string

- **WHEN** the machine gate approves a fuzzy entry under the policy
- **THEN** the entry becomes a shipped translation for the next release and
  the approval is recorded in the ledger

#### Scenario: Fuzzy entry remains unreviewed

- **WHEN** a fuzzy entry has been neither reviewed by a human nor approved by
  the machine gate
- **THEN** it continues to fall back to English and is excluded from releases

### Requirement: Translation updates flow through Rosetta

Rosetta SHALL remain a supported source of translations, but it SHALL NOT be
required for a release. A sync MAY use a locally authorized read-only
Launchpad credential to request one-off catalog exports; it SHALL NOT be a CI
dependency, and a release SHALL proceed when no sync has run.

#### Scenario: Translated catalog downloaded from Rosetta

- **WHEN** an authorized sync downloads translated `.po` files from Rosetta
  before a release
- **THEN** the confirmed translations are included in the release and
  unreviewed fuzzy entries continue to fall back to English

#### Scenario: No Rosetta sync has run

- **WHEN** a release is cut without a Launchpad export
- **THEN** the release uses the catalogs already in the repository and is not
  blocked by the missing sync

#### Scenario: CI does not authenticate

- **WHEN** CI runs any translation check
- **THEN** it sends no Launchpad credential and downloads no catalog

## ADDED Requirements

### Requirement: Coverage is measured against the current template

Coverage reports SHALL compare each catalog with the current `.pot` and SHALL
report shipped, fuzzy, missing, stale and obsolete entries per language. The
denominator SHALL be the current source, not the catalog's own entry count.

#### Scenario: A catalog behind the template reports real coverage

- **WHEN** a catalog has 558 entries of which 549 are shipped while the
  template has 665 msgids
- **THEN** the report gives the coverage as 549 of 665, not 549 of 558

#### Scenario: Missing and stale entries are distinguished

- **WHEN** a catalog lacks a template msgid and also contains an entry whose
  msgid is no longer in the template
- **THEN** the report counts the first as missing and the second as stale

### Requirement: Merge is deterministic and records the previous msgid

A maintained command SHALL regenerate the template and update every catalog
in one deterministic step. For every changed entry it SHALL record the
previous msgid, and it SHALL NOT silently adopt a `msgmerge` fuzzy match as a
translation. A refresh SHALL be reviewable as a single diff.

#### Scenario: A changed entry keeps its previous msgid

- **WHEN** the template changes the msgid of an entry that has a translation
- **THEN** the merge records the previous msgid beside the new entry

#### Scenario: A msgmerge fuzzy match is not adopted

- **WHEN** `msgmerge` proposes a fuzzy match for a new msgid
- **THEN** the merge leaves the entry fuzzy and does not clear it

### Requirement: Fuzzy proposals are validated as if shipped

Every fuzzy entry SHALL receive the same placeholder, plural, markup and
render checks as a non-fuzzy entry. A test-only compiled catalog SHALL format
every message with generated arguments so that a Python `%` error is caught
before the entry can be approved.

#### Scenario: A fuzzy entry carries a runtime fault

- **WHEN** a fuzzy entry's msgstr would raise a `TypeError` or `ValueError`
  when formatted with its source arguments
- **THEN** validation fails and the entry cannot be approved

#### Scenario: A fuzzy entry passes every check

- **WHEN** a fuzzy entry passes the placeholder, plural, markup and render
  checks
- **THEN** the entry remains eligible for human or machine approval

### Requirement: Translator context travels with the template

The template SHALL carry `TRANSLATORS:` comments, widget and action context,
and a glossary so that short labels such as `Select` or `Pan` are unambiguous
to a human or a model.

#### Scenario: A short label carries context

- **WHEN** the template contains a short label such as `Pan`
- **THEN** its entry names the widget, the action and the intended meaning

### Requirement: Release reports real coverage and English fallbacks

A release build SHALL report per-language coverage against the current
template and the number of messages that fall back to English. It SHALL NOT
report a catalog's own entry count as coverage.

#### Scenario: Release reports fallbacks

- **WHEN** a release is built for a language with missing or unapproved
  entries
- **THEN** the report names the language's coverage against the template and
  the count of English fallbacks

### Requirement: The pre-2026 snapshot is preserved as the human reference

The merge and audit tooling SHALL preserve the pre-2026 Launchpad snapshot as
a read-only human reference, and SHALL NOT overwrite it when catalogs are
refreshed.

#### Scenario: A refresh leaves the snapshot intact

- **WHEN** the catalogs are merged after a template change
- **THEN** the pre-2026 snapshot is unchanged and still available to the
  approval audit
