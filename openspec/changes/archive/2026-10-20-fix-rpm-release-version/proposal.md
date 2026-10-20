## Why

Every GitHub release since v3.0.20 has shipped RPMs built from the
v3.0.19 source tarball. The Fedora and openSUSE `scantpaper.spec`
files hard-code a `Version:` that release preparation has to remember
to change, and `Source0` derives the tarball URL from that version. The
v3.0.24 release therefore contains `scantpaper-3.0.19-1.*.rpm` assets
that package September's GTK3-era code while the wheel and `.deb` on
the same page are 3.0.24. The defect is invisible to CI: the builds
succeed, `%check` does not run the test suite, and the clean-room job
never compares the installed version with the tag.

Keeping a second version source also means a branch build always
packages the last release tag instead of the branch, so the RPM jobs
cannot validate unreleased code.

## What Changes

- Replace the literal `Version:` and `Release:` fields in both RPM
  specs with `@VERSION@` and `@RELEASE@` placeholders, and name the
  source tarball locally (`Source0: scantpaper-%{version}.tar.gz`).
- Add `dev/prepare_rpm.py`, shared by local and CI builds, to
  render the spec and create the source archive from a selected git
  ref with `git archive`.
- Take the version from `pyproject.toml` at that ref and derive the
  release as `0.<commit-count>.g<short-sha>%{?dist}`, for tagged and
  snapshot builds alike, so distro packages at `Release: 1` sort above
  upstream artifacts and no epoch is needed.
- Generate the RPM `%changelog` entry from the source ref's commit date
  and the template's existing packager identity.
- Remove RPM spec mutation from `dev/release.py`, restoring its
  three-file scope, and replace the static spec-parity test with
  renderer and template tests.
- Update both RPM workflows to fetch full history, render the spec and
  archive, stop using `spectool` for ScantPaper, and accept an optional
  `source_ref` dispatch input so a published release can be rebuilt
  from its tag without moving it.
- Keep the installed `scantpaper --version` tag assertions, and recover
  the v3.0.24 assets by dispatching with `source_ref=v3.0.24`.
- Document the template/source-ref workflow and the release-ordering
  rule.

## Capabilities

### New Capabilities

- `packaging-version-parity`: RPM metadata and source are generated
  from the same git ref, identify that ref's project version, and sort
  below distro packages for the same upstream release.

### Modified Capabilities

None.

## Impact

- New `dev/prepare_rpm.py` and
  `src/scantpaper/tests/test_prepare_rpm.py`.
- `packaging/fedora/scantpaper.spec`,
  `packaging/opensuse/scantpaper.spec`,
  `packaging/opensuse/build.sh`.
- `.github/workflows/fedora.yml`, `.github/workflows/opensuse.yml`.
- `dev/release.py` and `src/scantpaper/tests/test_release.py` (RPM
  handling removed); `src/scantpaper/tests/test_packaging_versions.py`
  is replaced or removed.
- `release_procedure.md`, `packaging/opensuse/README.md`,
  `changelog.md`.
- No runtime/application code, no new dependencies. The v3.0.24
  release's RPM assets must be rebuilt and re-uploaded as a recovery
  step.
