# Design

## Context

See `proposal.md` - Why. The constraints that shape the approach:

- `dev/` is deliberately not a Python package (see AGENTS.md), so the
  existing `dev/prepare_rpm.py` cannot be imported as a module. Dev scripts
  are executed by path.
- `dpkg-buildpackage`/`debuild` only read `debian/` at the root of the source
  tree; there is no build-directory option.
- `.gitignore` is tracked, the repository has no `.gitattributes`
  `export-ignore`, and `git archive` output ships to the salsa packaging repo.
  A root `/debian/` ignore rule would hide newly added files there.
- `pyproject.toml` is the only stored project version; `dev/release.py` owns
  the three release files and does not touch packaging.
- The RPM renderer already implements the git plumbing this needs: version at
  a ref, tag assertion, commit count, commit timestamp, locale-independent
  dates, temp-file-then-replace writes.

## Goals / Non-Goals

**Goals:**

- Make the Debian recipe a reviewable, testable, locally reproducible artifact
  with the same properties as the RPM specs.
- Keep the repository root free of a generated `debian/` directory without
  changing `.gitignore`.
- Give the Debian package the same version-identity guarantees as the RPMs.

**Non-Goals:**

- Automating or syncing the salsa packaging repository.
- Running `lintian` as a CI gate, signing packages, or building source
  packages/DSCs for upload.
- Changing package contents, dependencies, package name, or the PPA matrix.
- Sharing code between the two renderers.

## Decisions

### Decision: a sibling renderer, not a shared module

Add `dev/prepare_deb.py` beside `dev/prepare_rpm.py`. Both are plain scripts
run by path, so a shared helper would need `dev/` to become a package or
require `sys.path` manipulation, contradicting AGENTS.md. The duplicated part
is only the git plumbing (version at a ref, tag check, commit count and date);
the outputs - an RPM spec plus a tarball versus a source tree plus a changelog
- have nothing in common beyond that.

Alternatives rejected:

- Extend `prepare_rpm.py` with a Debian mode: one script with two output
  formats and two changelog grammars is harder to test than two focused ones.
- Put the renderer under `src/scantpaper/`: it is release tooling, not
  installed application code.

### Decision: templates keep their real names; only the changelog is templated

`packaging/debian/` mirrors the `debian/` layout exactly (`control`,
`copyright`, `rules`, `scantpaper.install`, `scantpaper.manpages`, `watch`,
`upstream/metadata`, `source/format`), with real filenames and no `.in`
suffix, matching the decision already taken for the RPM specs. Only
`changelog` carries `@VERSION@` plus the generated date and text.

`control` stays fully static. It contains no version, no build-variable field
that is actually varied, and `Architecture: all` is what every build has used
(`DEB_ARCHITECTURE` in the current workflow is never set). The
`${GITHUB_REPO_NAME}`, `${AUTHOR}`, `${HOMEPAGE:-...}` and
`${DEB_ARCHITECTURE}` expansions disappear rather than becoming placeholders;
if a second architecture is ever needed, a placeholder can be added then.

### Decision: build in a scratch tree materialised from the ref

`dev/prepare_deb.py` streams `git archive <ref>` into
`build/deb/scantpaper-<version>/` with Python's `tarfile` (data filter so
exported modes are normalised but the executable bit is kept), copies the
template tree into `<tree>/debian/`, renders the changelog there, and ensures
`debian/rules` is `0755`. The Debian build is then run from that directory.

This is the option that removes the `.gitignore` problem rather than working
around it, gives the empty-source guarantee the RPM tarball has (uncommitted
files cannot leak into a local package), and makes `source_ref` rebuilds
possible. `build/deb/` is already ignored by the unanchored `build/` rule, so
no ignore file changes at all.

Alternatives rejected:

- Render into `<repo>/debian/` and add the path to `.git/info/exclude`: works,
  but every clone must opt in, and CI and a developer machine would then
  behave differently.
- Render into `<repo>/debian/` and add `/debian/` to `.gitignore` guarded by
  `.gitattributes` `export-ignore`: adds a second mechanism whose only purpose
  is to make a shipping ignore line harmless, and changes what every upstream
  tarball contains.
- Build in `mktemp -d`: nothing to inspect after a local build and no stable
  CI path. `build/deb/` gives both.

The rendered tree is produced in a temporary sibling directory and swapped
into place, so a failure leaves no half-written packaging, matching the
all-or-nothing behaviour of the RPM renderer.

### Decision: one version scheme, `<version>-0.<commit-count>.g<short-sha>`

The same for tag and branch builds, mirroring the RPM `Release:` field.
Verified with `dpkg --compare-versions`:

```text
within 4.0.1:
  4.0.1-0.499.g<sha>  <  4.0.1-0.500.g<tag-sha>  <  4.0.1-0.501.g<sha>
across versions:
  4.0.1-0.501.g<sha>  <  4.0.2-0.530.g<sha>
below the distro:
  4.0.1-0.501.g<sha>  <  4.0.1-1
```

Consequences:

- A later snapshot sorts above the tag build, and every upstream build stays
  below a distro package at revision `1` with no epoch.
- The same commit always renders the same version, whether or not its tag
  exists, so a tag rebuild is identical to the original tag build.
- The release asset looks like a snapshot (`-0.500.gabc1234`), which is
  accepted; that is precisely what it is, and it is traceable to a commit.
