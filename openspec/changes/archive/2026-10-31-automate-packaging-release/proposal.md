# Proposal

## Why

The Debian and Ubuntu release steps are still a hand-run sequence: copy the
packaging files into the salsa checkout, notice what changed, word a changelog
entry, then build and upload the same source once for Debian and once per
Ubuntu series. The salsa worktree carries exactly such an uncommitted copy
today, made by hand, and the last three packaging changes - the
screenshot/install cleanup, the test dependency declarations, and debhelper 14 -
each had to be mirrored into it manually.

Two parts are slow and easy to get wrong: the changelog has to say what changed
in `debian/`, and the Ubuntu source package has to be adjusted per series
before every upload. Both are mechanical enough to draft automatically and
small enough to review.

The copy model only became possible now. The `privacy` patch is superseded by
`dev/strip_remote_images.py`, and the `rpm_tests` patch deletes a test that now
skips when git is absent and passes when git is present. With both gone,
salsa's `debian/` can be the upstream packaging plus a changelog.

## What Changes

- Make the two packaging trees identical except for the changelog: adopt
  salsa's `Maintainer`, `Uploaders`, `Vcs-Git` and `Vcs-Browser` in
  `packaging/debian/control`, move `debian/clean` into `packaging/debian/`, and
  delete `debian/patches/{privacy,rpm_tests,series}` from the salsa
  repository.
- Add `dev/sync_salsa.py`, run in the salsa checkout after
  `gbp import-orig`: copy the shared packaging into `debian/`, delete stale
  shared files, keep `debian/changelog`, and fail if any other file remains, so
  a stray patch or leftover is caught rather than silently preserved. Draft a
  changelog entry from the file, dependency and rules diff; leave the text for
  editing and print the build, test, commit and upload commands instead of
  running them.
- Add `dev/build_ppa.py` and `packaging/ubuntu/suites.toml`: for each selected
  series, build a source package in a throwaway tree with that
  series' `debhelper-compat` (13 for jammy, noble and resolute; 14 for
  stonking), version `<upstream>-0~ppa1<series>` and `Distribution: <series>`,
  reusing the pristine-tar orig tarball. The matrix may also drop a test
  dependency a series does not carry (jammy has no `jbig2` encoder). Print the
  `dput` command and never run it.
- Update `release_procedure.md` to use the two tools, and add a `changelog.md`
  entry.

## Capabilities

### New Capabilities

- `packaging-release`: copies the shared Debian packaging into the salsa tree
  with a drafted changelog, and generates per-series Ubuntu PPA source packages
  from a suite matrix, leaving commits, signing decisions and uploads to the
  maintainer.

### Modified Capabilities

None.

## Impact

- `packaging/debian/control`: the identity fields become the Debian Python
  Team and salsa URLs, so the GitHub `.deb` reports the team as maintainer.
  `Uploaders` and `Vcs-*` are source-only fields, so the binary is otherwise
  unchanged and nothing about the build or its dependencies moves.
- `packaging/debian/clean`: new shared file.
- `dev/sync_salsa.py`, `dev/build_ppa.py`, `packaging/ubuntu/suites.toml`: new
  tooling; run in the salsa checkout, no runtime effect on the application.
- Salsa repository: the two patches and their series entry are deleted; no
  other change is needed, because the sync produces the rest and fails if
  anything other than the changelog is left over.
- Tests: new tests for the diff drafting, the copy-and-verify step and the
  suite matrix rendering.
- `release_procedure.md`, `changelog.md`: updated.
- No change to application code, dependencies, CLI, UI, session format, the
  GitHub `.deb` build, or the Debian source format. Uploads, commits, tags and
  signing remain manual.
