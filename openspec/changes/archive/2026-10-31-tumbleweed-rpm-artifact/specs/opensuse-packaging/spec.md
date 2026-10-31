# Spec Delta

## Purpose

Defines how the openSUSE RPM artifacts are produced for each supported
openSUSE release, so a user on Leap or Tumbleweed can install the same
application from one published release.

## ADDED Requirements

### Requirement: Supported openSUSE targets

The openSUSE build SHALL produce an artifact set for Leap 16.0 and for
Tumbleweed, and SHALL reject a target it does not support before building
anything.

#### Scenario: Leap artifact is produced

- **WHEN** the build runs for Leap 16.0
- **THEN** it produces the Leap RPM set

#### Scenario: Tumbleweed artifact is produced

- **WHEN** the build runs for Tumbleweed
- **THEN** it produces the Tumbleweed RPM set

#### Scenario: Unknown target is rejected

- **WHEN** the build is asked for an unsupported target
- **THEN** it exits with an error naming the target and produces no RPM

### Requirement: Tumbleweed uses distribution Python packages

The Tumbleweed artifact SHALL depend on Tumbleweed's packaged Python
modules for every runtime dependency it provides, and SHALL locally build
only ScantPaper and the patched python-sane. It MUST NOT install a locally
built module at a version lower than the Tumbleweed package.

#### Scenario: Dependency set is minimal

- **WHEN** the Tumbleweed artifact is collected
- **THEN** it contains ScantPaper and the patched python-sane, and no other
  locally rebuilt Python module

#### Scenario: Distribution versions are not downgraded

- **WHEN** the Tumbleweed set is installed on a current Tumbleweed system
- **THEN** zypper installs it without `--allow-downgrade` and without
  replacing a newer distribution package with an older local build

### Requirement: Leap dependency set is unchanged

The Leap 16.0 artifact SHALL continue to contain the locally rebuilt
Python dependency packages that Leap does not provide.

#### Scenario: Leap set keeps its dependencies

- **WHEN** the Leap 16.0 artifact is collected
- **THEN** it contains the same locally rebuilt dependency packages as
  before the Tumbleweed target was added

### Requirement: Patched python-sane on every target

Every artifact set SHALL contain a python-sane build carrying the
`snap()` patch, built for that target's default Python flavor, and
sorting above a distribution package at the same upstream version but
below a later upstream release.

#### Scenario: Tumbleweed set carries the patch

- **WHEN** the Tumbleweed artifact is inspected
- **THEN** its python-sane package contains the `snap()` patch and is
  built for Tumbleweed's default Python flavor

#### Scenario: A later upstream release wins

- **WHEN** Tumbleweed publishes python-sane at a later upstream version
- **THEN** RPM orders that package above the patched build

### Requirement: Tumbleweed python-sane preserves distribution capabilities

The patched python-sane in the Tumbleweed set SHALL provide the
unversioned `python3-sane` and `python3dist(python-sane)` capabilities, so
replacing the distribution package leaves other packages' requirements
satisfiable.

#### Scenario: Replacement keeps requirements satisfied

- **WHEN** the patched python-sane replaces Tumbleweed's python-sane
- **THEN** a package that requires `python3-sane` still resolves

### Requirement: Release identity matches the target

The Leap artifact SHALL carry the Leap distribution suffix and the
Tumbleweed artifact MUST NOT carry it. Published assets for the two
targets SHALL have distinct file names.

#### Scenario: Leap package is labelled

- **WHEN** a Leap RPM is built
- **THEN** its release contains the Leap distribution suffix

#### Scenario: Tumbleweed package is not labelled as Leap

- **WHEN** a Tumbleweed RPM is built
- **THEN** its release does not contain the Leap suffix

#### Scenario: Release assets do not collide

- **WHEN** both targets are built for the same source ref and attached to
  one release
- **THEN** no asset overwrites an asset from the other target

### Requirement: Clean-room install verifies the published set

Each target's published artifact SHALL install in a clean container of
that release without resolution flags, and the installed application
SHALL report the source ref's version and import its runtime modules.

#### Scenario: Tumbleweed clean install succeeds

- **WHEN** the Tumbleweed set is installed in a container with only the
  default repositories
- **THEN** installation succeeds and `scantpaper --version` reports the
  version of the selected source ref

#### Scenario: Broken runtime import fails the check

- **WHEN** an installed runtime module cannot be imported
- **THEN** the check fails and names the module

#### Scenario: Stale artifact is rejected

- **WHEN** a tag build installs an artifact built from a different source
  ref
- **THEN** the version check fails

### Requirement: Tumbleweed build uses the standard package triggers

The Tumbleweed build SHALL run on the same triggers as the other package
builds: `push`, `pull_request` and `workflow_dispatch`, with the same
optional `source_ref` input.

#### Scenario: Pull request builds the Tumbleweed set

- **WHEN** a pull request is opened
- **THEN** the Tumbleweed build runs and reports its result

#### Scenario: Tag build publishes the Tumbleweed set

- **WHEN** a `v*` tag is pushed
- **THEN** the Tumbleweed build runs and its assets are attached to the
  release

#### Scenario: Rebuild from a published tag

- **WHEN** a maintainer dispatches the workflow with `source_ref=v4.0.1`
- **THEN** the build uses that ref

### Requirement: Installed payload matches the Leap package

The Tumbleweed package SHALL install the same application files as the
Leap package, including the desktop entry, AppStream metadata, icons,
translations, man page and README. It MUST NOT add generated HTML
documentation.

#### Scenario: Payload parity

- **WHEN** the file lists of the Leap and Tumbleweed packages are compared
- **THEN** they contain the same application files

#### Scenario: HTML documentation is not added

- **WHEN** the Tumbleweed package is inspected
- **THEN** it contains no generated `documentation.html`

### Requirement: Tumbleweed installation is documented

The user documentation SHALL describe how to install the Tumbleweed RPMs,
note that they include the patched python-sane, and state that PostScript
export is unavailable because `tiff2ps` is not packaged.

#### Scenario: User finds the Tumbleweed instructions

- **WHEN** a Tumbleweed user reads the RPM installation section
- **THEN** it names the Tumbleweed artifact and its install command

#### Scenario: Patch caveat is stated

- **WHEN** a user reads the Tumbleweed notes
- **THEN** the documentation explains that the artifact replaces
  Tumbleweed's python-sane with the patched build

#### Scenario: PostScript limitation is stated

- **WHEN** a Tumbleweed user looks for PostScript export support
- **THEN** the documentation says `tiff2ps` is not packaged
