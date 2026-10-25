# Proposal

## Why

The Debian workflow builds and uploads a `.deb` but never verifies that it
is installable or policy-clean: `debuild` happens to run the runner's
lintian, whose output nobody gates on, and `packaging/debian/tests/` is
never executed. The package is therefore published from a build that has
only proved the `.deb` could be assembled, not that it passes Debian's
checks or its own test suite.

Two defects keep a proper check from passing today:

- `debian/scantpaper.install` and `debian/source/include-binaries` reference
  `debian/screenshot.png`, which does not exist in the packaging tree, so
  `dh_install` aborts: "missing files". I reproduced this locally. The salsa
  tree carries that PNG separately; ours must not duplicate the upstream
  `screenshot.png`.
- The generated `documentation.html` embeds remote images from the README
  (the donation button and four badges). Lintian reports
  `E: privacy-breach-donation` and four `W: privacy-breach-generic`, so
  `--fail-on warning` exits 2 before any other check matters.

## What Changes

- Move the build job into the same `debian:sid-slim` container, so the
  `debhelper-compat (= 14)` the packaging now requires is available, and
  delete the `check-launchpad` job and the PPA from the workflow. Debian
  unstable provides every dependency, and the launchpad availability gate
  existed only for the PPA.
- Add a `debian-checks` job to `.github/workflows/deb.yml` that runs in a
  `debian:sid-slim` container, downloads the build job's upload, and runs
  `lintian --fail-on warning` followed by `autopkgtest` against the built
  `.deb`, with `debian/tests` taken from the rendered tree of the same git
  ref. Debian unstable resolves every dependency the package and tests
  declare, so this job needs no PPA.
- Upload the `.changes` and `.buildinfo` alongside the `.deb`, because
  linting the upload needs all three; and pass `--no-lintian` to `debuild`
  in the build job so the sid stage is the only lintian opinion in the
  workflow.
- Stop duplicating the upstream screenshot: install `screenshot.png` from
  the source root and delete `packaging/debian/scantpaper.install` (its
  remaining contents live in `install` and `scantpaper.docs`) and
  `packaging/debian/source/include-binaries`.
- Remove the remote images from the generated `documentation.html` with a
  small tested helper, `dev/strip_remote_images.py`, called from
  `debian/rules` after pandoc. This fixes the privacy tags instead of
  overriding them, and the helper can be reused by the salsa packaging.
- Document the checks job, the sid testbed, and the no-duplication rule in
  `packaging/debian/README.md`; note the checks in `release_procedure.md`;
  add a `changelog.md` entry.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `debian-packaging`: the built upload is linted with `--fail-on warning`
  and tested with autopkgtest on Debian unstable; the generated
  documentation must not reference remote resources; and packaging files
  install a source-tree file by its source path rather than carrying a copy.

## Impact

- `.github/workflows/deb.yml`: new `debian-checks` job; build job uploads
  the upload triple and stops running lintian itself.
- `packaging/debian/`: `install` gains the screenshot; `scantpaper.install`
  and `source/include-binaries` are deleted; `rules` calls the new helper.
- `dev/strip_remote_images.py`: new build helper, used by both this tree and
  salsa; no runtime effect on the application.
- `src/scantpaper/tests/test_strip_remote_images.py`: new.
- `packaging/debian/README.md`, `release_procedure.md`, `changelog.md`:
  updated.
- No change to application code, runtime dependencies, CLI, UI or session
  format. The GitHub `.deb` is now built and checked on Debian unstable
  rather than Ubuntu; its package metadata is unchanged, and Ubuntu users
  still get their dependencies from the PPA at install time.
