## ADDED Requirements

### Requirement: Malformed format placeholders fail catalog validation

The mechanical catalog validation SHALL reject entries whose translated
text contains a malformed format placeholder, for both placeholder styles the
application uses, and SHALL fail the build in CI on any violation.

For printf style (any entry carrying a `*-format` flag — `python-format` or a
stale `perl-format` left by an earlier seed): a `msgstr` SHALL NOT contain a
`%` separated from its conversion letter by whitespace (e.g. `"% s"`,
`"% d"`), which `msgfmt --check` accepts under its printf modes but which
renders incorrectly at runtime. The check SHALL ignore legitimate positional
reordering such as `%2$s ... %1$d` and the literal `%%` escape.

For `str.format` style (any entry whose `msgid` contains a `{...}`
replacement field; gettext has no flag for these, so `msgfmt` validates
nothing): each non-empty `msgstr` SHALL parse without error under
`string.Formatter().parse()` (no unbalanced/malformed brace) and SHALL carry
the same multiset of replacement-field names as the `msgid`. A renamed,
whitespace-corrupted (`"{ count }"` vs `"{count}"`), dropped, or extra field
SHALL fail validation. The literal `{{`/`}}` escapes SHALL NOT be counted as
fields.

This requirement exists because a malformed placeholder that survives into a
compiled catalog either renders incorrectly (`%s` drops the adjacent space,
`%d`/`%i` gains a leading one) or raises at the first `.format()` call
(`KeyError`/`ValueError`) — neither observable until a user reaches that
message.

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
- **THEN** the field-name multiset differs, validation fails, and CI fails the
  build

#### Scenario: format entry with a malformed brace is rejected

- **WHEN** an entry's `msgid` contains a `{...}` field and its `msgstr` has an
  unbalanced brace such as `"{value"`
- **THEN** `string.Formatter().parse()` errors and validation fails the build

#### Scenario: format entry with matching fields passes

- **WHEN** a `msgid` is `"{0} and {1}"` and its `msgstr` reorders to
  `"{1} et {0}"` (indexed fields)
- **THEN** the field-name multisets match and validation succeeds

#### Scenario: entry with no placeholders is unaffected

- **WHEN** an entry's `msgid` contains neither a printf token nor a `{}` field
  and the `msgstr` introduces a stray `%` or `{`
- **THEN** this check does not report the entry and the validation outcome is
  unchanged

### Requirement: Catalog hygiene defects are reported

The mechanical catalog validation SHALL report, per catalog, four hygiene
conditions that `msgfmt --check` does not: (a) the count of obsolete `#~`
entries, (b) entries carrying a `#, fuzzy` flag whose `msgstr` is empty, (c)
any `msgstr` text that is not normalised to Unicode NFC form, and (d) any
`msgid` that uses a bare `{}` replacement field while the string contains
more than one field. These SHALL be surfaced as an advisory report that does
not fail the build by default. The obsolete-entry count SHALL be subject to a
configurable ceiling initialised at or above the current total, so that the
build fails only when the count *grows* beyond the ceiling, not because of the
pre-existing backlog. Condition (d) is advisory rather than a hard gate
because a bare `{}` with a single field is legitimate; it flags only the
multi-field case, which translators cannot reorder safely and should express
as `{0}`/`{1}` or named fields.

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
