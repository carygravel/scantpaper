# packaging-release Specification

## Purpose

Defines how a tagged upstream release is propagated into the Debian and Ubuntu
packaging trees: a verified copy of the shared packaging, a drafted changelog,
and per-series PPA source packages, with signing and uploads left to the
maintainer.

## Requirements

### Requirement: Shared packaging is copied without drift

The sync tool SHALL copy every shared file from `packaging/debian/` into the
salsa `debian/` directory, delete shared files removed upstream, preserve
`debian/changelog`, and fail when any other file remains, naming it.

#### Scenario: Changed file is copied

- **WHEN** `packaging/debian/rules` changes upstream
- **THEN** the synced `debian/rules` is identical to it

#### Scenario: Removed file is deleted

- **WHEN** a shared file no longer exists in `packaging/debian/`
- **THEN** the synced `debian/` directory no longer contains it

#### Scenario: Stray file fails the sync

- **WHEN** `debian/patches/series` or any other file that is neither shared nor
  the changelog exists after the copy
- **THEN** the tool fails and names the file instead of leaving it in place

#### Scenario: Only the changelog differs

- **WHEN** the sync succeeds
- **THEN** `debian/` equals `packaging/debian/` except for `debian/changelog`

#### Scenario: Pre-migration release

- **WHEN** the previous release has no `packaging/debian` tree
- **THEN** the sync requires `debian/` to hold only the changelog and copies
  the tree without a diff

#### Scenario: Wrong checkout is refused

- **WHEN** the tool runs outside a salsa checkout with the expected debian
  branch and an imported upstream tree
- **THEN** it fails before writing anything and names the missing prerequisite

### Requirement: Changelog entry is drafted from the packaging diff

The sync tool SHALL add exactly one changelog entry, using the imported
upstream version and `unstable`: `<upstream>-1` when the upstream version
changed, the next revision otherwise. It SHALL draft bullets from the file,
dependency and rules changes since the previous release and leave the text
editable and uncommitted.

#### Scenario: New upstream version

- **WHEN** `pyproject.toml` reports `4.0.2` and the newest entry is
  `4.0.1-1`
- **THEN** the drafted entry is `4.0.2-1` for `unstable`

#### Scenario: Packaging-only update

- **WHEN** the upstream version matches the newest entry
- **THEN** the drafted revision is one higher

#### Scenario: Diff becomes bullets

- **WHEN** a test file was added and a build dependency was removed since the
  previous release
- **THEN** the draft names the added file and the removed dependency

#### Scenario: Draft is not committed

- **WHEN** the entry has been drafted
- **THEN** no commit, tag or push has been made and the text can still be
  edited

### Requirement: Per-series PPA sources come from a suite matrix

The PPA tool SHALL read `packaging/ubuntu/suites.toml` and, for each selected
series, produce a source package from the synced salsa tree in a throwaway
tree: version `<upstream>-0~ppa1<series>`, distribution `<series>`, that
series' `debhelper-compat`, and any configured test-dependency removals,
reusing the pristine-tar orig tarball.

#### Scenario: noble source package

- **WHEN** the tool prepares noble
- **THEN** the source version is `<upstream>-0~ppa1noble`, its distribution is
  `noble`, and its `debhelper-compat` is 13

#### Scenario: stonking source package

- **WHEN** the tool prepares stonking
- **THEN** its `debhelper-compat` is 14

#### Scenario: Series without a test dependency

- **WHEN** the matrix removes `jbig2` for jammy
- **THEN** the jammy source's `debian/tests/control` does not name it

#### Scenario: Orig tarball is reused

- **WHEN** the source package is built
- **THEN** it uses the orig tarball exported from pristine-tar rather than
  generating a new one

#### Scenario: Salsa tree is left untouched

- **WHEN** all selected series have been built
- **THEN** the salsa working tree is unchanged and each series' tree was
  discarded

### Requirement: Matrix values are verified against the series archive

The PPA tool SHALL verify a series' configured `debhelper-compat` against the
`debhelper` provides of that series' archive and fail, naming the series, when
the value is not available there.

#### Scenario: Stale matrix is rejected

- **WHEN** the matrix gives noble a compat value its `debhelper` does not
  provide
- **THEN** verification fails and names noble

### Requirement: Signing and uploads stay manual

The tools SHALL NOT commit, tag, push, sign or upload. They SHALL stop after
writing their outputs and print the commands for the maintainer to run.

#### Scenario: Sync stops before history

- **WHEN** the sync has written `debian/` and the changelog draft
- **THEN** it prints the build, test, commit and upload commands and creates no
  commit or tag

#### Scenario: PPA sources are unsigned and not uploaded

- **WHEN** the PPA tool has built a source package
- **THEN** it is unsigned, nothing has been uploaded, and the tool prints
  `debsign` and `dput` for the maintainer
