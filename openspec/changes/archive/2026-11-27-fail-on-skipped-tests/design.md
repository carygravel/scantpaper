# Design

## Context

See `proposal.md` - Why. The observable contract is in
`specs/test-environment/spec.md`; this document explains the mechanism.

The suite has two test roots, `src/scantpaper/tests` and `dev/tests`.
`src/scantpaper/conftest.py` is the only conftest today, and it is an
ancestor of the first root but not of the second, so its hooks do not
run for `dev/tests`. Every skip arrives through one of four routes:

- `pytest.mark.skipif` (marker, including module-level markers)
- `pytest.skip()` in a fixture or a test body
- `pytest.importorskip()` (an import guard)
- a module-level `pytest.skip(..., allow_module_level=True)`

There is no per-skip hook to intercept in one place, and pytest has no
built-in "a skip is a failure" option. The suite must stay green by
default on a machine that lacks `de_DE.utf8` or an optional tool; that is
why the skips exist. The coverage audit (`dev/check_test_coverage.py`)
already detects a skip in the canonical GitHub environment, but only as a
second command over `.coverage`, which a packager such as nixpkgs may not
run (it stubs coverage out). nixpkgs runs `pytest` through
`pytestCheckHook`, where an environment variable is the simplest switch.

The one skip observed in the Debian autopkgtest's `dev/tests` output is
`dev/tests/test_join_metadata.py::test_joined_desktop_validates`, because
`packaging/debian/tests/control` does not declare `desktop-file-utils`.
That is a Debian-packaged tool, so the existing `debian-packaging`
requirement says it should be declared rather than skipped.

## Goals / Non-Goals

**Goals:**

- An opt-in run, selectable by flag or environment variable, that fails
  the session when any test is skipped.
- The failure names every skipped test and its reason.
- New skip sites are covered automatically, with no per-test change.
- The default run keeps today's behaviour.
- Tests excluded by `-m`, `-k`, `--deselect` or `--ignore` are not
  failures.
- The switches and the canonical environment's dependencies are
  documented.
- The complete GitHub jobs and the Debian autopkgtest dogfood the mode.

**Non-Goals:**

- Forcing a skipped test body to execute.
- Removing or reclassifying the existing skip sites.
- An allowlist of permitted skips.
- Making the mode the default.
- Consolidating the three locale probes in `conftest.py`,
  `test_helpers.py` and `test_1111_save_pdf.py`.
