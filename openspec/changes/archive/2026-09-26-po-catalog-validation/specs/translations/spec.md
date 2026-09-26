## ADDED Requirements

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
