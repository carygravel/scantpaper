# Proposal

## Why

`v4.0.3` publishes 34 assets plus two generated source archives in one flat
list. Twelve of them are Fedora `-debuginfo`/`-debugsource` packages that no
user installs, and the Leap 16.0 and Tumbleweed RPMs differ only by a
`lp160.1` suffix or by nothing at all. The release page has no text, so a
user cannot tell which files form one installable set without reading the
README, and leaving out a rebuilt dependency turns the install into a
resolution error. Grouping each target into one archive makes the release
page a small, unambiguous menu and gives it a place to explain the choice.

## What Changes

- **BREAKING**: replace the per-RPM assets with one `.tar.gz` per
  distribution target: Fedora 43, Fedora 44, openSUSE Leap 16.0 and
  openSUSE Tumbleweed. Each archive contains the complete runtime RPM set
  under a versioned top-level directory, plus `SHA256SUMS` and
  `INSTALL.txt`. The `.deb` and `.whl` remain standalone assets.
- Stop publishing Fedora `-debuginfo` and `-debugsource` RPMs. They are not
  part of a user install and remain optional workflow artifacts for
  troubleshooting.
- Add a static Downloads section to every tag release. It explains the
  one-archive-per-target convention, gives copy-pasteable Fedora and
  openSUSE install commands, points Debian and Ubuntu users at apt and the
  PPA, and links to the README. It uses target names and wildcards rather
  than version-specific filenames, so the same text is correct for every
  release and every publishing job.
- Update the README install sections and `packaging/opensuse/README.md` to
  download and extract the archive. Remove the rule that picks Leap by its
  `.lp160.1` suffix. Update `release_procedure.md` so a rebuilt release
  replaces one archive per target.
- Leave package contents, RPM/DEB metadata, versions and dependency
  relationships unchanged. Only the published grouping and the release page
  presentation change.

## Capabilities

### New Capabilities

- `release-assets`: what a tagged GitHub release publishes, how each
  distribution's runtime set is grouped, which artifacts are excluded, and
  the Downloads text shown on the release page.

### Modified Capabilities

None. The existing `opensuse-packaging` requirement that the two targets'
published assets have distinct names still holds; the distinction moves
from individual RPM filenames to the archive names.

## Impact

- `.github/workflows/fedora.yml`: exclude debug packages from the published
  set and build and upload the Fedora 43/44 archive per matrix leg.
- `.github/workflows/opensuse.yml` and
  `.github/workflows/opensuse-tumbleweed.yml`: wrap the `collect-runtime`
  set in the target archive.
- `.github/workflows/deb.yml` and `.github/workflows/test.yml`: keep the
  single-file assets and attach the shared Downloads text to the release.
- A shared bundle builder (new `dev/` script) and a checked-in Markdown
  body for the release page, both tested. They use only the standard
  library and `tar`.
- `README.md`, `packaging/opensuse/README.md` and
  `release_procedure.md`: download, extract, install and rebuild steps.
- Tests: archive contents exclude debug packages and include the checksum
  and install note; the Downloads text names every target; workflow tags
  and release triggers stay unchanged. No runtime application code changes.
