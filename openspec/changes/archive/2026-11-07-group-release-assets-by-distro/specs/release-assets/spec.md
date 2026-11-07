# Spec Delta

## Purpose

Defines what a tagged GitHub release publishes for each supported
distribution, so a user can choose one self-contained install set and the
release page explains that choice.

## ADDED Requirements

### Requirement: One archive per RPM target

A tagged release SHALL publish exactly one archive per supported RPM
target - Fedora 43, Fedora 44, openSUSE Leap 16.0 and openSUSE
Tumbleweed - and SHALL NOT publish those targets' individual RPMs as
separate release assets. The Debian package and the wheel SHALL remain
individual assets.

#### Scenario: Fedora release has one archive per version

- **WHEN** a tag builds Fedora 43 and Fedora 44
- **THEN** the release has one Fedora 43 archive and one Fedora 44
  archive, and no individual Fedora RPMs

#### Scenario: openSUSE targets are distinct

- **WHEN** both openSUSE targets are built for one tag
- **THEN** the release has one Leap 16.0 archive and one Tumbleweed
  archive with distinct names

#### Scenario: Debian and wheel stay individual

- **WHEN** the Debian package and wheel are built for a tag
- **THEN** each is attached as its own asset

### Requirement: Archive identifies its target and version

Each archive name SHALL contain the project name, the release version and
a target identifier that distinguishes every supported distribution, so no
two targets are confused by filename alone.

#### Scenario: Target is visible in the name

- **WHEN** a user lists the release assets
- **THEN** the Fedora, Leap and Tumbleweed archives are distinguishable
  from their names

#### Scenario: Rebuilt archive keeps its identity

- **WHEN** a tag release is rebuilt
- **THEN** each target's replacement archive has the same target and
  version identity as the original

### Requirement: Archive is a complete, verifiable runtime set

Each archive SHALL contain the target's complete runtime RPM set under a
single top-level directory, a `SHA256SUMS` file covering every RPM, and an
install note naming the command that installs the set in one transaction.
It MUST NOT contain build-only helper or debug packages.

#### Scenario: Checksums cover every RPM

- **WHEN** the archive is extracted and `sha256sum -c SHA256SUMS` runs
- **THEN** every RPM passes

#### Scenario: Install note names the command

- **WHEN** a user opens the archive's install note
- **THEN** it gives the target's install command, including the
  unsigned-RPM flag for openSUSE

#### Scenario: Debug packages are absent

- **WHEN** a Fedora archive is inspected
- **THEN** it contains no `-debuginfo` or `-debugsource` RPM

#### Scenario: Runtime dependencies are present

- **WHEN** a target's archive is extracted
- **THEN** it contains every locally rebuilt package that target needs,
  not just the application RPM

#### Scenario: Archives do not mix targets

- **WHEN** the Leap and Tumbleweed archives are extracted
- **THEN** neither contains a package built for the other target

### Requirement: Release page explains the archive menu

Every tagged release body SHALL carry a Downloads section that explains
the one-archive-per-target convention, gives install commands for Fedora
and openSUSE, routes Debian and Ubuntu users to apt and the PPA, and links
to the installation guide. The text MUST NOT depend on a specific
ScantPaper version, so it remains correct for every tag and every
publishing workflow.

#### Scenario: Release body carries the section

- **WHEN** a tag release is published
- **THEN** its body contains the Downloads section

#### Scenario: Section covers every target

- **WHEN** the Downloads section is read
- **THEN** it names the Fedora, Leap and Tumbleweed archive patterns and
  the Debian and wheel alternatives

#### Scenario: openSUSE command is complete

- **WHEN** the Downloads section gives the openSUSE commands
- **THEN** they include `--allow-unsigned-rpm`

#### Scenario: No version-specific archive name

- **WHEN** the same release body is used for a later tag
- **THEN** it still describes that release's archives without editing

### Requirement: Publishing is tag-only

Only a workflow run started from a tag SHALL attach assets or the
Downloads section to a release. A branch or pull-request build MUST NOT
publish.

#### Scenario: Tag publishes

- **WHEN** the triggering ref is a tag
- **THEN** the target archive and the Downloads section are attached to
  the release

#### Scenario: Branch build stays private

- **WHEN** the triggering ref is a branch or pull request
- **THEN** no release asset or body is published
