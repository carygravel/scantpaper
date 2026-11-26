# Spec Delta

## ADDED Requirements

### Requirement: Metadata strings are extracted into the message template

The message template SHALL extract translatable strings from the AppStream
metainfo using a vendored `metainfo.its`, and from the desktop entry using
gettext's Desktop parser. The desktop `Name` and `Keywords` SHALL be excluded.
Every extracted msgid SHALL name its metadata source, and the template SHALL
still be generated with gettext alone.

#### Scenario: Metainfo strings are extracted
- **WHEN** the message template is generated
- **THEN** it contains the translatable metainfo summary and description
  strings

#### Scenario: The desktop comment is extracted
- **WHEN** the message template is generated
- **THEN** it contains the desktop entry's `Comment` value

#### Scenario: The desktop brand and keywords are excluded
- **WHEN** the message template is generated
- **THEN** it contains neither the desktop `Name` value nor the `Keywords`
  value as a msgid from the desktop file

#### Scenario: Metadata references are recorded
- **WHEN** a msgid is extracted from the metainfo or the desktop entry
- **THEN** its template entry names the metadata file it came from

#### Scenario: A missing metadata source fails generation
- **WHEN** the metainfo or desktop source file is absent
- **THEN** generation exits non-zero rather than silently omitting its strings

## MODIFIED Requirements

### Requirement: Vendored ITS rules are compared with the installed copy

Because a vendored copy can drift from upstream, the validation SHALL compare
each vendored pair against the installed copy and report any difference. The
comparison SHALL be advisory and SHALL NOT fail the build: a difference means
this project's copy may be behind, not that the generated template is wrong.
The report SHALL name the files and state whether the installed copy is
absent, so an absent copy is distinguishable from an identical one.

#### Scenario: vendored rules differ from the installed copy
- **WHEN** the ITS rules installed on the system differ in content from a
  vendored copy
- **THEN** the difference is reported, naming both files, and validation exits
  successfully

#### Scenario: no ITS rules are installed on the system
- **WHEN** the system has no copy of a vendored ITS rule set to compare
  against
- **THEN** the report states that no installed copy was found, which is
  distinguishable from a matching copy, and generation still uses the
  vendored rules

#### Scenario: metainfo rules differ from the installed copy
- **WHEN** the installed metainfo ITS rules differ from the vendored pair
- **THEN** the difference is reported for the metainfo pair, naming both
  files, and validation exits successfully
