# Design

## Context

See `proposal.md` for motivation and `specs/mutation-testing/spec.md` for the
contract. The constraints that shape this design are:

- The suite is green and fast enough for a weekly run: 2,745 tests in about
  168 s locally. It needs GTK4 under Xvfb, and it starts and stops GLib
  threads.
- `pyproject.toml` puts the 99% coverage gate, pytest-cov and pytest-timeout
  in `addopts`, and `src/scantpaper/conftest.py` sets a 10,000 s per-test
  timeout. A mutation run must not inherit either behaviour unchanged.
- The application supports Python 3.10, but the mutation tool is a developer
  tool. It may require 3.11+, so it cannot be added unconditionally to the
  `[test]` extra used by the jammy job.
- The project already pins developer tools in one file (`dev/lint-versions`,
  `dev/openspec-version`) and runs scheduled advisory checks that keep one
  issue each.

## Goals / Non-Goals

**Goals:**

- Make assertion gaps in shipped `scantpaper` code visible with a repeatable
  local and scheduled check.
- Keep the mutation tool out of runtime and package dependencies.
- Make every mutant's outcome explicit so a tool or selection failure cannot
  masquerade as a high score.
- Fit the existing advisory-check culture: one scheduled report, no pull
  request gate.

**Non-Goals:**

- Mutating `dev/` scripts, test modules, generated files, or dependencies.
- A pass/fail mutation-score ratchet. The first version reports; a baseline
  can be added after the score is shown to be stable.
- Changing application behaviour, packaging, or the normal test matrix.
- Replacing coverage, linting, or the test-code audit.

## Decisions

### Tool: pytest-gremlins, pinned

Use `pytest-gremlins` as the mutation engine. The pilot on
`src/scantpaper/savethread.py` generated 216 mutants and finished in 169 s
with four workers and no timeouts; mutmut 3.8.1 generated 2,365 mutants on
the same target, hit 154 timeouts, and was still running at a 600 s cutoff.
Gremlins also runs each mutant in a fresh subprocess, which is safer for a
GTK/GLib suite than mutmut's fork-after-suite model.

Cosmic-ray was rejected: its only advantage was mutating path-loaded
`dev/` modules, which are now out of scope, and it has no coverage-guided
test selection. It would require a hand-maintained module-to-test map and
would risk false survivors.

Gremlins is young, so the runner keeps the tool behind one small module and
records its exact version. Mutmut remains a fallback if gremlins becomes
unmaintained, but the two tools generate different mutants, so their scores
are not comparable.

### Scope: `src/scantpaper` only

The manifest names modules under `src/scantpaper`. The runner rejects any
target outside that tree, including `dev/`, `build/` and `src/scantpaper/
tests/`. Test code is never a mutation target.

### Pin: a new `dev/mutation-version` file

Record `pytest-gremlins=<version>` in `dev/mutation-version`, following the
existing pin-file convention. The runner installs or verifies exactly that
version. Do not add the tool to `pyproject.toml`: the `[test]` extra is
installed on Python 3.10 in the jammy job, where gremlins cannot be
installed. The dedicated mutation environment also needs `pytest>=8.4.2`
and `coverage>=7.12`; install `.[test]` first, then the pinned plugin, and
let pip resolve the newer pytest and coverage in that environment only.

### Runner: `dev/run_mutations.py`

A thin wrapper rather than a hand-written mutation engine. It:

1. Reads `dev/mutation-targets.toml` and validates every target is under
   `src/scantpaper` and exists. An optional repeatable `--target` overrides
   the manifest list for local iteration; CI always uses the manifest.
2. Builds one pytest invocation for all targets, with the full
   `src/scantpaper/tests` tree as the test selection so coverage-guided
   selection sees cross-cutting tests.
3. Clears the normal `addopts` with `-o addopts=` so the coverage gate,
   pytest-cov and pytest-timeout do not interfere, sets `PYTHONPATH=src`,
   and points `COVERAGE_FILE` at a temporary file so the gate's `.coverage`
   is untouched.
4. Runs under `xvfb-run -a` when `DISPLAY` is unset; uses the existing
   display otherwise.
5. Passes `--gremlins`, the target list, `--gremlin-report=json` and
   `--gremlin-report=html`, `--gremlin-workers`, `--gremlin-cache` (local
   only), `--gremlin-coverage-timeout=600` and
   `--gremlin-mutant-timeout=120`.
6. Fails if the output reports that coverage-guided selection was disabled.
   Gremlins then falls back to running every test per mutant, which would
   turn a weekly job into a multi-day one.
