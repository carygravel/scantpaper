# Tasks

## 1. Packaging fixes

- [x] 1.1 Add `screenshot.png usr/share/doc/scantpaper/` to
  `packaging/debian/install`, delete `packaging/debian/scantpaper.install`
  and `packaging/debian/source/include-binaries`, and verify by rendering
  and building that the screenshot is installed, the icons and desktop file
  are installed once, and no `debian/screenshot.png` exists in the template
- [x] 1.2 Add `dev/strip_remote_images.py` and
  `src/scantpaper/tests/test_strip_remote_images.py` covering a remote
  `https` image, a protocol-relative image and a local image, and verify
  with `pytest src/scantpaper/tests/test_strip_remote_images.py`
- [x] 1.3 Call the helper from `debian/rules` after the pandoc step, keep
  the rules file native and executable, and verify on a built tree that the
  installed `documentation.html` has no remote `<img>` source

## 2. Workflow

- [x] 2.1 In `.github/workflows/deb.yml`, upload
  `REPO/build/deb/scantpaper_${VERSION}_*` instead of only the `.deb` and
  pass `--no-lintian` to `debuild`; verify the artifact list contains the
  `.deb`, `.changes` and `.buildinfo`
- [x] 2.2 Add the `debian-checks` job on `debian:sid-slim` that installs
  `git`, `ca-certificates`, `python3`, `lintian` and `autopkgtest`, renders
  the tree from the same `SOURCE_REF`, downloads the artifact, runs
  `lintian --fail-on warning` on the `.changes` and then `autopkgtest -B`
  on the `.deb` with `-- null` and `--user`; verify the YAML parses and the
  step order puts lintian before autopkgtest
- [x] 2.3 Document the checks job, the sid testbed and the no-duplication
  rule in `packaging/debian/README.md`, note the checks in
  `release_procedure.md`, and add a `changelog.md` entry; verify the
  documented commands match the workflow

- [x] 2.4 Move the build job into a `debian:sid-slim` container, install
  git, ca-certificates, python3, debhelper, devscripts, fakeroot and equivs
  before checkout, drop `sudo` and the PPA, delete the `check-launchpad`
  job, and verify the YAML parses and the workflow contains no PPA,
  launchpad or `sudo` reference

- [x] 2.5 Declare the optional tools the suite exercises in
  `packaging/debian/tests/control`: `jbig2` for the four JBIG2 save tests and
  `tesseract-ocr-deu` for the multi-language OCR test; verify in a sid
  container that only the OpenSpec CLI test is skipped

## 3. Integration checks

- [x] 3.1 Run `pytest`, `ruff format --check`, `ruff check` and
  `ty check .`; verify all pass and coverage stays at or above the gate
- [x] 3.2 Render, build and lint locally; verify lintian exits 0 with
  `--fail-on warning`, reports no `privacy-breach-*` tag, and that the
  repository root still has no `debian/` directory
- [x] 3.3 Push the branch and verify the `debian-checks` job lints and runs
  autopkgtest successfully on the pull request

## Workflow follow-up

- Verify the next tagged release publishes the `.deb` only after the checks
  job passes.
- Archive the change after the project's review requirements are satisfied.
