# application-version Specification

## Purpose

Defines how the running application determines, validates and reports its
version, including the fallback used when installed distribution metadata is
missing, unreadable or malformed.

## Requirements

### Requirement: Version detection never blocks startup

The application SHALL resolve its version to a non-empty string while
importing. It SHALL use the source `pyproject.toml` when running from a
checkout; otherwise it SHALL use installed distribution metadata. When that
metadata is absent, unreadable or carries no `Version` field, the application
SHALL continue starting with a defined unknown-version string instead of
raising.

#### Scenario: Source checkout uses the project version

- **WHEN** the application runs from a checkout whose `pyproject.toml`
  declares a project version
- **THEN** the resolved version is that project version

#### Scenario: Installed metadata supplies the version

- **WHEN** the application runs from an installation whose `scantpaper`
  distribution metadata declares `Version: 4.0.4`
- **THEN** the resolved version is `4.0.4`

#### Scenario: Missing metadata does not prevent startup

- **WHEN** the installed `scantpaper` distribution metadata is missing, and
  no `pyproject.toml` is available
- **THEN** the application starts and reports the unknown-version string

#### Scenario: Metadata without a version does not prevent startup

- **WHEN** the installed `scantpaper` distribution metadata exists but has no
  `Version` field, and no other distribution supplies one
- **THEN** the application starts and reports the unknown-version string

### Requirement: A valid installed version is recovered despite stale metadata

When the first discovered `scantpaper` distribution has no `Version`, the
application SHALL inspect the remaining installed distributions and use the
first one that supplies a version. It SHALL use the unknown-version string
only when no installed distribution supplies a version.

#### Scenario: Empty stale metadata does not hide the current version

- **WHEN** an empty `scantpaper-<old>.dist-info` directory is discovered before
  the current distribution's metadata
- **THEN** the resolved version is the current distribution's version

#### Scenario: Only stale metadata falls back to unknown

- **WHEN** the only discovered `scantpaper` distribution has no `Version`
- **THEN** the application starts and reports the unknown-version string

### Requirement: Version reporting uses the resolved string

The application SHALL use the resolved version string for the command-line
`--version` output, the window title, the About dialog, saved PDF metadata and
saved hOCR `ocr-system` metadata. When the unknown-version string is resolved,
those surfaces SHALL present it without raising.

#### Scenario: Version option reports a valid version

- **WHEN** the application is run with `--version` and a valid installed
  version is resolved
- **THEN** it prints `scantpaper <version>` and exits successfully

#### Scenario: Version option reports the fallback

- **WHEN** the application is run with `--version` and the unknown-version
  string is resolved
- **THEN** it prints the unknown-version string instead of raising

#### Scenario: Startup succeeds with the fallback

- **WHEN** the application starts while the unknown-version string is resolved
- **THEN** the main window opens
