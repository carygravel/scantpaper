## Purpose

Prepares the three release-version files (`pyproject.toml`, `changelog.md` and
the AppStream metainfo file) for a release so that the version and release date
are recorded consistently in one operation.

## ADDED Requirements

### Requirement: Release version resolution

The tool SHALL determine the release version from the newest `(unreleased)`
heading in `changelog.md`, and SHALL accept a `--version` override that MUST
match that heading. If no `(unreleased)` heading exists, or the override does
not match it, the tool SHALL fail without modifying any file.

#### Scenario: Version taken from the changelog

- **WHEN** the tool runs and `changelog.md` contains a `## 3.0.22 (unreleased)`
  heading
- **THEN** it treats `3.0.22` as the release version

#### Scenario: Override matches the changelog

- **WHEN** the tool is given `--version 3.0.22` and the changelog heading is
  `## 3.0.22 (unreleased)`
- **THEN** it proceeds with `3.0.22`

#### Scenario: Override disagrees with the changelog

- **WHEN** the tool is given `--version 3.0.23` but the newest `(unreleased)`
  heading is `## 3.0.22 (unreleased)`
- **THEN** it reports the mismatch and exits without modifying any file

#### Scenario: No unreleased heading

- **WHEN** the tool runs and `changelog.md` has no `(unreleased)` heading
- **THEN** it reports the missing heading and exits without modifying any file

### Requirement: Single consistent release date

The tool SHALL use one resolved date for every file it writes, so the changelog
date and the metainfo date are always identical. The date SHALL be taken from
`--date` when given, otherwise from `SOURCE_DATE_EPOCH` when set, otherwise
from the current date, formatted as `YYYY-MM-DD`.

#### Scenario: Changelog and metainfo dates match

- **WHEN** the tool writes `YYYY-MM-DD` to the changelog and the metainfo file
  in the same run
- **THEN** both files carry the exact same date

#### Scenario: Explicit date override

- **WHEN** the tool is given `--date 2026-10-04`
- **THEN** both the changelog and metainfo entries use `2026-10-04`

### Requirement: Changelog entry is stamped with the release date

The tool SHALL replace the `(unreleased)` marker on the release version's
heading in `changelog.md` with the resolved date, and SHALL NOT add or remove
any changelog bullet.

#### Scenario: Unreleased heading becomes dated

- **WHEN** the changelog contains `## 3.0.22 (unreleased)` and the resolved date
  is `2026-10-10`
- **THEN** the heading becomes `## 3.0.22 (2026-10-10)` and all bullets under
  it are unchanged

### Requirement: pyproject version is set

The tool SHALL set `[project] version` in `pyproject.toml` to the resolved
release version, preserving the rest of the file byte-for-byte.

#### Scenario: pyproject bumped

- **WHEN** `pyproject.toml` has `version = "3.0.21"` and the release version is
  `3.0.22`
- **THEN** the file contains `version = "3.0.22"` and every other line is
  unchanged

### Requirement: Metainfo release entry is added

The tool SHALL insert a `<release version="X.Y.Z" date="YYYY-MM-DD" />` element
as the first child of the `<releases>` element in the metainfo file, and SHALL
NOT alter existing `<release>` entries.

#### Scenario: New release is the newest entry

- **WHEN** the metainfo file's first release is `3.0.21` and the release version
  is `3.0.22`
- **THEN** a `3.0.22` entry with the resolved date is added above it and all
  older entries are unchanged

### Requirement: All-or-nothing write

The tool SHALL validate every transformation before writing any file, so that a
parse or validation failure leaves all three files untouched.

#### Scenario: One file fails validation

- **WHEN** the metainfo file cannot be parsed while the changelog and pyproject
  transformations are valid
- **THEN** no file is written and the tool reports an error

### Requirement: Dry run

The tool SHALL provide a `--dry-run` mode that performs all resolution and
validation and reports what would change without writing any file.

#### Scenario: Dry run writes nothing

- **WHEN** the tool runs with `--dry-run`
- **THEN** it prints the intended changes and all three files retain their
  original contents

### Requirement: No version control or translation side effects

The tool SHALL NOT invoke git or regenerate the translation template; committing,
tagging, pushing and `generate_pot.py` remain separate manual steps.

#### Scenario: No git or pot work

- **WHEN** the tool completes a successful release preparation
- **THEN** it has not created commits, tags or translation templates
