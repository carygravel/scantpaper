## Why

The release procedure requires manually editing the version in `pyproject.toml`,
adding a dated `<release>` entry to `org.scantpaper.desktop.metainfo.xml`, and
dating the unreleased section of `changelog.md`. Doing this by hand invites
typos and, in particular, lets the changelog date drift out of sync with the
metainfo date, since the two are written independently.

## What Changes

- Add a developer script (`dev/release.py`) that prepares the three version
  files for a release:
  - stamps the current `## X.Y.Z (unreleased)` heading in `changelog.md` with
    the release date,
  - bumps `[project] version` in `pyproject.toml`,
  - inserts `<release version="X.Y.Z" date="YYYY-MM-DD" />` as the first
    entry of `<releases>` in `org.scantpaper.desktop.metainfo.xml`.
- The changelog date and the metainfo date come from a single resolved date
  value, guaranteeing they match.
- The release version is derived from the changelog's `(unreleased)` heading,
  optionally overridden by `--version`; a mismatch is rejected.
- The script writes the three files only after all transformations validate
  (all-or-nothing), and supports `--dry-run`.
- The script does **not** touch git and does **not** run `generate_pot.py`; the
  commit, tag, push and translation-template steps remain manual.
- Update `release_procedure.md` so the version steps point at the script.

## Capabilities

### New Capabilities

- `release-tooling`: Preparing the release version across `pyproject.toml`,
  `changelog.md` and the AppStream metainfo file with a single, consistent
  release date.

### Modified Capabilities

<!-- None: no existing spec's requirements change. -->

## Impact

- New file: `dev/release.py`.
- New test: `src/scantpaper/tests/test_release.py`.
- Modified docs: `release_procedure.md` (version steps reference the script).
- Written by the script at release time: `pyproject.toml`, `changelog.md`,
  `org.scantpaper.desktop.metainfo.xml`.
- No runtime/application code, no new dependencies, no packaging changes.
