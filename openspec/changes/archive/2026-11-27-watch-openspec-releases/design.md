# Design

## Context

See `proposal.md` - Why. Current state that shapes the approach:

- `test.yml` installs `@fission-ai/openspec@1.14.3` and runs two separate
  validation commands, because `--archived` does not combine with `--specs`.
- `.github/workflows/translations-check.yml` already implements the pattern
  this change needs: a daily cron job with `issues: write` that keeps one
  living issue per condition, driven by a stdlib-only `dev/check_launchpad.py`
  with a JSON report and an advisory exit-code contract.
- `dev/` is not a Python package; its scripts are imported around the package
  namespace in tests (`dev/tests/test_launchpad.py` does the same), and the
  99% coverage gate covers only `src/scantpaper`.

## Goals / Non-Goals

**Goals:**

- One source of truth for the pin, read by both CI and the checker.
- A single command that answers "is a newer OpenSpec out, and does this repo
  pass it?" locally and in the scheduled job.
- A report that says either "safe to upgrade" or "blocked by <command>", with
  the failing output inline.
- An issue that closes itself once the pin catches up.

**Non-Goals:**

- Automatically bumping the pin or opening a PR. Renovate was considered and
  rejected as disproportionate for one pinned dev dependency; the bump stays
  a reviewed commit.
- Validating the *pinned* release on a schedule. `test.yml` already does that
  on every push, so the scheduled job validates only the candidate.
- Watching anything except `@fission-ai/openspec`.

## Decisions

### Pin lives in `dev/openspec-version`, not in `test.yml`

`test.yml` reads the one-line file with
`npm install -g "@fission-ai/openspec@$(cat dev/openspec-version)"`, and the
checker reads the same file. Alternatives: parsing the version out of the
workflow YAML (brittle, regex against a moving file) or a `package.json`
dependency (adds a Node manifest to a Python project). The file is the
smallest thing that both consumers can read unambiguously.

### The checker is a script, not inline workflow YAML

`dev/check_openspec.py` does the reading, comparison and classification;
the workflow only installs a CLI and files an issue. This follows
`check_launchpad.py`, keeps the logic testable with a `file://` registry
fixture and stub validation commands, and lets a maintainer run the same
check locally without GitHub.

### The checker runs validation through a configurable command list

`--validate-cmd` is repeatable, defaulting to the two CI commands
(`--specs --strict`, then `--archived`). The workflow does not re-encode
them, so a new gate is added in one place. Each command runs with
`subprocess.run` in the repository root, capturing stdout and stderr; the
first failure is recorded with its output and the run is classified
`update-blocked`.

Alternatives: hard-coding the two commands (duplicates the CI definition),
or letting the workflow run validation and pass output back (splits the
classification across YAML and Python, and makes it untestable).

### Three states, and only one issue

`current`, `update-safe`, `update-blocked`. The workflow upserts one issue
labelled `openspec-update`, with the title naming the state, and closes it
when the state returns to `current`. Alternatives: two labels (safe/blocked)
so each can be closed independently - rejected, because the states are
mutually exclusive and an edited single issue cannot leave a stale
recommendation behind.

### Silence is not evidence: every run leaves a summary

A run that finds nothing files no issue, which is indistinguishable from a run
that never happened; that ambiguity already produced one false alarm after the
first manual dispatch. The checker therefore includes its human summary in the
JSON report, and the workflow appends it to `$GITHUB_STEP_SUMMARY`, so the run
page always states the versions and the conclusion. Alternatives: commenting on
a tracking issue every run (noise on a daily cron), or filing an issue even
when current (defeats the self-closing rule).

### Exit codes follow the translations check

`0` whenever the state was determined, including when an update was found and
whether it is safe or blocked; `2` when the pin file, registry, or candidate
version could not be read. Filing an issue is the workflow's job, so "found
something" must not fail the job. This mirrors `check_launchpad.py`, keeping
the two scheduled checks consistent.

### Daily cron, matching the existing check

`0 7 * * *` plus `workflow_dispatch`, copied from `translations-check.yml`.
Upstream released twice in the two weeks before this change, so daily is not
excessive; moving to weekly is a one-line edit if the noise becomes a
problem. Scheduled workflows are best-effort on GitHub and are disabled after
long inactivity, so this is a reminder, not a guarantee.

### The candidate is installed only in the scheduled job

The job runs `npm install -g @fission-ai/openspec@<latest>` and then the
checker with the default validation commands. Nothing from the pin-derived
install is reused, so the candidate is what gets validated. The checker
itself never installs anything, which keeps it safe to run locally against an
already-installed CLI.

## Risks / Trade-offs

- **A passing candidate can still change behaviour that validation does not
  cover** (archiving, spec sync) → the issue recommends a reviewed commit
  with the normal test suite, never an auto-merge, and the workflow's own
  green result is not treated as proof.
- **npm registry outages or rate limits make the job red** → exit `2`
  without filing an issue, so a flaky registry cannot masquerade as "update
  available"; `workflow_dispatch` allows a manual re-run.
- **An issue left open after an unrelated manual bump** → the next run
  detects `current` and closes it, so the reminder is self-clearing.
- **Two scheduled checks now exist** → both are stdlib-only, advisory, and
  follow the same contract, so the maintenance cost is one more YAML file.

## Migration Plan

1. Add `dev/openspec-version` with `1.16.0`; change `test.yml` to read it.
2. Land the checker, its tests, and the workflow in the same commit, so the
   pin has a single source of truth the moment it changes.
3. Rollback: restore the previous version in `dev/openspec-version`. The
   workflow can be disabled independently and files no issue while the pin
   matches the registry.
