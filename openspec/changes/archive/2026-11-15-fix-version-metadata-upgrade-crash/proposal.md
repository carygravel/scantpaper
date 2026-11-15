# Proposal

## Why

An openSUSE RPM upgrade leaves the previous release's version-named
`*.dist-info` directory behind, empty, because the generated `%files`
list owns only files and symlinks. `importlib.metadata.version("scantpaper")`
can then discover that empty directory first and return `None`;
`get_version()` passes it through, and `"%(prog)s " + VERSION` raises
`TypeError` before the main window opens. The application is unusable
after a routine upgrade, and the failure looks like "nothing happens"
when launched from Plasma. The 4.0.2 -> 4.0.3 and 4.0.3 -> 4.0.4 paths
both still have this defect.

## What Changes

- Make the running application's version lookup total: return a string
  even when the source `pyproject.toml` is absent, the installed
  metadata has no `Version:` header, or the distribution cannot be
  found.
- Recover the real version from the installed distribution metadata
  before falling back, so a stale empty `*.dist-info` directory does not
  force an "unknown" version.
- Keep version-based config migration safe when the version is unknown;
  only a missing version (an old config) is treated as legacy.
- Make the generated openSUSE `%files` list own the package's
  directories under site-packages, including the version-named
  `*.dist-info` directory, so an upgrade removes the previous one. Apply
  the same pattern to all ten openSUSE specs, which Leap and Tumbleweed
  share.
- Add CI checks on both openSUSE targets: assert the built RPM owns its
  `*.dist-info` directory, and run the installed application with an
  empty stale `*.dist-info` present.
- Document the one-line cleanup for users who already have a stale
  directory and cannot upgrade immediately.

No CLI, file-format or dependency changes.

### Platform coverage

- Leap 16.0 and 16.1: both the application fix and the openSUSE
  packaging fix apply. Leap 16.1 keeps Python 3.13 as its default
  interpreter and installs the Leap 16.0 RPM set.
- Tumbleweed: both fixes apply. The Tumbleweed build uses the same
  `packaging/opensuse/*.spec` templates and the same `build.sh` as Leap;
  only `TARGET` and the distro branches differ.
- Fedora: only the application fix applies. `%pyproject_save_files` and
  `%files -f %{pyproject_files}` already make RPM own the
  `*.dist-info` directory, so upgrades remove the previous one.
- Debian: only the application fix applies. `dpkg` tracks directories,
  so the `.deb` already cleans up the previous `*.dist-info` directory.

## Capabilities

### New Capabilities

- `application-version`: how the running application determines,
  validates and reports its version, including fallback behaviour when
  installed metadata is missing or malformed, and how an unknown version
  interacts with config migration.

### Modified Capabilities

- `opensuse-packaging`: the generated RPM file list must own the
  package's directories so an upgrade removes the previous version's
  `*.dist-info` directory; clean-room checks must cover a pre-existing
  stale metadata directory or a real upgrade.
- `config-loading`: a version-keyed migration must not re-run when the
  saved version string is unparseable, while a missing version continues
  to mean a legacy config.

## Impact

- `src/scantpaper/const.py`: `get_version()` and `VERSION`.
- `src/scantpaper/config.py`: `_version_tuple()` and the threshold
  migration guard.
- `src/scantpaper/tests/test_const.py`,
  `src/scantpaper/tests/test_8_config.py`: regression tests.
- `packaging/opensuse/*.spec` (ten specs): directory ownership in the
  generated `%files` list; `packaging/opensuse/README.md` records the
  rationale.
- `.github/workflows/opensuse.yml` and
  `.github/workflows/opensuse-tumbleweed.yml`: directory-ownership
  assertion and a stale-metadata clean-room check on each target (and/or
  an upgrade scenario).
- `README.md` and release notes: cleanup command for already-affected
  systems.
- New spec `openspec/specs/application-version/spec.md`; deltas for
  `openspec/specs/opensuse-packaging/spec.md` and
  `openspec/specs/config-loading/spec.md`.
- No dependencies added or removed.
