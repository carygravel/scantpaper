# Spec Delta

## Purpose

Defines how the installed AppStream metainfo and FreeDesktop desktop entry
carry translations generated from the approved catalogs, and the English-only
shape their source files must keep.

## ADDED Requirements

### Requirement: Source metadata is English-only

Both metadata source files SHALL contain only the English source text. The
metainfo SHALL NOT carry inline `xml:lang` elements, and the desktop entry
SHALL NOT carry localized keys such as `Comment[de]`. Translations SHALL be
produced at build time from the approved catalogs, never committed to the
source files.

#### Scenario: Source metainfo has no inline translation
- **WHEN** the source metainfo is inspected
- **THEN** it contains no `xml:lang` element

#### Scenario: Source desktop entry has no localized key
- **WHEN** the source desktop entry is inspected
- **THEN** it contains no localized key such as `Comment[de]`

#### Scenario: An inline translation is rejected
- **WHEN** a change adds an inline `xml:lang` element or a localized desktop
  key to a source file
- **THEN** the test suite fails and names the offending file

### Requirement: Untranslatable metadata stays untranslated

The brand name, the developer name, and the desktop entry's `Name` and
`Keywords` SHALL NOT be translated. The metainfo SHALL mark the brand and
developer name `translate="no"`, and the join SHALL keep the desktop `Name`
and `Keywords` from the template even when a catalog contains a matching
msgid.

#### Scenario: Generated metainfo keeps one untranslated name
- **WHEN** the metainfo is joined
- **THEN** the brand `<name>` appears once, marked `translate="no"`, with no
  `xml:lang` variant

#### Scenario: Developer name is not translated
- **WHEN** the metainfo is joined
- **THEN** the `<developer><name>` element carries no `xml:lang` variant

#### Scenario: Desktop Name and Keywords are preserved
- **WHEN** a catalog translates `scantpaper` or the keyword list
- **THEN** the generated desktop entry keeps the template's `Name` and
  `Keywords` values and adds no localized variant of either

### Requirement: Installed metadata carries approved translations

The installed metainfo and desktop entry SHALL be generated from the same
approval-gated catalogs as the application's `.mo` files. A non-fuzzy
translation with a valid ledger approval SHALL appear as an inline `xml:lang`
element or a localized desktop key; a fuzzy or unapproved translation SHALL be
absent, so the English text is shown.

#### Scenario: Approved metainfo translation appears
- **WHEN** a catalog has an approved Czech translation of the summary
- **THEN** the generated metainfo contains that text in a
  `<summary xml:lang="cs">` element

#### Scenario: Unapproved metainfo translation is omitted
- **WHEN** a catalog has a non-fuzzy metainfo translation with no valid ledger
  approval
- **THEN** the generated metainfo has no `xml:lang` element for it and shows
  the English text

#### Scenario: Fuzzy metainfo translation is omitted
- **WHEN** a catalog has a fuzzy metainfo translation
- **THEN** the generated metainfo has no `xml:lang` element for it

#### Scenario: Approved desktop translation appears
- **WHEN** a catalog has an approved German translation of the desktop
  `Comment`
- **THEN** the generated desktop entry contains it as `Comment[de]`

#### Scenario: Unapproved desktop translation is omitted
- **WHEN** a catalog has a non-fuzzy desktop translation with no valid ledger
  approval
- **THEN** the generated desktop entry has no localized `Comment` for it

### Requirement: The join consumes the approval-gated catalogs

The join SHALL read the compiled `.mo` tree produced with the approval ledger,
not the raw `.po` files, so the ledger is applied exactly once. It SHALL use
only `msgunfmt` and `msgfmt` from gettext beyond the Python standard library,
and SHALL NOT require `itstool`.

#### Scenario: The join reads compiled catalogs
- **WHEN** a `.po` file is edited without recompiling the `.mo` tree
- **THEN** the joined output is unchanged

#### Scenario: The join needs no itstool
- **WHEN** the join runs on a system without `itstool`
- **THEN** it succeeds and produces the same output

#### Scenario: A language with no approved translation contributes nothing
- **WHEN** a language's catalog has no approved metainfo or desktop
  translation
- **THEN** the joined output adds no element or key for that language

### Requirement: Generated metadata is valid

The generated metainfo SHALL pass `appstreamcli validate --no-net`, and the
generated desktop entry SHALL pass `desktop-file-validate`. The metainfo
description SHALL NOT contain inline markup such as `<em>` or `<code>` while
the join is gettext-only, because `msgfmt --xml` escapes it; the join SHALL
fail when such markup is present.

#### Scenario: Generated metainfo validates
- **WHEN** the metainfo is joined
- **THEN** `appstreamcli validate --no-net` reports success

#### Scenario: Generated desktop entry validates
- **WHEN** the desktop entry is joined
- **THEN** `desktop-file-validate` reports no error

#### Scenario: Inline markup fails the join
- **WHEN** the metainfo description contains an `<em>` or `<code>` element
- **THEN** the join exits non-zero and names the element that cannot be joined

### Requirement: Every packaging path installs the generated metadata

Each supported packaging path (Debian/PPA, Fedora and openSUSE) SHALL install
the joined metainfo and desktop entry, not the English-only sources. A path
that regenerates the catalogs SHALL run the join after compiling them, and a
recipe that omits the join SHALL fail the packaging test.

#### Scenario: Each recipe runs the join after compiling
- **WHEN** a packaging recipe regenerates the catalogs
- **THEN** it invokes the join after the catalog compilation step

#### Scenario: A package carries translated metadata
- **WHEN** a package is built
- **THEN** its installed metainfo and desktop entry contain the approved
  translations from the catalogs

#### Scenario: A recipe without the join is rejected
- **WHEN** a packaging recipe omits the join
- **THEN** the packaging test fails and names the recipe
