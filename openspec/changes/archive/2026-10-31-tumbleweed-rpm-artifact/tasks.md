# Tasks

## 1. Spec template target conditional

- [x] 1.1 Add the `%if 0%{?suse_version} >= 1699` dependency blocks to
  `packaging/opensuse/scantpaper.spec`: the Tumbleweed branch uses the
  unversioned `python3-*` names and the Leap branch keeps `python313-*`.
  Verify with `rpmspec -P` that each branch expands on its matching
  container and the Leap branch is unchanged.
- [x] 1.2 Rewrite the spec comments that assert a Leap-only fact (pandoc,
  the pythondist generator) so they are target-neutral. Verify the detailed
  rationale remains in `packaging/opensuse/README.md` and no stale claim is
  left in the spec.
- [x] 1.3 Extend `src/scantpaper/tests/test_packaging_versions.py` to
  assert both dependency branches, the Tumbleweed `python3-*` names and the
  unchanged Leap `python313-*` names. Verify
  `pytest src/scantpaper/tests/test_packaging_versions.py` passes.

## 2. Build driver target selection

- [x] 2.1 Add `TARGET=leap16` (default) and `TARGET=tumbleweed` to
  `packaging/opensuse/build.sh`, with target-specific `ORDER`, `RUNTIME`,
  `%dist`, non-oss handling and the Tumbleweed runtime build dependencies.
  Verify `TARGET=bogus bash packaging/opensuse/build.sh build sane` exits
  non-zero before calling zypper and `bash -n packaging/opensuse/build.sh`
  passes.
- [x] 2.2 Make `rpmname_for sane` derive the package name from the
  target's Python flavor, and pass `--define 'pyflavor ...'` to both
  `rpmspec -P` and `rpmbuild`. Verify the expanded spec and the install
  glob name the same package for a simulated 314 flavor.
- [x] 2.3 Create `src/scantpaper/tests/test_packaging_opensuse.py` with
  tests for the invalid-target exit, the two target arrays and the `%dist`
  mapping. Verify `pytest src/scantpaper/tests/test_packaging_opensuse.py`
  passes.

## 3. Patched sane flavor and provides

- [x] 3.1 Parameterize `packaging/opensuse/python313-sane.spec` with a
  `pyflavor` macro (default `313`) in `Name`, `BuildRequires` and
  `Requires`, and add the Tumbleweed `Provides: python3-sane` and
  `python3dist(python-sane)`. Verify `rpmspec -P --define 'pyflavor 314'`
  expands the name and dependencies to 314 while the default expands to
  313.
- [x] 3.2 Add tests to `test_packaging_opensuse.py` for the default flavor,
  the two `Provides` lines and the `.0` version suffix. Verify
  `pytest src/scantpaper/tests/test_packaging_opensuse.py` passes.
- [x] 3.3 Document the flavor macro and the replacement/provides rule in
  `packaging/opensuse/README.md`. Verify the documented `--define` command
  matches the one `build.sh` passes.

## 4. Tumbleweed CI workflow

- [x] 4.1 Create `.github/workflows/opensuse-tumbleweed.yml` with the same
  `push`, `pull_request` and `workflow_dispatch` triggers as the other
  package builds, and a build job on `opensuse/tumbleweed:latest` that runs
  `TARGET=tumbleweed build.sh setup`, builds and installs sane and
  scantpaper, and collects the runtime set. Verify the YAML parses and the
  trigger block matches the other package workflows.
- [x] 4.2 Add the clean-room install job with stock and seeded
  `python-sane` scenarios. Verify a dispatched run installs the published
  set, checks `scantpaper --version` and the runtime imports, and does not
  assert that the patched sane survives a later update.
- [x] 4.3 Add the release step that uploads the set as
  `scantpaper-opensuse-tumbleweed`. Verify a tag run attaches the
  Tumbleweed asset and its file names do not collide with the Leap asset.
- [x] 4.4 Add tests to `test_packaging_opensuse.py` asserting the `push`,
  `pull_request` and `workflow_dispatch` triggers, the container image, the
  artifact name, the seeded scenario and the absence of the Leap update
  assertion. Verify `pytest src/scantpaper/tests/test_packaging_opensuse.py`
  passes.
- [x] 4.5 Add the Tumbleweed workflow to the rebuild dispatch list in
  `release_procedure.md`. Verify the documented command matches the
  workflow's `source_ref` input.

## 5. User documentation

- [x] 5.1 Add the Tumbleweed install section to `README.md` with the
  artifact name, the patched-sane caveat and the `tiff2ps` limitation.
  Verify the documented `zypper install` command names the Tumbleweed RPMs
  and does not reuse the Leap package list.
- [x] 5.2 Add the target-selection, dependency-strategy, trigger and release
  asset notes to `packaging/opensuse/README.md`. Verify every documented
  target and command matches `build.sh` and the workflow.
- [x] 5.3 Add a test to `test_packaging_opensuse.py` that the README names
  Tumbleweed, the patched sane and `tiff2ps`. Verify
  `pytest src/scantpaper/tests/test_packaging_opensuse.py` passes.

## 6. Integration verification

- [x] 6.1 Build the Tumbleweed set in `opensuse/tumbleweed:latest` with
  `TARGET=tumbleweed build.sh all`, then install the collected runtime set
  in a fresh container. Verify `scantpaper --version`, `python3 -c 'import
  sane, tesserocr, iso639, img2pdf, ocrmypdf'` and `rpm -q` for the
  patched sane package.
- [x] 6.2 Build the Leap set with `TARGET=leap16 build.sh all` and verify
  the package set is unchanged from the current artifact.
- [x] 6.3 Run `pytest` and `openspec validate --strict`; verify both pass
  and coverage does not regress.
- [x] 6.4 Run `ruff format --check` and `ruff check`; verify no new
  findings.

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Track upstream PR 109. When it is merged and released, remove the local
  `python-sane` patch and shadow package in a separate change.
