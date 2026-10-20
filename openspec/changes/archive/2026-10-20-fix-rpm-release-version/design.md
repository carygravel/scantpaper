## Context

See `proposal.md` for the incident and v3.0.24 asset evidence.

- Both specs currently declare `Version: 3.0.24`, `Release: 1%{?dist}`,
  and a `Source0` URL built from `v%{version}`. `dev/release.py`
  currently mutates both specs at release time.
- `.github/workflows/opensuse.yml` builds through
  `packaging/opensuse/build.sh`, which resolves `Source0` with
  `rpmspec` and downloads it with `curl`. The Fedora workflow copies
  the spec and downloads `Source0` with `spectool`.
- A branch build therefore always packages the last released tag. On
  the v3.0.24 release, the stale `Version:` made every RPM a v3.0.19
  build while the rest of the release was 3.0.24.
- The planned `packaging/debian/` directory will be copied into the
  source at build time and use a version placeholder. The RPM packaging
  should follow the same copy-and-substitute model instead of storing a
  second literal version.

## Goals / Non-Goals

**Goals:**

- Make `pyproject.toml` the only stored project version and render both
  RPM specs from it at build time.
- Build the RPM source from the exact git ref being tested, including
  branch and pull-request builds.
- Keep upstream RPMs below distro packages for the same release without
  an epoch.
- Make installed RPMs identify as the tag on tag builds, and allow a
  published release to be rebuilt from its tag without moving it.
- Recover the already-published v3.0.24 RPM assets.

**Non-Goals:**

- Producing a spec that can be submitted unchanged to Fedora or
  openSUSE; the generated spec uses a locally generated source archive.
- Maintaining a Debian-style patch series for unreleased commits.
- Signing RPMs, changing the rpmbuild toolchain, or changing package
  names or dependency metadata.
- Implementing `packaging/debian/`.

## Decisions

### Decision: render specs at build time, not release time

Both `scantpaper.spec` files become templates with `@VERSION@`,
`@RELEASE@`, and `@CHANGELOG@` placeholders. A shared
`dev/prepare_rpm.py` renders them into
`~/rpmbuild/SPECS/scantpaper.spec` and creates the source archive. The
template itself stays at the existing path so build scripts, globs and
review diffs keep working. The renderer lives in `dev/` beside the release
script, so it reuses the existing dev-script lint exemptions instead of
adding a new per-file ignore for `packaging/`.

This supersedes the interim release-time bump: `dev/release.py` returns
to its three-file scope (`pyproject.toml`, `changelog.md`, metainfo).
A release step that must remember a fifth and sixth file is the failure
mode being fixed, and a branch build would still package the last tag.

Alternatives rejected:

- A pre-commit hook: version changes belong at build time, not on every
  commit; local hooks are bypassable and cannot see the tag.
- A Debian-style tarball-plus-patch queue: a cumulative patch grows
  quickly, needs binary-diff handling, and retains the stale-tag source
  problem unless the patch applies cleanly to every build.
- Renaming the templates to `.spec.in`: it adds path churn without
  making the placeholder model easier to read or test.

### Decision: derive the version from the source ref

The renderer reads `[project] version` from `pyproject.toml` at the
selected git ref, not from the working tree and not from a tag. This
also lets a release commit be built before its tag exists.

When the selected ref is a `v<version>` tag, the renderer asserts that
the tag and `pyproject.toml` agree. A mismatch fails before writing
anything. The workflow's installed-command assertion remains the
end-to-end check for tag runs.

### Decision: use commit count in the release field

Both tagged and snapshot builds use:

```spec
Release: 0.<commit-count>.g<short-sha>%{?dist}
```

`commit-count` is `git rev-list --count <ref>` and `short-sha` is the
abbreviated commit id. Total count is monotonic as commits are added,
works locally and in CI, and needs no stored counter. The leading `0.`
keeps every upstream build below a distro package at `Release: 1` for
the same upstream version:

```text
3.0.24-0.512.g1b36963.fc43  <  3.0.24-1.fc43
```

No `Epoch` is added. An epoch would make the upstream RPM win over the
distro package and could not be overridden without the distro bumping
its own epoch. A GitHub `run_number` was rejected because it differs
between the Fedora and openSUSE workflows and does not exist for local
builds.

Consequences:

- A post-tag snapshot (`0.513`) sorts above the tag build (`0.512`).
  Only tagged builds may be published in a dnf repository; snapshots
  remain workflow artifacts.
