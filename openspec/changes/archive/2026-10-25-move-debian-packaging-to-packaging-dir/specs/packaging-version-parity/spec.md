# Spec Delta

## MODIFIED Requirements

### Requirement: Specs are rendered from the selected source ref

The committed RPM specs SHALL contain `@VERSION@` and `@RELEASE@`
placeholders and MUST NOT contain a literal version value. The RPM
renderer SHALL produce a buildable spec whose `Version:` equals the
`[project] version` in `pyproject.toml` at the selected source ref and
whose `Release:` is `0.<commit-count>.g<short-sha>%{?dist}`.

#### Scenario: Branch build uses the branch version

- **WHEN** the selected ref's `pyproject.toml` declares `4.0.0` and the
  ref has 512 commits
- **THEN** the rendered spec declares `Version: 4.0.0` and
  `Release: 0.512.g<short-sha>%{?dist}`

#### Scenario: A hard-coded template fails the repository check

- **WHEN** a committed spec declares a literal `Version: 3.0.24`
- **THEN** the template check fails and names the offending spec

#### Scenario: Shallow history is rejected

- **WHEN** the renderer runs in a shallow clone
- **THEN** it fails with an explicit full-history error and writes no
  spec or archive

### Requirement: Tag and project version agree

When the selected source ref is a `v<version>` tag, every packaging
renderer SHALL assert that the tag's version equals the
`pyproject.toml` version at that ref. A mismatch SHALL fail before any
spec, archive or rendered packaging is written.

#### Scenario: Matching tag

- **WHEN** the ref is tag `v3.0.24` and its `pyproject.toml` declares
  `3.0.24`
- **THEN** rendering succeeds

#### Scenario: Mismatched tag

- **WHEN** the ref is tag `v4.0.0` but its `pyproject.toml` declares
  `3.0.24`
- **THEN** rendering fails and no output file is created

## ADDED Requirements

### Requirement: Debian version is rendered from the selected source ref

The committed Debian changelog template SHALL contain `@VERSION@` and
MUST NOT contain a literal version. The Debian renderer SHALL produce a
changelog whose version is
`<version>-0.<commit-count>.g<short-sha>`, where `<version>` is the
`[project] version` in `pyproject.toml` at the selected source ref.

#### Scenario: Tag build uses the tag version

- **WHEN** the ref is tag `v4.0.1`, its `pyproject.toml` declares
  `4.0.1`, and the ref has 500 commits
- **THEN** the rendered changelog version is `4.0.1-0.500.g<short-sha>`

#### Scenario: Branch build uses the branch version

- **WHEN** the selected ref's `pyproject.toml` declares `4.0.2` and the
  ref has 530 commits
- **THEN** the rendered changelog version is `4.0.2-0.530.g<short-sha>`

#### Scenario: Same commit yields the same version

- **WHEN** one commit is rendered once while carrying its release tag
  and once without it
- **THEN** both renders declare the same Debian version

#### Scenario: A hard-coded template fails the repository check

- **WHEN** the committed changelog template declares a literal version
- **THEN** the template check fails and names the offending file

### Requirement: Debian snapshots sort below the distro package

The rendered Debian version SHALL order a later snapshot above the build
of an earlier tag and below a distro package for the same upstream
version, and the changelog version MUST NOT carry an epoch. For
`4.0.1-0.500.g<tag-sha>` and a distro package at `4.0.1-1`, the order is
`4.0.1-0.500.g<tag-sha>` < `4.0.1-0.501.g<sha>` < `4.0.1-1`.

#### Scenario: Later snapshot wins

- **WHEN** the upstream versions are `4.0.1-0.500.g<tag-sha>` and
  `4.0.1-0.501.g<sha>`
- **THEN** `dpkg` orders the second above the first

#### Scenario: Distro package wins

- **WHEN** the upstream version is `4.0.1-0.501.g<sha>` and a distro
  package is `4.0.1-1`
- **THEN** `dpkg` orders the distro package above the upstream build

#### Scenario: No epoch is emitted

- **WHEN** the changelog is rendered for any ref
- **THEN** its version contains no `epoch:` prefix

### Requirement: Debian changelog entry matches the rendered version

The rendered `debian/changelog` SHALL hold exactly one entry whose
version matches the rendered version, whose date is the source ref's
commit date in Debian changelog form, and whose text identifies either a
tagged release or a snapshot build.

#### Scenario: Snapshot changelog entry

- **WHEN** the source ref is an untagged commit with short id `1b36963`
- **THEN** the entry version ends in `g1b36963` and the entry text says
  it is a snapshot build from that commit

#### Scenario: Tagged changelog entry

- **WHEN** the source ref carries the `v4.0.1` tag
- **THEN** the entry text identifies release `4.0.1`

#### Scenario: Changelog date is locale independent

- **WHEN** the renderer runs under a non-C locale
- **THEN** the changelog date uses fixed English weekday and month names

### Requirement: Debian package rebuilds from a published tag

The Debian workflow SHALL accept an optional `source_ref` and read the
version, source tree and commit date from that ref while using the
workflow's renderer and templates, so a published release can be rebuilt
without moving or recreating its tag.

#### Scenario: Rebuild an older release

- **WHEN** a maintainer dispatches the workflow from the current branch
  with `source_ref=v4.0.1`
- **THEN** the build uses the v4.0.1 source and version even though the
  branch's `pyproject.toml` is newer, and the tag is not moved

#### Scenario: Normal dispatch uses the selected commit

- **WHEN** a maintainer dispatches the workflow without a `source_ref`
- **THEN** the renderer uses the commit that triggered the workflow
