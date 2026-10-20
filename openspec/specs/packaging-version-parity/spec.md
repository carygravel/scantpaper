# packaging-version-parity

## Purpose

Generate RPM metadata and source from the same git ref at build time, so
release and snapshot RPMs identify and package that ref, and upstream
builds sort below distro packages for the same upstream release.

## Requirements

### Requirement: Specs are rendered from the selected source ref

The committed packaging specs SHALL contain `@VERSION@` and `@RELEASE@`
placeholders and MUST NOT contain a literal version value. A shared
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

### Requirement: Source archive matches the source ref

The renderer SHALL create `scantpaper-<version>.tar.gz` from
`git archive <ref>` with a top-level `scantpaper-<version>/` directory,
and the rendered spec's `Source0` SHALL name that local archive. Builds
SHALL NOT fetch a tag tarball for ScantPaper.

#### Scenario: Branch source is archived

- **WHEN** the source ref is a branch commit that changes `src/`
- **THEN** the archive contains the branch's file and no tag tarball is
  downloaded

#### Scenario: Uncommitted files are excluded

- **WHEN** the worktree contains a modified tracked file or an untracked
  file
- **THEN** neither appears in the archive

#### Scenario: Tag source is archived

- **WHEN** the source ref is the `v4.0.0` tag
- **THEN** the archive contains the v4.0.0 tree

### Requirement: Tag and project version agree

When the selected source ref is a `v<version>` tag, the renderer SHALL
assert that the tag's version equals the `pyproject.toml` version at
that ref. A mismatch SHALL fail before any spec or archive is written.

#### Scenario: Matching tag

- **WHEN** the ref is tag `v3.0.24` and its `pyproject.toml` declares
  `3.0.24`
- **THEN** rendering succeeds

#### Scenario: Mismatched tag

- **WHEN** the ref is tag `v4.0.0` but its `pyproject.toml` declares
  `3.0.24`
- **THEN** rendering fails and neither output file is created

### Requirement: Upstream builds sort below distro builds

For the same upstream version, the rendered `Release:` SHALL begin with
`0.` and the spec MUST NOT declare an `Epoch`, so a distro package at
`Release: 1` or higher sorts above the upstream build, including for a
tagged release.

#### Scenario: Distro package wins

- **WHEN** the upstream RPM is
  `3.0.24-0.512.g1b36963.fc43` and a distro package is
  `3.0.24-1.fc43`
- **THEN** RPM orders the distro package above the upstream package

#### Scenario: No epoch is emitted

- **WHEN** either spec is rendered
- **THEN** the output contains no `Epoch:` line

### Requirement: Changelog entry matches the generated EVR

The rendered spec's `%changelog` SHALL begin with an entry whose version
and release match the generated EVR, whose date is the source ref's
commit date, and whose text identifies a tagged release or a snapshot.
The template's older entries SHALL be preserved unchanged.

#### Scenario: Snapshot changelog entry

- **WHEN** the source ref is an untagged commit with short id `1b36963`
- **THEN** the first entry names `3.0.24-0.<count>.g1b36963` and says it
  is a snapshot build from that commit

#### Scenario: Tagged changelog entry

- **WHEN** the source ref is the `v3.0.24` tag
- **THEN** the first entry names `3.0.24-0.<count>.g<sha>` and identifies
  release `3.0.24`

#### Scenario: Changelog date is locale independent

- **WHEN** the renderer runs under a non-C locale
- **THEN** the changelog weekday and month use the fixed English
  abbreviations

### Requirement: Installed RPMs report the release version

When an RPM workflow runs for a release tag, the installed package
SHALL report that tag's version through `scantpaper --version`; if it
does not, the workflow SHALL fail.

#### Scenario: A stale artifact is rejected

- **WHEN** the `v4.0.0` release workflow installs an RPM built from the
  `v3.0.24` source
- **THEN** `scantpaper --version` does not report `4.0.0` and the
  workflow fails

### Requirement: Published releases can be rebuilt from their tag

The RPM workflows SHALL accept an optional `source_ref` and SHALL read
the version, source archive, commit count and commit date from that ref
while using the workflow's renderer and template. A published release
SHALL be rebuildable this way without moving or recreating its tag.

#### Scenario: Rebuild an older release

- **WHEN** a maintainer dispatches a workflow from the current branch
  with `source_ref=v3.0.24`
- **THEN** the build uses the v3.0.24 source and version even though the
  branch's `pyproject.toml` is newer, and the tag is not moved

#### Scenario: Normal dispatch uses the selected commit

- **WHEN** a maintainer dispatches a workflow without a `source_ref`
- **THEN** the renderer uses the commit that triggered the workflow
