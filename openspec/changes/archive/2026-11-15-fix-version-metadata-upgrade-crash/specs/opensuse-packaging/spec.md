# Spec Delta

## ADDED Requirements

### Requirement: RPM file lists own the package's site-packages directories

The generated `%files` list for every package in the openSUSE set SHALL own the
package's directories under the Python install tree, including the
version-named `*.dist-info` directory. Shared system directories such as
`/usr`, `/usr/lib`, `/usr/bin` and `/usr/share` SHALL remain unowned. An
upgrade SHALL therefore remove the previous version's `*.dist-info` directory.

#### Scenario: Leap package owns its metadata directory

- **WHEN** a Leap `scantpaper` RPM is inspected
- **THEN** its file list contains the version-named
  `site-packages/scantpaper-*.dist-info/` directory

#### Scenario: Tumbleweed package owns its metadata directory

- **WHEN** a Tumbleweed `scantpaper` RPM is inspected
- **THEN** its file list contains the version-named
  `site-packages/scantpaper-*.dist-info/` directory

#### Scenario: Upgrade removes the previous metadata directory

- **WHEN** a package built this way replaces a previous release that owned its
  own metadata directory
- **THEN** the previous version's `*.dist-info` directory is removed

#### Scenario: Shared system directories stay unowned

- **WHEN** the generated file list is inspected
- **THEN** it does not own `/usr`, `/usr/lib`, `/usr/bin` or `/usr/share`

### Requirement: CI rejects an RPM that does not own its metadata directory

The openSUSE build SHALL reject any built RPM whose file list does not contain
the version-named `*.dist-info/` directory it installs. The check SHALL name
the offending RPM and SHALL run for both the Leap and Tumbleweed artifact
sets.

#### Scenario: Leap set is checked

- **WHEN** the Leap artifact set is built
- **THEN** every RPM that installs a `*.dist-info` directory lists that
  directory in its file list

#### Scenario: Tumbleweed set is checked

- **WHEN** the Tumbleweed artifact set is built
- **THEN** every RPM that installs a `*.dist-info` directory lists that
  directory in its file list

#### Scenario: Unowned metadata fails the check

- **WHEN** a built RPM installs a `*.dist-info` directory without owning it
- **THEN** the check fails and names that RPM

### Requirement: Clean-room checks cover stale distribution metadata

Each openSUSE target's clean-room check SHALL create an empty stale
`scantpaper-*.dist-info` directory in the installed site-packages before
running the application. The application SHALL still start and report the
source ref's version through `scantpaper --version`.

#### Scenario: Leap install survives stale metadata

- **WHEN** an empty stale `scantpaper-*.dist-info` directory exists in the
  Leap clean-room install
- **THEN** `scantpaper --version` reports the source ref's version and exits
  successfully

#### Scenario: Tumbleweed install survives stale metadata

- **WHEN** an empty stale `scantpaper-*.dist-info` directory exists in the
  Tumbleweed clean-room install
- **THEN** `scantpaper --version` reports the source ref's version and exits
  successfully

#### Scenario: A crash or unknown fallback fails the check

- **WHEN** the application crashes or reports the unknown-version fallback
  with stale metadata present
- **THEN** the clean-room check fails and names the target
