# Proposal

## Why

A packager that runs the test suite can silently skip tests when an
optional tool or locale is missing, so the build passes while the
coverage of that run is quietly reduced. nixpkgs hit this with the
`de_DE.utf8` locale (issue #107). The suite already skips
environment-dependent tests for developer convenience, but it offers no
way to opt into a run where a skip is a failure.

## What Changes

- Add an opt-in strict test-run mode, selectable by `--fail-on-skip` or
  `SCANTPAPER_FAIL_ON_SKIP=1`.
- In a strict run, every skipped test is reported with its node id and
  reason, and the pytest session exits non-zero.
- Leave the default run unchanged: without a switch, skips remain skips.
- Do not add an allowlist. A packager that deliberately omits a test
  disables it explicitly (for example with `pytest --ignore`, or
  `pytestCheckHook`'s `disabledTestPaths`), so the omission stays
  visible.
- Document both switches and the dependencies of the canonical test
  environment (the `de_DE.utf8` locale, the external OCR, DjVu, PDF and
  packaging tools, a display, and the `openspec` CLI) in README.md.
- Enable the mode in the canonical GitHub jobs whose declared test
  dependencies are complete, after confirming they have no skips.
- Enable the mode in the Debian autopkgtest after declaring
  `desktop-file-utils`, the missing declaration behind the one observed
  skip, and explicitly ignoring the third-party `openspec` module.

## Capabilities

### New Capabilities

- `test-environment`: owns the opt-in strict test-run contract, the
  reporting of skipped tests and the session failure they cause, and the
  documented set of dependencies that a canonical test environment
  provides.

### Modified Capabilities

<!-- None: the coverage gate, the test-code audit and the Debian
packaging policy keep their current requirements. The autopkgtest change
is a fix for an undeclared Debian-packaged tool, not a new policy. -->

## Impact

- `conftest.py` (new, at the repository root): registers the flag and
  implements the session-level skip collection and exit behavior for
  both the `src/scantpaper/tests` and `dev/tests` roots.
- `src/scantpaper/tests/test_fail_on_skip.py`: covers the new
  behavior by loading the root conftest directly.
- `README.md` (Testing) and `AGENTS.md` (testing workflow): document
  both switches and the canonical environment.
- `.github/workflows/test.yml`: enables the switch in the complete jobs.
- `packaging/debian/tests/control` and `packaging/debian/tests/test-suite`:
  declare `desktop-file-utils`, ignore the third-party `openspec` module,
  and run the suite with the switch.
- No application code, runtime dependencies, or end-user workflow
  changes.
