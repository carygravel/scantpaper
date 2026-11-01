# Proposal

## Why

Debian's autopkgtest fails the coverage gate at 98.39% while every
application test passes. The 37 skipped tests are all for developer
tooling: 36 need `git`, which the autopkgtest environment does not
install, and one needs the npm-based `openspec` CLI. Because those test
modules live under `src/scantpaper/tests/`, `--cov=scantpaper` measures
their bodies, so skipping them lowers the gate. The same mechanism
previously dropped coverage from 99.29% to 98.64% when a missing
`de_DE.utf8` locale skipped 24 tests. The gate therefore reports which
optional tools happen to be installed, not whether the shipped code is
covered, and it is not reproducible across local, GitHub and Debian
runs.

Excluding test code from the reported total is the obvious fix, but done
naively it also discards the useful signal that test code is actually
executed. This change keeps that signal without letting it set the gate.

## What Changes

- **Report application coverage only, but keep recording test
  execution.** Move the exclusion from run-level to report-level
  (`[tool.coverage.report] omit`), so the 99% gate and HTML report cover
  the shipped package while test modules remain traced and stored. The
  application baseline is unchanged at 99.07% with zero missing lines.
- **Audit test code where the environment is complete.** Add
  `dev/check_test_coverage.py`, run after the full suite locally and in
  GitHub's `latest` job. It fails when a test module was not collected or
  contains an unexecuted statement, and ratchets the partial-branch count
  at the current baseline of 85. The current test baseline is 27,502
  statements with zero missing. Debian does not run the audit: its skips
  are environment-driven, not dead code.
- **Colocate developer-tooling tests.** Move the seven test modules that
  exist solely to test a `dev/` script from `src/scantpaper/tests/` to
  `dev/tests/`, and update their repository-root calculations. They
  remain collected by the default `pytest` run. This is organisational:
  the audit covers both test roots, and the application gate never
  measured `dev/` in the first place. `test_po_files.py` stays because it
  also validates the shipped catalogs; `test_openspec_specs.py` stays
  because it validates repository specs, not a `dev/` script.
- **Run the git-dependent tests in Debian.** Add `git` to the autopkgtest
  `Depends` in `packaging/debian/tests/control`, so 36 tests Debian can
  run are no longer skipped. The single `test_openspec_specs.py` skip
  remains: the `openspec` CLI is an npm package Debian does not ship.
- **Record the one-time baseline shift.** With test code outside the
  gate, measured statements fall from about 41.8k to 14.4k and partial
  branches from 260 to 175. The 27.4k test statements move to the audit,
  whose baseline is zero missing and 85 partial branches. Debian's 98.39%
  becomes the same 99.07% seen locally and on GitHub.

## Capabilities

### New Capabilities

- `test-coverage`: what the coverage gate measures, the
  environment-independent threshold, the canonical test-code audit, and
  where developer-tooling tests live.

### Modified Capabilities

- `debian-packaging`: the autopkgtest dependency set must declare the
  system tools the suite probes for, so tests Debian can run are not
  silently skipped.

## Impact

- `pyproject.toml`: coverage `omit` moves to the report section; a
  configuration guard asserts it; ruff per-file ignores extend to
  `dev/tests/**`.
- New `dev/check_test_coverage.py` with tests under `dev/tests/`.
- `.github/workflows/test.yml`: the audit runs in the `latest` job only,
  after `pytest`.
- Seven modules moved (`test_build_ppa.py`, `test_prepare_deb.py`,
  `test_prepare_rpm.py`, `test_sync_salsa.py`, `test_release.py`,
  `test_launchpad.py`, `test_strip_remote_images.py`), with their
  `REPO_ROOT` calculations adjusted.
- `packaging/debian/tests/control`: add `git` to the test dependencies.
- No runtime code, API or user-visible behaviour changes. `git` is a
  test-only dependency and is not added to the package's own `Depends`.
