# Tasks

## 1. Converge the packaging

- [x] 1.1 Adopt salsa's `Maintainer`, `Uploaders`, `Vcs-Git` and `Vcs-Browser`
  in `packaging/debian/control`, move `debian/clean` upstream as
  `packaging/debian/clean`, and verify the GitHub artifact still renders,
  builds and passes `lintian --fail-on warning` with the new control
- [x] 1.2 In the salsa checkout, delete `debian/patches/privacy`,
  `debian/patches/rpm_tests` and `debian/patches/series`; verify `git status`
  shows only that deletion and `debian/` still builds a source package

## 2. Suite matrix

- [x] 2.1 Add `packaging/ubuntu/suites.toml` with stonking (compat 14),
  resolute (13), noble (13) and jammy (13, dropping `jbig2` from the test
  dependencies); verify every value against
  `apt-cache show debhelper` in `ubuntu:<series>`

## 3. Sync tool

- [x] 3.1 Implement the copy in `dev/sync_salsa.py`: shared-file copy from
  `packaging/debian/`, deletion of stale shared files, preservation of
  `debian/changelog`, and failure naming any other leftover; cover the copy,
  deletion, leftover and wrong-checkout cases in `test_sync_salsa.py` and
  verify with `pytest src/scantpaper/tests/test_sync_salsa.py`
- [x] 3.2 Implement changelog drafting: upstream version from
  `pyproject.toml`, `-1` or incremented revision, `unstable`, the midnight UTC
  default with `--date`/`SOURCE_DATE_EPOCH`, and bullets for added/removed
  files, dependency changes and rules changes; verify each bullet class in the
  tests
- [x] 3.3 Add `--dry-run` and the printed build, test, commit and upload
  commands; verify a dry run writes nothing and a real run creates no commit,
  tag or upload

## 4. PPA tool

- [x] 4.1 Implement matrix loading and per-series rewriting in
  `dev/build_ppa.py`: `<upstream>-0~ppa1<series>`, `Distribution: <series>`,
  the series' compat and `drop-test-depends`; verify the generated changelog,
  control and `tests/control` in tests
- [x] 4.2 Build each series from a throwaway tree of the committed branch with the pristine-tar
  orig tarball, `debuild -S -us -uc -sa`, output under `build/ppa/<series>/`,
  printed `debsign`/`dput`, and the tree removed; verify a noble source
  package builds and the salsa working tree is unchanged
- [x] 4.3 Implement `--verify` against `ubuntu:<series>` and verify it fails,
  naming the series, when the matrix carries a compat the series' `debhelper`
  does not provide

## 5. Documentation and integration

- [x] 5.1 Replace the Debian and Ubuntu steps in `release_procedure.md` with
  the two tools, and add a `changelog.md` entry; verify the documented
  commands match the implemented interfaces
- [x] 5.2 Run `pytest`, `ruff format --check`, `ruff check` and `ty check .`;
  verify all pass and coverage stays at or above the gate
- [x] 5.3 On a scratch salsa clone, sync a packaging change, build the Debian
  source package and build all four PPA source packages unsigned; verify no
  upload or commit happened and the salsa tree is unchanged apart from the
  sync

## Workflow follow-up

- Commit and push the salsa sync, sign and upload the Debian source, then sign
  and upload the PPA sources for each series.
- Archive the change after the project's review requirements are satisfied.
