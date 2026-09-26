# translations

## Purpose

Defines how scantpaper's translations are produced, marked, and shipped:
fuzzy-marked translations are treated as untranslated until a human confirms
them, and only non-fuzzy translations reach end users.

## Requirements

### Requirement: Fuzzy translations fall back to English
The system SHALL treat a `#, fuzzy` translation as untranslated, so users see
the English source string for that message until the fuzzy flag is cleared.

#### Scenario: Fuzzy string is displayed to user
- **WHEN** a catalog contains a `#, fuzzy` entry for a message and the user
  runs the application in that language
- **THEN** the user sees the English source text for that message, not the
  fuzzy translation

#### Scenario: Non-fuzzy translation is displayed to user
- **WHEN** a catalog contains a non-fuzzy entry for a message and the user
  runs the application in that language
- **THEN** the user sees the translated text for that message

### Requirement: Only non-fuzzy translations ship
Release builds SHALL include only non-fuzzy translations; fuzzy entries SHALL
never be compiled into a released catalog.

#### Scenario: Release with fuzzy entries present
- **WHEN** a release is built while a catalog still contains fuzzy entries
- **THEN** the release is built successfully with those messages falling back
  to English, and the release is not blocked by the fuzzy entries

#### Scenario: Fuzzy entries never appear in released output
- **WHEN** a released catalog is inspected for a message that is fuzzy in the
  source catalog
- **THEN** the fuzzy translation is absent from the released output and the
  English fallback is used instead

### Requirement: Missing translations may be added as fuzzy
The translation workflow SHALL allow missing strings to be translated and
marked `#, fuzzy` (needing review) rather than left untranslated.

#### Scenario: Translator confirms a fuzzy string
- **WHEN** a human translator reviews a fuzzy entry and clears its fuzzy flag
- **THEN** the entry becomes a shipped translation for the next release

#### Scenario: Fuzzy entry remains unreviewed
- **WHEN** a fuzzy entry has not been reviewed by a translator
- **THEN** it continues to fall back to English and is excluded from releases

### Requirement: Translation updates flow through Rosetta
The system SHALL continue to use the Rosetta (Launchpad) workflow to download
translated catalogs and receive cleared (non-fuzzy) translations before a
release.

#### Scenario: Translated catalog downloaded from Rosetta
- **WHEN** translated `.po` files are downloaded from Rosetta before a release
- **THEN** the confirmed translations are included in the release and
  unreviewed fuzzy entries continue to fall back to English

### Requirement: Translation catalogs are mechanically validated
The system SHALL validate every translation catalog mechanically before it
is accepted: each `po/*.po` SHALL pass `msgfmt --check` (format-specifier
consistency between `msgid` and `msgstr`, escape-sequence correctness, and
plural-entry counts) and SHALL declare a `Plural-Forms` header that matches
the CLDR plural rules for its language (e.g. `nplurals=3` for
ru/uk/pl/be/sr/cs/sk, `nplurals=4` for sl, `nplurals=6` for ar). The check
SHALL run in CI and fail the build on any violation.

#### Scenario: Catalog with placeholder drift is rejected
- **WHEN** a catalog contains a translated string whose format specifiers
  do not match its source string
- **THEN** the mechanical validation fails and CI fails the build

#### Scenario: Catalog with wrong plural forms is rejected
- **WHEN** a catalog declares a `Plural-Forms` header that does not match
  the CLDR plural rules for its language
- **THEN** the mechanical validation fails and CI fails the build

#### Scenario: Valid catalog passes
- **WHEN** a catalog passes `msgfmt --check` and declares the correct
  `Plural-Forms` header for its language
- **THEN** the mechanical validation succeeds

### Requirement: Malformed format placeholders fail catalog validation
The mechanical catalog validation SHALL reject entries whose translated
text contains a malformed format placeholder, for both placeholder styles
the application uses, and SHALL fail the build in CI on any violation.

