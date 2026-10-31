# Proposal

## Why

Tumbleweed users have no prebuilt ScantPaper RPM artifact. The repository
builds Leap 16 RPMs by rebuilding nine Python dependencies that Leap lacks,
but Tumbleweed already packages all of them, at versions equal to or newer
than the pinned local builds (verified against the 20261028 Tumbleweed
snapshot). The extension is therefore mostly a dependency-strategy and CI
problem, not new packaging work. Without it, Tumbleweed users must install
from a wheel and assemble the native libraries themselves.

## What Changes

- Add a Tumbleweed target to the openSUSE build driver. On Tumbleweed it
  builds only ScantPaper and the locally patched `python-sane`; every other
  Python dependency comes from the Tumbleweed repositories instead of the
  nine-package rebuild chain used on Leap.
- Make the release suffix distro-aware: a Tumbleweed build MUST NOT carry the
  Leap `.lp160.1` suffix.
- Express the Tumbleweed dependencies through the unversioned `python3-*`
  provides, so the build follows Tumbleweed's default Python instead of
  pinning `python313-*`. Both Leap 16 and Tumbleweed currently default to
  3.13, but Tumbleweed already builds a 3.14 flavor.
- Keep the `snap()` patch on Tumbleweed by shipping the patched `python-sane`
  built for Tumbleweed's default Python flavor, replacing the unpatched 2.9.2
  package. Preserve the distro's `python3-sane` and
  `python3dist(python-sane)` provides so other packages' requirements stay
  satisfiable. Upstreaming the patch is a separate follow-up; until it lands,
  a future Tumbleweed `python-sane` release will sort above the patched build
  and remove the fix.
- Add a Tumbleweed CI job on `opensuse/tumbleweed:latest` that builds the set,
  installs it in a clean container, runs `scantpaper --version`, imports the
  runtime modules, and asserts that the set installs without an unresolved
  `python3dist()` requirement.
- Run the Tumbleweed build with the same triggers as the other package
  builds: `push`, `pull_request` and `workflow_dispatch` with the existing
  `source_ref` input.
- Publish the Tumbleweed RPMs as a separate release artifact with distinct
  asset names, and document the Tumbleweed install command and the unchanged
  PostScript limitation (`tiff2ps` is absent from `tiff` 4.7.2 on both
  distributions).
- Leave the generated documentation and every other installed file identical
  to the Leap package. Enabling the HTML documentation that Tumbleweed's
  `pandoc` would allow is a separate change.

## Capabilities

### New Capabilities

- `opensuse-packaging`: Produces installable openSUSE RPM artifacts for Leap
  and Tumbleweed from one build driver, using each release's own dependency
  set, and validates the published set in a clean container.

### Modified Capabilities

None. The existing `packaging-version-parity` requirements already govern the
renderer and version scheme, and apply unchanged to a second RPM workflow.

## Impact

- `packaging/opensuse/build.sh`: target selection, dependency strategy and
  release-suffix handling.
- `packaging/opensuse/*.spec`: Tumbleweed package names and provides; no
  change to the Leap build.
- `.github/workflows/opensuse.yml` (or a sibling workflow): a Tumbleweed build
  and clean-room install job, plus separate release assets.
- `README.md`, `packaging/opensuse/README.md`, `release_procedure.md`:
  Tumbleweed install, rebuild and patch-caveat documentation.
- Tests: the build driver's target selection and the spec's dependency
  mapping.
- No application code, CLI, session format or existing Leap artifact changes.
