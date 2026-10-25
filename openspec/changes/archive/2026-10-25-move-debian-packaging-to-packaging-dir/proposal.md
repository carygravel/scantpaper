# Proposal

## Why

The Debian build is the only packaging recipe in the repository that is not
*in* the repository: `.github/workflows/deb.yml` writes nine files under
`debian/` with shell heredocs on every run. Those files cannot be reviewed as
a diff, linted, tested, or reproduced outside CI, and this is the last
packaging tree still outside the model that `fix-rpm-release-version`
established - `packaging/<distro>/` templates plus a renderer that reads the
selected git ref. That change named `packaging/debian/` as its deferred
follow-up.

Two defects follow from the current arrangement.

**Version identity.** A push to `main` produces `4.0.1+<full-sha>-0`, which
`dpkg` orders *above* Debian's own `4.0.1-1`, so a CI artifact outranks the
distro package for the same upstream release. A tag build is never checked
against `pyproject.toml`, so a mistyped tag silently produces a mislabelled
package. Two different commits can claim the same `-0` version. This is the
same class of bug the RPM change fixed, using the same remedy.

**Build location.** `dpkg-buildpackage` only reads `debian/` at the root of
the source tree, so the generated tree lands there. The obvious remedy,
adding `/debian/` to `.gitignore`, is unsafe: `.gitignore` is tracked, the
repository has no `export-ignore`, so it ships in the source tarball that the
salsa packaging repository imports. A root `/debian/` ignore rule there would
hide every newly added file in the directory the packager works in.

## What Changes

- Add a committed `packaging/debian/` tree: `control`, `copyright`, `rules`,
  `scantpaper.install`, `scantpaper.manpages`, `watch`,
  `upstream/metadata`, `source/format`, a `changelog` template, and a
  `README.md`. `rules` stays a native, unrendered makefile and is committed
  executable (policy 4.9; the current heredoc loses the bit).
- Add `dev/prepare_deb.py`, a renderer beside `dev/prepare_rpm.py`. It reads
  the version from `pyproject.toml` at the selected ref, asserts that a
  `v<version>` tag agrees with it, derives
  `<version>-0.<commit-count>.g<short-sha>`, and stamps a single changelog
  entry dated from the commit (not the wall
  clock), so the same commit renders the same packaging and
  `SOURCE_DATE_EPOCH` is stable.
- Build in a throwaway tree: the renderer materialises `git archive <ref>`
  under `build/deb/scantpaper-<version>/`, copies and renders the templates
  into its `debian/`, and the workflow runs `debuild` there. Nothing is
  created at the repository root, so **`.gitignore` is not changed** - the
  existing `build/` rule already covers the scratch tree.
- Rewrite `.github/workflows/deb.yml`: delete the heredoc block and the
  unused `FIRST_YEAR`/`THIS_COMMIT_YEAR`/`THIS_COMMIT_DATE`/`YEAR_RANGE`
  computation and the never-set `HOMEPAGE` expansion; check out full history
  (`fetch-depth: 0`) because the revision needs the commit count; render
  before installing build dependencies, since `mk-build-deps` reads the
  rendered `control`; and add `pull_request` and `workflow_dispatch` (with an
  optional `source_ref`, matching the RPM workflows) so packaging changes and
  release rebuilds are possible.
- Update the artifact and release paths to `build/deb/*.deb` and the
  `-0.*` version glob.
- Extend `src/scantpaper/tests/test_packaging_versions.py` so the Debian
  template cannot contain a literal version, and add
  `src/scantpaper/tests/test_prepare_deb.py` mirroring the RPM renderer
  tests (tag mismatch, missing placeholder, shallow history, unmodified
  output on failure, locale-independent date, executable `rules`).
- Document the rendered tree, the local build commands, and the relationship
  to salsa in `packaging/debian/README.md`; note the scratch build and the
  `.gitignore` constraint in `release_procedure.md`; add a `changelog.md`
  entry.
- **BREAKING** for anyone scripting the release asset name: GitHub `.deb`
  versions change from `<version>-0` (and `<version>+<full-sha>-0` on
  branches) to `<version>-0.<commit-count>.g<short-sha>`.

The salsa `debian/` tree remains authoritative for the Debian and Ubuntu
packaging; this change only makes the GitHub release artifact reproducible and
reviewable. Automating salsa from the same tree is deliberately out of scope.

## Capabilities

### New Capabilities

- `debian-packaging`: the Debian build recipe is version-controlled and
  rendered into a throwaway build tree, using native, executable packaging
  files, with no `debian/` directory at the repository root and no
  `.gitignore` rule that would follow the source into the salsa packaging
  repository.

### Modified Capabilities

- `packaging-version-parity`: version identity and ordering requirements
  extended from RPM to the Debian package (placeholder version rendered from
  the selected ref, tag agreement, commit-date changelog, rebuild from a
  published tag, upstream build below the distro package), and the existing
  "committed packaging specs" requirement scoped to the RPM specs so it is
  not read as applying to the Debian files.

## Impact

- `.github/workflows/deb.yml`: heredoc block, version computation and build
  paths replaced; triggers and checkout depth changed.
- `packaging/debian/`: new tracked tree; `packaging/debian/README.md` new.
- `dev/prepare_deb.py`: new renderer, no runtime effect on the application.
- `src/scantpaper/tests/test_prepare_deb.py`: new; `test_packaging_versions.py`
  extended.
- `release_procedure.md`, `changelog.md`: updated.
- `.gitignore`: deliberately unchanged.
- No change to application code, runtime dependencies, CLI, UI, session
  format, or the translation workflow. `README.md` install instructions are
  unaffected because they document the Debian/sid and PPA packages, not the
  GitHub `.deb` asset.
