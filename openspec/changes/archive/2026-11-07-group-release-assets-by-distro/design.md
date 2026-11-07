# Design

## Context

See `proposal.md` for motivation and the `release-assets` spec for the
behaviour contract.

- Five independent release steps publish assets: `test.yml` (wheel),
  `deb.yml` (`.deb`), `fedora.yml` (matrix 43/44), `opensuse.yml` (Leap
  16.0) and `opensuse-tumbleweed.yml`. Each calls
  `softprops/action-gh-release` under `github.ref_type == 'tag'`; there is
  no coordinator, so whichever job finishes first creates the release and
  the rest append assets.
- GitHub release assets are flat, name-sorted and cannot be grouped into
  directories. Asset labels can replace a row's text but do not reorder the
  list, so grouping has to come from the file names or from the archive set.
- Fedora copies every RPM from `~/rpmbuild/RPMS`, including `-debuginfo`
  and `-debugsource`. openSUSE already has `collect-runtime`, which leaves
  only the runtime set.
- The release body is empty today. Only the body can carry the Downloads
  explanation.
- The RPM workflows do not expose a `VERSION` environment variable today.
  The builder can read the version from the built application RPM, which
  also works on branch and pull-request builds.

## Goals / Non-Goals

**Goals:**

- Make every RPM target one download with one install command.
- Remove debug packages and build-only helpers from release assets.
- Put a short, durable Downloads explanation on every tag release.
- Keep the `.deb`, the wheel and every RPM's internal metadata unchanged.
- Keep the existing CI artifact uploads available for troubleshooting.

**Non-Goals:**

- Moving to COPR, OBS, PyPI or another native repository.
- Signing the RPMs or adding a repository metadata index.
- Generating full release notes from the changelog or commit history.
- Merging the independent workflows into one coordinated release pipeline.
- Renaming RPMs or changing the RPM specs' build behaviour.
- Bundling the `.deb` or the wheel, which are already single files.

## Decisions

### One archive per target

Each target gets exactly one archive named
`scantpaper-<version>-<target>.tar.gz`, with target ids `fedora-43`,
`fedora-44`, `opensuse-leap-16.0` and `opensuse-tumbleweed`. The archive
extracts to a top-level directory with the same stem, then the RPMs,
`SHA256SUMS` and `INSTALL.txt`.

Alternative: prefix every individual RPM with its target. Rejected because
it breaks the canonical `name-version-release.arch.rpm` form and does not
reduce the number of assets.

### Shared bundle builder

Add `dev/make_release_bundle.py`, which accepts `--target`, `--input`,
`--output` and an optional `--version`. It validates the target, finds the
built `scantpaper-*.rpm`, derives the version from its filename when
`--version` is absent, rejects `-debuginfo` and `-debugsource` members,
requires the application RPM, stages the directory, writes `INSTALL.txt`
and `SHA256SUMS`, and creates the `.tar.gz`.

Alternative: inline `tar`, `sha256sum` and install-note text in each
workflow. Rejected because four copies would drift in naming, filtering
and checksum handling.

### Feed the builder the existing runtime directory

- Fedora keeps copying every RPM into `artifacts/` for the CI artifact,
  then the builder filters the release bundle from that directory.
- Leap and Tumbleweed keep `collect-runtime artifacts`, which already
  excludes debug and build-only helpers, then the builder packages that
  directory.

Alternative: suppress debug package generation in the Fedora specs.
Rejected because it changes the build and removes an artifact that is
occasionally useful; filtering at publication is enough.

### Canonical RPM names inside the archive

The target identity lives in the archive name, so `rpm -qp`,
`dnf install` and the existing packaging documentation keep working.

Alternative: rename RPMs with a target prefix inside the archive. Rejected
because the archive already disambiguates the target, and renaming would
only make the contents unfamiliar.

### Static release body