- Force-pushing or rebasing can change the total count, so snapshots
  are not guaranteed to increase across a rewritten branch. Tagged
  releases change `Version`, so they are unaffected.
- A distro final package that itself uses `Release: 0` or `0.1` cannot
  be beaten by every `0.x` scheme; final distro packages normally use
  `1` or higher. If that edge case matters, do not publish both in the
  same repository.

### Decision: build the source with `git archive`

The renderer runs:

```sh
git archive --format=tar.gz \
    --prefix=scantpaper-<version>/ \
    -o <sources>/scantpaper-<version>.tar.gz <ref>
```

The generated spec declares `Source0: scantpaper-%{version}.tar.gz`,
and `%autosetup -n scantpaper-%{version}` is unchanged. No tag tarball
is fetched for ScantPaper.

This gives branch builds the branch's code and removes the network
dependency. The trade-offs are accepted:

- The source has no canonical upstream URL, so the generated spec is
  not directly suitable for distro submission.
- `git archive HEAD` excludes uncommitted and untracked files; local
  builds package the selected commit, not a dirty worktree.
- Submodules, Git LFS, and `.gitattributes export-ignore` would change
  the archive contents. The repository currently has none; if one is
  added, the renderer tests must cover it.

### Decision: generate the RPM changelog entry

The template keeps its historical `%changelog` entries and places
`@CHANGELOG@` immediately after the `%changelog` marker. The interim
`3.0.24-1` entry is removed during conversion because no such RPM was
published; the `3.0.19-1` entry remains as packaging history. The
renderer replaces the placeholder with one entry:

```text
* <Weekday Month DD YYYY> <packager> - <version>-<release>
- <Release <version>. | Snapshot build from commit <sha>.>
```

The packager identity is reused from the template's newest existing
entry. The date comes from the source ref's commit timestamp in UTC,
formatted with a fixed English weekday/month table so the output is
reproducible and locale-independent.

### Decision: workflows select a source ref

Both RPM workflows gain an optional `source_ref` dispatch input,
defaulting to `github.sha`. The renderer reads the version, archive,
commit count and date from that ref; the template and renderer come
from the workflow's checkout. Full history and tags are fetched with
`fetch-depth: 0`.

This is required for recovery: dispatching on `main` without a source
ref would archive current `main`, not the v3.0.24 tag. With
`source_ref=v3.0.24`, the build uses main's renderer and the tag's
source and metadata, without moving the tag.

The renderer refuses a shallow repository, because `git rev-list
--count` silently returns 1 there and would produce a misleading
release. The workflows must fetch full history.

## Risks / Trade-offs

- [A template is not directly buildable] -> The placeholders are
  invalid RPM values, so a direct `rpmbuild` fails loudly; the packaging
  READMEs document the renderer and the generated spec path.
- [Snapshots sort above the tag build in the same version] -> Publish
  only tag builds to repositories; keep snapshots as GitHub artifacts.
- [History rewrites change the release count] -> Tagged releases change
  `Version` and are unaffected; snapshots are not release artifacts.
- [A shallow checkout silently undercounts commits] -> The renderer
  detects a shallow repository and exits with an explicit error; CI
  sets `fetch-depth: 0`.
- [The generated archive is not the canonical GitHub tarball] -> The
  build packages the exact git tree and the tag assertion verifies the
  installed version; distro submission remains a separate concern.
- [Recovering an old tag with a newer template could fail if build steps
  diverge] -> Recover v3.0.24 immediately after this change; the app
  payload is the tag tree, and the release is not blocked by the
  absence of the old assets.
- [A distro package uses `Release: 0.x`] -> No universal lower release
  exists; do not publish upstream artifacts in the same repository in
  that case.

## Migration Plan

1. Add the renderer tests and implementation; convert both specs to
   templates.
2. Remove the spec mutation and its tests from `dev/release.py`;
   replace the static spec-parity test with template/renderer checks.
3. Wire the renderer into `packaging/opensuse/build.sh` and both
   workflows, including `fetch-depth: 0` and `source_ref`.
4. Update the release procedure, packaging READMEs and changelog.
5. Run `pytest`, `ruff format --check`, `ruff check`, `ty check .`, and
   render both specs locally for inspection.
6. Push the change, then dispatch both RPM workflows with
   `source_ref=v3.0.24` and replace the stale release assets.
7. Rollback is a revert of the change; already-replaced assets stay
   correct. No tag is moved at any point.
