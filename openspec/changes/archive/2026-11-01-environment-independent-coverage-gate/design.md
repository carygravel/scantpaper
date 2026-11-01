# Design

## Context

See `proposal.md` - Why.

`pyproject.toml` runs pytest with
`--cov=scantpaper --cov-report=html --cov-fail-under=99` and
`[tool.coverage.run] branch = true`. The measured source is the whole
`scantpaper` package, which includes `src/scantpaper/tests/`. The test
modules for `dev/` scripts live there too, although `dev/` itself is not
measured.

Measured on the 4.0.2 source tarball, which is what Debian's job ran:

```
  all tests run (local, GitHub)    40,397 stmts, 0 missing  -> 99.44%
  5 modules skipped (Debian)       40,397 stmts, 592 missing -> 98.39%
  application only                 14,064 stmts, 0 missing  -> 99.05%
  test tree (after this change)    27,502 stmts, 0 missing,
                                   736 branches, 85 partial -> 100% stmts
```

Coverage distinguishes `[run] omit`, which discards a file's data, from
`[report] omit`, which keeps the data and removes the file from the
reported total. Verified with the versions Debian ships
(coverage 7.16.1, pytest-cov 7.1.0): with report-level omit the gate total
was 14,412 application statements, while the same `.coverage` file still
held all 27,402 test statements for a second report. pytest-cov computes
`--cov-fail-under` from `cov.report()`, so it uses the filtered total.

pytest is invoked from the tree root with no `testpaths`, so a second test
root needs no configuration beyond keeping collection working.

## Goals / Non-Goals

**Goals:**

- The gate measures the application package only, and reports the same
  percentage in local, GitHub and Debian runs.
- Unexecuted test code remains visible, without letting a missing system
  tool fail the gate on an incomplete environment.
- Tests for `dev/` scripts live next to those scripts.
- Tests that Debian can run are not silently skipped there.

**Non-Goals:**

- Static analysis for unreachable code inside a test that still executes;
  the audit covers unexecuted statements, not logical dead branches.
- Making `test_openspec_specs.py` run in Debian: the CLI is not packaged.
- Moving tests that also validate shipped artifacts.
- Adding `git` to the package's runtime `Depends`.

## Decisions

### D1: Exclude test code at report level, not run level

Add `*/scantpaper/tests/*` and `*/dev/tests/*` to
`[tool.coverage.report] omit`, and measure both test roots with
`--cov=scantpaper --cov=dev/tests`, leaving `[tool.coverage.run]` without
an omit entry. The gate and HTML report show application modules; the
execution data for test modules is still collected.

Why not the alternatives:

- `[run] omit` discards the data, so no later audit can tell an unexecuted
  helper from an excluded file. It would fix the gate only by giving up the
  signal this change is meant to preserve.
- `--cov` on a hand-maintained module list drifts whenever a module is
  added.
- Lowering `--cov-fail-under` in Debian makes environments disagree and
  hides real application regressions.
- Moving only the skipped modules leaves the remaining test code measured,
  so a locale-style skip returns on the next dependency change.

The glob is matched against the path, not the working directory, so it also
covers an installed `scantpaper/tests` tree.

### D2: Audit test code only where the environment is complete

Add `dev/check_test_coverage.py`, run after a full suite with:

```
pytest && python3 dev/check_test_coverage.py
```

The script:

- reads data recorded for both test roots: pytest measures
  `--cov=scantpaper --cov=dev/tests`, while the report omits both, so the
  relocated modules are present in the data without entering the gate;
- enumerates every `.py` file under `src/scantpaper/tests/` and
  `dev/tests/`;
- opens the `.coverage` data with
  `Coverage(config_file=False, branch=True)`, whose default exclusions
  (pragma markers and `if TYPE_CHECKING:`) match the project's report
  configuration, so no file is silently exempted;
- fails with a clear message when the data file is missing, when a test
  module is absent from the measured set, or when any test module has a
  missing statement;
- reports partial branches and fails when the total exceeds the recorded
  baseline of 85.

Placement matters:

- It runs in GitHub's `latest` job, which installs every optional test
  tool, so all test modules execute and a skip is a real finding.
- It does not run in Debian, whose missing `git`/`openspec` skips are
  environment facts, not dead code.
- It is not in pytest `addopts`: a partial local run leaves most modules
  unmeasured and would fail the audit. It is a separate command after the
  full suite, as coverage is today.