Add `.github/release-notes.md` and pass it as `body_path` from all five
release steps. The text uses archive patterns and shell globs rather than
full versioned filenames or direct download links. It gives the Fedora and
openSUSE commands, including `--allow-unsigned-rpm`, routes Debian and
Ubuntu users to apt and the PPA, and links to the README.

Alternative: generate the body per release with exact names and links.
Rejected because the five jobs have no ordering guarantee, a failed bundle
would leave a broken link, and the generator would have to stay in sync
with every workflow.

Alternative: let one workflow own the body. Rejected because the jobs run
independently; relying on the others to omit the field is an implicit
contract that is easy to break.

### Archive layout and checksums

The archive contains the runtime RPMs, `SHA256SUMS` covering every RPM,
and `INSTALL.txt` with the one-transaction command. `INSTALL.txt` can use
`cd <directory>` and `./*.rpm`, so it needs no version-specific text.

Tar members are sorted, with fixed ownership and mtime, for a stable member
order. Byte-for-byte reproducibility is not claimed because the RPMs
themselves may carry build metadata.

### Version source

The builder derives the version from the built `scantpaper-<version>-...`
RPM filename. `--version` remains an override for tests or unusual inputs.
This makes the bundle step runnable on pull requests and branch pushes,
where `github.ref_name` is not a release version, and avoids adding a
second version source to the RPM workflows. The existing tag-verification
step remains the release-time assertion.

### Release body content

The body has a short introduction, one command block per RPM target, a
note that the `.deb` and `.whl` are single files, and a link to the
installation guide. Fedora uses a `FEDORA=43` or `FEDORA=44` variable so
one block covers both. The asset list below the body remains the
authoritative list of what was actually built.

### Documentation and procedure

- `README.md`: download and extract the archive for Fedora, Leap and
  Tumbleweed; remove the `.lp160.1` selection rule.
- `packaging/opensuse/README.md`: the published artifact is the archive
  containing the `collect-runtime` set.
- `release_procedure.md`: a rebuilt release replaces one archive per
  target; the body stays static.

### Tests

- `dev/tests/test_make_release_bundle.py`: unsupported target, debug
  exclusion, required application RPM, layout, checksums, install-note
  command, stable member order and output name.
- `src/scantpaper/tests/test_release_assets.py`: each workflow calls the
  builder for every target, all five release steps pass `body_path`, the
  tag guard remains, and the body names every target and the unsigned-RPM
  flag. A matrix change must fail until the builder and body agree.
- Existing workflow assertions in `test_packaging_opensuse.py` keep their
  CI artifact names; the release asset assertions move to the new test.

## Risks / Trade-offs

- **Breaking asset URLs** -> the README and release procedure change in
  the same change, old releases keep their flat assets, and the proposal
  marks the change as breaking.
- **A bundle misses a dependency** -> the existing clean-room install jobs
  still install the published set; the builder requires the application
  RPM and verifies every surviving RPM is listed in `SHA256SUMS`.
- **The body promises an archive that failed to build** -> the body uses
  patterns rather than links, so the asset list remains authoritative.
- **Last writer wins on the body** -> every release step uses the same
  checked-in file; a test asserts all five steps set `body_path`.
- **Debug packages are no longer release assets** -> the existing CI
  artifact uploads still contain them for troubleshooting.
- **Target list drift** -> the builder rejects unknown targets and the
  tests compare the supported set with the workflow matrix and the body.
- **Manual rebuilds** -> replacing one archive replaces the whole target's
  set, and `INSTALL.txt` and `SHA256SUMS` travel with it.

## Migration Plan

There is no data migration. The next tag publishes archives; older
releases keep their individual assets. README, the openSUSE packaging
README and the release procedure are updated in the same change. Rollback
reverts the workflow and documentation edits; a release already published
with archives would need its individual RPMs re-uploaded if the old layout
had to be restored.

## Open Questions

- Whether to set the release title to `ScantPaper <version>` instead of
  the bare tag. This is deferrable and does not change the specs or tasks.
- Whether the body should also link to the changelog section for the
  release. The proposal leaves full release notes out of scope.