- `-0~ppa1noble` still sorts below `-0.500`, so a GitHub `.deb` outranks a PPA
  build of the same version. A user switching to the PPA package would need
  `--allow-downgrades`; the two are not offered from one repository.

Alternatives rejected:

- `-0` for tag builds and `-0.<count>.g<sha>` for snapshots: satisfies the
  ordering rule, but the same commit then has two identities depending on
  whether its tag exists, which is exactly the ambiguity the RPM change
  removed.
- `<version>+<sha>-0`, today's branch format: sorts *above* `<version>-1`, so a
  CI artifact would beat the distro package.
- Debian-native `~` snapshots (`<version>~git...-0`): sorts below the release
  instead of above it, which is the opposite of the required ordering.

### Decision: commit timestamp, formatted for Debian

The changelog date is the selected ref's commit date in Debian changelog form,
formatted with fixed English weekday and month tables as the RPM renderer does.
This makes rendering byte-identical across machines and locales, and keeps the
`SOURCE_DATE_EPOCH` that `dpkg-buildpackage` derives from the changelog stable,
so the same commit produces the same binary package bytes.

Alternatives rejected: `date --rfc-email` (wall clock, not reproducible);
`SOURCE_DATE_EPOCH` from the environment (absent locally, so local and CI
output would differ).

### Decision: the renderer owns the version, the workflow asks for it

The renderer prints the rendered version on success, and the workflow exports
that to `GITHUB_ENV` instead of re-deriving it from `GITHUB_REF_NAME`. One
source of the version removes the current three-branch shell logic (tag,
branch, non-numeric tag) and the tag/version mismatch that logic never
checked. The renderer keeps the RPM renderer's guards: refuse a shallow clone,
and fail before writing anything if a `v<version>` tag disagrees with
`pyproject.toml`.

### Decision: workflow order and scope

`render -> mk-build-deps -> debuild` in the scratch tree, because
`mk-build-deps` and `configure` both read the rendered `control`. The checkout
uses `fetch-depth: 0`, and `debuild` runs inside
`build/deb/scantpaper-<version>` so the `.deb` lands in `build/deb/`, which the
upload and release steps use. `pull_request` and `workflow_dispatch` with an
optional `source_ref` are added, matching the RPM workflows. The
launchpad-reachability gate and the PPA-provided build dependencies are left
alone.

### Decision: tests mirror the RPM test pair

- `src/scantpaper/tests/test_packaging_versions.py` additionally asserts the
  changelog template contains `@VERSION@` and no literal version, and that
  `packaging/debian/rules` is executable in git.
- New `src/scantpaper/tests/test_prepare_deb.py` builds a throwaway git repo
  like `test_prepare_rpm.py` and covers: branch and tag rendering, tag/version
  mismatch, missing placeholder, shallow history, exclusion of modified and
  untracked files, executable `rules` in the rendered tree, locale-independent
  date, and no output on failure.
- A rendered-tree test asserts the generated file set is exactly the template
  set plus one changelog, and that `deb.yml` contains no heredoc, so a
  reintroduced inline file fails the suite.

## Risks / Trade-offs

- [Release asset names change] -> Noted as breaking in the proposal and the
  changelog; the version is printed by the renderer so downstream steps use
  the new name automatically.
- [A local build no longer packages uncommitted edits] -> Documented in
  `packaging/debian/README.md`; a developer can commit to a scratch branch or
  change the ref. This is the price of the empty-source guarantee.
- [`build/` is an unanchored ignore rule] -> If a tracked directory named
  `build` is ever added, the scratch tree becomes invisible to git. Low risk;
  the renderer fails loudly if the archive output lands on a tracked path.
- [`git archive` excludes submodules, LFS content and `export-ignore` paths]
  -> The repository has none today. If one is added, the renderer tests must
  cover it, as with the RPM archive.
- [The scratch tree adds a step before `mk-build-deps`] -> Build dependencies
  are only installed after rendering, so a renderer failure fails fast and
  cheaply, before the slow dependency install.
- [Two packaging trees can drift] -> Out of scope by design; the README states
  which one is authoritative, and a drift check against salsa is a later,
  separate change.
- [The GitHub `.deb` outranks the PPA build of the same version] -> They are
  not published from one repository; documented as a switching caveat.
- [The launchpad gate still blocks a tag build when launchpad is down] ->
  Unchanged and out of scope.

## Migration Plan

1. Add `packaging/debian/`, the renderer and the tests; convert the template
   tests.
2. Rewrite `.github/workflows/deb.yml` to render and build in `build/deb/`.
3. Update `packaging/debian/README.md`, `release_procedure.md` and
   `changelog.md`.
4. Run `pytest`, `ruff format --check`, `ruff check`, `ty check .`, and render
   plus `debuild` locally for inspection; run `lintian` on the result without
   making it a gate yet.
5. Push a branch first: the new `pull_request` trigger proves the workflow on
   the change itself before any tag is cut.
6. Rollback is a revert of the change. No tag is moved and no published asset
   is replaced.

## Open Questions

- Should `lintian` become a gate once the rendered tree is available? Left
  open until a run shows whether the current package is lintian-clean enough.
- Should the GitHub `.deb` be documented in the README install section? Today
  the README names only Debian/sid and the PPA, so the asset is undocumented
  either way.
- Is a drift check against salsa worth building next? It needs no change to
  this design or these specs.