7. Copies the JSON report into `mutation-report/`, adds the environment
   versions, and writes `summary.json` and `summary.md`.
8. Exits 0 when the run completed with findings, and non-zero when the
   manifest, tool version, baseline suite, coverage selection, or report is
   unusable.

The tool's JSON separates `zapped`, `survived`, `timeout`, `error` and
`pardoned`; a per-result record with an empty `selected_tests` list is
classified as no-test. The summary keeps those categories distinct and
never folds no-test into killed.

### Manifest: `dev/mutation-targets.toml`

One file lists the source modules, worker count, and timeouts. Adding a
target is a manifest-only change. The initial set is deliberately
localized:

- `savethread.py` — PDF save, codec decisions and fallback paths.
- `bboxtree.py` — bounding-box geometry.
- `unpaper.py` — image-cleanup parameters.
- `tesseract.py` — OCR parameter parsing.
- `config.py` — user defaults.

`canvas.py`, `imageview.py`, `layer.py` and `docthread.py` are the next
tier. `page.py`, `document.py` and `helpers.py` are avoided initially
because they are reached by dozens of test files and survivors become
expensive to evaluate.

### Triage: inline pardons with a reason

Survivors are left visible unless they are genuinely equivalent or
untestable. Suppression uses the tool's inline
`# gremlin: pardon[reason] justification` form, and the summary reports the
pardon count. Do not use `--gremlin-exclude` to hide a file or package.
This keeps every exclusion reviewable in the source diff.

### CI: one scheduled advisory workflow

Add `.github/workflows/mutation-check.yml` with a weekly schedule and
`workflow_dispatch`. Pin the runner image to `ubuntu-24.04` and Python 3.12
for the first version to match the noble developer machine and avoid the
fork behaviour of newer CPython until it is verified. Install the same
system packages as the `latest` test job (GTK, SANE, Tesseract, OCRmyPDF,
Ghostscript, ImageMagick, unpaper, jbig2), install the mutation environment,
run the wrapper, upload `mutation-report/`, and write the summary to the
job page.

The workflow keeps at most one open issue labelled `mutation-testing`. The
issue body carries the score, the per-target table, no-test/error/timeout
counts, the pardon count, the top survivors, the artifact link, and the
recorded environment. It is updated in place and closed when a run has no
unpardoned findings. A run that cannot complete fails the job and does not
update the issue with a clean-looking result.

## Risks / Trade-offs

- **A permanent dashboard issue becomes noise** → update one issue in
  place, summarise only the top survivors, and close it when a run is
  clean. A per-target ratchet can replace it later.
- **Equivalent mutants inflate the survivor count** → require an inline
  pardon with a reason and justification; report the pardon count; review
  pardons in the source diff.
- **Parallel GTK tests share one X display** → start with four workers and
  the existing `xvfb-run`; if tests interfere, switch to per-worker
  displays or reduce the worker count.
- **Flaky tests produce false kills** → the baseline must be green before
  mutation starts; if flakiness appears under load, add
  `pytest-rerunfailures` to the mutation environment and record reruns.
- **Gremlins is pre-2.0** → pin the exact version, keep the wrapper thin,
  and record the version in every report. Do not compare scores across
  tool versions.
- **Gremlins does not mutate string literals or module-level constants** →
  accept the blind spot for the first version. The project's codec and
  message strings are usually asserted directly; a later change can add a
  targeted constant sweep if needed.
- **Environment drift changes the score** → record Python, tool,
  OCRmyPDF and Ghostscript versions and compare only within one recorded
  environment. Run one canonical CI environment for now.
- **The coverage pre-scan is disabled after 600 s** → fail the run rather
  than fall back to full-suite-per-mutant execution.
- **The fork warning under multi-threaded GTK becomes an error** → verify
  on the Debian testing Python; if needed, pin Python 3.12 for the runner
  or reduce the worker pool.

## Migration Plan

1. Land the pin, manifest, runner, tests and documentation without a CI
   job; run it locally on the initial target set.
2. Add the scheduled workflow and let it report for a few runs.
3. If the score is stable, add a per-target baseline as a separate change.
4. Rollback is removing the workflow and the `dev/` files; no runtime or
   package behaviour depends on them.

## Open Questions

- Should the follow-up ratchet compare only targets whose source and test
  hashes are unchanged, or compare the whole target set after each run?
- Should CI add a second environment (Debian testing) once the first one is
  stable, or keep one canonical environment indefinitely?
- Is a targeted string/constant mutation sweep worth adding for
  `savethread.py` and `config.py`, given gremlins' operator blind spot?