- Changing the coverage gate or the test-code audit.
- Enabling the mode in jobs that intentionally skip for a supported
  floor (jammy's toolkit and Python).

## Decisions

### D1: Collect skips at session level, not at each skip site

`pytest_runtest_makereport` records skipped reports on `item.config`, and
`pytest_sessionfinish` sets the exit status. This catches all four skip
routes, including `importorskip`, and it automatically covers a skip
added by a future test.

Alternatives rejected:

- Rewriting a skipped report to failed in `pytest_runtest_makereport`.
  A skip's `longrepr` is a `(path, line, reason)` tuple, not a failure
  representation; changing `outcome` makes the terminal output lie and
  risks a reporter error.
- Raising a failure in `_require_de_locale` or each skip site. That
  covers only the locale, misses the two duplicated `skipif` sites, and
  needs maintenance for every new skip.

### D2: The strict hooks live in a new root `conftest.py`

Pytest calls `pytest_addoption` only for an initial conftest, so an
option defined in the nested `src/scantpaper/conftest.py` is rejected as
an unrecognized argument (verified empirically). The hooks must also see
both test roots, and the nested conftest is not an ancestor of
`dev/tests`.

A new root `conftest.py` therefore owns the option, the session state and
the hooks. It imports only `os`, `sys` and `pytest`, so it is cheap to
load. `src/scantpaper/conftest.py` keeps its fixtures and helpers and is
unchanged.

Alternative rejected: loading a plugin with `-p` from `addopts`. It
changes every invocation, needs a plugin module, and is less obvious than
the conventional root conftest.

### D3: The switches are `--fail-on-skip` and `SCANTPAPER_FAIL_ON_SKIP=1`

The root conftest registers `--fail-on-skip` with `pytest_addoption`.
`pytest_configure` stores the decision on `config`:

```text
config.getoption("fail_on_skip")
or os.environ.get("SCANTPAPER_FAIL_ON_SKIP") == "1"
```

Either switch selects the same behaviour. Match the variable exactly
`"1"`: `"0"` is truthy in Python and must not enable the mode. The flag
is discoverable in `pytest --help`; the variable is the packager's
switch, for example nixpkgs' `preCheck`.

Alternatives rejected:

- Only an environment variable. The flag is the conventional pytest
  interface and is easier to use in a local run.
- Only a flag. The requester's build harness sets environment variables
  more naturally than pytest flags.
- Adding an option to `addopts` in `pyproject.toml`. That would change
  the default for every developer and break runs on machines that
  legitimately lack a dependency.

### D4: State lives on `config`, keyed by node id

`pytest_configure` initialises a dict, for example
`config._fail_on_skip_skips`. `pytest_runtest_makereport` adds
`report.nodeid -> reason` when `report.skipped` and `report.when` is
`setup` or `call`. It excludes a report with `wasxfail` set: pytest
reports an expected failure with `skipped=True`, but it is not an
environment skip. Deduplicating by node id avoids counting the same
item twice and keeps state from leaking into a later in-process session.

`_skip_reason` handles both skip representations: the third element of a
`(path, line, reason)` tuple, and `longreprtext` for a plain string.

### D5: The exit-status rule preserves an existing failure

`pytest_sessionfinish(session, exitstatus)` acts only when the mode is
enabled, at least one skip was recorded, and the session is not an
`xdist` worker (`hasattr(config, "workerinput")` is false). If
`exitstatus` is `ExitCode.OK`, set `session.exitstatus` to
`ExitCode.TESTS_FAILED`; otherwise keep the existing non-zero status, so
a test or coverage failure is not masked.

### D6: The human report is printed by the terminal reporter

`pytest_terminal_summary` prints a separated block listing each node id
and its reason, for example:

```text
[FAIL] 2 test(s) skipped while fail-on-skip is enabled:
  src/.../test_openspec_specs.py::test_specs_validate_strictly
    requires an openspec source tree and the openspec CLI
```

`pytest_report_header` adds a `fail on skip: enabled` line, so a clean
log proves the switch was active. If the terminal reporter is absent
(`-p no:terminal`), `pytest_sessionfinish` writes the same block to
stderr, so the report is never lost.

### D7: Deselection and ignore need no special handling

`pytest_runtest_makereport` only fires for items the session executed or
skipped. `-m`, `-k`, `--deselect` and `--ignore` produce no report, so
they are not counted. Comparing collected and reported counts instead
would misfire under `--maxfail` or `-x`, where later tests are not
skipped but never reached.

### D8: No allowlist

A packager that deliberately omits a test disables it explicitly with
its own harness (`pytest --ignore=...`, or `pytestCheckHook`'s
`disabledTestPaths`). That keeps the omission reviewable. The failure
message names the test and reason, so the next action is obvious. An
allowlist can be added later if a recurring, legitimate need appears.

### D9: Documentation names both switches and the canonical environment

README's Testing section gains both switches and a short list of what the
suite probes for: `de_DE.utf8`, `tesseract` with the German data,
`unpaper`, `cjb2`, `qpdf`, `pdfunite`, `pdftoppm`, `jbig2`, a display,
`git`, `appstreamcli`, `desktop-file-validate`, `msgfmt`, ImageMagick's
`convert`, the DejaVu fonts, and the `openspec` CLI. AGENTS.md gains the
same rule in its testing workflow, including that the mode is
canonical-environment-only.

### D10: Enable the mode in the complete CI jobs and the autopkgtest

Enable it in `latest`, `stonking` and `resolute`: each installs the
locale, `openspec` and the toolchain (and `resolute` already passes the
coverage audit, which fails on unexecuted test code).

In the Debian autopkgtest, declare `desktop-file-utils` in
`packaging/debian/tests/control` so `test_joined_desktop_validates` runs,
then run:

```text
pytest --fail-on-skip \
  --ignore=src/scantpaper/tests/test_openspec_specs.py
```

The ignore is the explicit third-party omission the `debian-packaging`
spec allows for the `openspec` CLI. The path is relative to the rendered
tree's root; if the module moves, the autopkgtest fails loudly rather
than silently skipping.

Do not enable the mode in `noble` or `jammy`: neither installs
`openspec`, and jammy also lacks `jbig2` and runs the supported-floor
PyGObject and Python. Before enabling a job, confirm with a local
`pytest -rs` run or the job log that it has no skips.

### D11: Test the hooks directly, plus one subprocess run

Unit tests in `src/scantpaper/tests/test_fail_on_skip.py` load the
root conftest with `importlib.util.spec_from_file_location` and cover:

- the flag, the variable, both, neither, and `"0"` (must not enable)
- reason extraction for a tuple and a string
- recording setup and call skips, ignoring other phases, passes and
  xfail reports, and deduplicating a node id
- the terminal summary containing each node id and reason
- the exit status from `OK`, from an existing failure, when disabled,
  when no skip is recorded, and for an `xdist` worker
- the stderr fallback when no terminal reporter is present
- the header on and off

One integration test copies the root conftest into a temporary
directory with a small skip-only test file and runs `python -m pytest`
there, with `PYTHONPATH` pointing at `src`. It asserts exit code 1 with
`--fail-on-skip` and with `SCANTPAPER_FAIL_ON_SKIP=1`, and 0 with
neither. It also asserts that a test excluded with `-m` or `--ignore`,
and an xfailed test, does not trigger a failure.

The root conftest is test infrastructure outside the shipped package. It
is not counted by the 99% coverage gate or by
`dev/check_test_coverage.py`; the unit tests load it directly and the
integration test exercises the real hook wiring. Keep it small and its
helpers pure.

## Risks / Trade-offs

- The root conftest is outside the coverage gate and the test-code
  audit. -> The unit tests load it directly and the integration test
  exercises it end-to-end; keep the logic small.
- A supported-floor skip (PyGObject 3.42, Python 3.10) fails a strict
  run. -> The mode is opt-in and documented as canonical-only; the
  jammy job does not enable it.
- A new intentional skip breaks a packager's strict build. -> That is
  the requested behaviour; the message names the test and reason, and
  the packager adds an explicit `--ignore` or `disabledTestPaths` entry.
- The autopkgtest ignore path can drift if the module moves. -> The run
  then fails loudly instead of silently skipping; update the path.
- `pytest -m "not slow"` still omits the canary without failing. ->
  Deselection is an explicit act, unlike an environment skip; document
  that a canonical run does not deselect.
- `pytest-xdist` worker sessions could set the wrong exit status. -> The
  session-finish hook runs only on the controller. The project does not
  use `xdist` today.
- State could leak between in-process sessions. -> Keep it on `config`,
  initialised in `pytest_configure`.

## Migration Plan

No data or API migration. The mode is opt-in and stores nothing. Adopt it
with `--fail-on-skip` or `SCANTPAPER_FAIL_ON_SKIP=1`; roll back by
removing the switch (or the CI step's `env` entry).