For printf style (any entry carrying a `*-format` flag): a `msgstr` SHALL
NOT contain a `%` separated from its conversion letter by whitespace (e.g.
`"% s"`, `"% d"`), which `msgfmt --check` accepts under its printf modes but
which renders incorrectly at runtime. The check SHALL ignore legitimate
positional reordering such as `%2$s ... %1$d` and the literal `%%` escape.

For `str.format` style (any entry whose `msgid` contains a `{...}`
replacement field; gettext has no flag for these, so `msgfmt` validates
nothing): each non-empty `msgstr` SHALL parse without error under
`string.Formatter().parse()` and SHALL carry the same multiset of
replacement-field names as the `msgid`. A renamed, whitespace-corrupted
(`"{ count }"` vs `"{count}"`), dropped, or extra field SHALL fail
validation. The literal `{{`/`}}` escapes SHALL NOT be counted as fields.

Obsolete (`#~`) entries never compile into a released catalog, so the
validation SHALL ignore them: only shipped (non-obsolete) entries are
checked, and an obsolete entry that a parser surfaces among active ones
SHALL be excluded from these checks.

#### Scenario: python-format entry with a spaced token is rejected
- **WHEN** a catalog contains a `#, python-format` entry whose `msgstr` is
  `"...% s..."` while the `msgid` is `"...%s..."`
- **THEN** the mechanical validation fails and CI fails the build

#### Scenario: printf positional reordering passes
- **WHEN** a `python-format` entry's `msgstr` uses only well-formed printf
  tokens, including a legitimate positional reordering such as `%2$s ... %1$d`
- **THEN** the format-placeholder check succeeds for that entry

#### Scenario: format entry whose msgstr renames a field is rejected
- **WHEN** a `msgid` is `"{count} in {dir}"` and its `msgstr` is
  `"{ count } dans {dir}"`
- **THEN** the field-name multiset differs, validation fails, and CI fails
  the build

#### Scenario: format entry with a malformed brace is rejected
- **WHEN** an entry's `msgid` contains a `{...}` field and its `msgstr` has
  an unbalanced brace such as `"{value"`
- **THEN** `string.Formatter().parse()` errors and validation fails the build

#### Scenario: format entry with matching fields passes
- **WHEN** a `msgid` is `"{0} and {1}"` and its `msgstr` reorders to
  `"{1} et {0}"` (indexed fields)
- **THEN** the field-name multisets match and validation succeeds

#### Scenario: entry with no placeholders is unaffected
- **WHEN** an entry's `msgid` contains neither a printf token nor a `{}`
  field and the `msgstr` introduces a stray `%` or `{`
- **THEN** this check does not report the entry and the validation outcome is
  unchanged

### Requirement: Catalog hygiene defects are reported
The mechanical catalog validation SHALL report, per catalog, four hygiene
conditions that `msgfmt --check` does not: (a) the count of obsolete `#~`
entries, (b) entries carrying a `#, fuzzy` flag whose `msgstr` is empty,
(c) any `msgstr` text that is not normalised to Unicode NFC form, and (d)
any `msgid` that uses a bare `{}` replacement field while the string
contains more than one field. These SHALL be surfaced as an advisory report
that does not fail the build by default. The obsolete-entry count SHALL be
subject to a configurable ceiling initialised at or above the current total,
so that the build fails only when the count *grows* beyond the ceiling, not
because of the pre-existing backlog. Condition (d) is advisory rather than a
hard gate because a bare `{}` with a single field is legitimate; it flags
only the multi-field case, which translators cannot reorder safely and
should express as `{0}`/`{1}` or named fields.

#### Scenario: hygiene issues are reported without failing
- **WHEN** a catalog contains obsolete entries, empty-fuzzy entries,
  out-of-NFC text, or a multi-field bare `{}` `msgid`, and is within the
  configured obsolete ceiling
- **THEN** validation prints the per-catalog counts and exits successfully

#### Scenario: obsolete backlog growth is rejected
- **WHEN** a change adds obsolete `#~` entries such that a catalog's count
  exceeds its configured ceiling
- **THEN** validation fails the build, signalling a regression rather than
  the existing backlog