Alternatives rejected: a second full pytest pass with the test tree as the
coverage source doubles CI time; vulture or an AST checker adds a
dependency and false positives; a strict-skip plugin catches skipped tests
but not dead helpers.

### D3: Move pure dev-tooling tests to `dev/tests/`

Move the seven modules whose docstring names a single `dev/` script:
`test_build_ppa.py`, `test_prepare_deb.py`, `test_prepare_rpm.py`,
`test_sync_salsa.py`, `test_release.py`, `test_launchpad.py` and
`test_strip_remote_images.py`.

`test_po_files.py` stays: it tests `dev/check_po.py` but also validates
the shipped catalogs, so it is mixed. `test_openspec_specs.py` stays too:
it validates repository specs, not a `dev/` script.

Mechanics:

- `REPO_ROOT` moves from `parents[3]` to `parents[2]` in each moved
  module. None of them import `scantpaper`, so `pythonpath = ["src"]` is
  unaffected.
- `pytest` has no `testpaths`, so both roots are discovered from the
  repository root. A `--collect-only` comparison guards the count.
- Ruff's existing test suppressions (`S101`, `SLF001`, `PLR2004`, ...)
  are extended to `dev/tests/**`. These are the same suppressions tests
  already rely on, not new ones.
- The audit's own tests live under `dev/tests/`, so the relocation lands
  before the audit work in the task order. The move has no effect on the
  gate once D1 lands and is reviewed as an organisational change.

### D4: Declare `git` in the autopkgtest dependencies

Add `git` to `Depends` in `packaging/debian/tests/control`. The tests
create their own temporary repositories, so they need the binary, not a
checkout or network access. `test_build_ppa.py` passes without
`git-buildpackage`: the missing-orig-tarball case asserts the graceful
"orig tarball" failure that `build_ppa.py` produces when `gbp` is absent.

Alternatives rejected: a `-k` filter in `debian/tests/test-suite` would
hide the tests; installing the `openspec` CLI would add an npm dependency
Debian does not carry.

The GitHub `debian-checks` job already installs `git`, so this brings the
real Debian run to the same behaviour.

### D5: Guard the configuration with tests

Add checks that fail if the measurement boundary, test layout or Debian
dependency regresses:

- `src/scantpaper/tests/test_coverage_config.py` asserts that
  `[tool.coverage.report] omit` matches a path under
  `src/scantpaper/tests/`, and that `[tool.coverage.run]` has no omit
  entry, so the audit can still read the data;
- the same file asserts the seven moved modules exist under `dev/tests/`
  and not under `src/scantpaper/tests/`;
- `src/scantpaper/tests/test_packaging_versions.py` asserts that the
  autopkgtest control declares `git` and the runtime control does not;
- `dev/tests/test_check_test_coverage.py` covers the audit's pass case,
  an unmeasured module, a missing statement, and a partial-branch
  overrun.

## Risks / Trade-offs

- **Thin application headroom**: 99.07% leaves about 0.05 points of slack.
  -> The change must not reduce application coverage; the full-suite run
  and term-missing report must show zero missing application lines, and the
  old inflated 99.44% must not be used as the comparison.
- **Audit run on partial data**: a local `pytest test_one.py` would fail
  the audit. -> It is a separate command after the full suite, never part
  of `addopts`, and the script refuses a missing data file and names
  unmeasured modules instead of failing silently.
- **Stale `.coverage`**: an old data file could hide a regression. -> CI
  runs the audit immediately after `pytest`; locally the documented
  command always runs the suite first.
- **Report omit on the wrong section**: an omit under `[run]` would look
  correct in the HTML report while destroying the audit's data. -> The D5
  guard asserts the section and the explicit absence of a run-level omit.
- **Partial-branch ratchet friction**: a legitimate defensive branch in a
  test helper raises the count. -> Update the recorded baseline in the same
  change, as with the project's other coverage baselines.
- **Debian is not audited**: dead test code is caught in the canonical
  environment, not in the distro run. -> Accepted; the Debian gate stays
  focused on application coverage.
- **The openspec test still skips in Debian**: accepted by the spec; it no
  longer affects coverage.

## Migration Plan

One commit series, no runtime migration:

1. Relocate the dev-tooling tests, which creates `dev/tests/` and its
   ruff excludes.
2. Add report-level omit, the audit script and the guard tests.
3. Add the Debian `Depends` entry and its guard.

Rollback is a revert of the series; nothing persists outside the
repository and no user data or package format changes.
