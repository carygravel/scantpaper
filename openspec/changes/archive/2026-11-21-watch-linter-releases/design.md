# Design

## Context

See `proposal.md` - Why. Current state that shapes the approach:

- `test.yml` pins ruff and ty as literals: `ruff==0.16.7 ty==0.0.85` in the
  `latest`, `stonking`, `resolute` and `noble` jobs, but `ruff==0.16.5` in
  `jammy` — the drift this change removes. `.pre-commit-config.yaml` pins
  `v0.16.6`, a third version that cannot share a pin file (pre-commit needs a
  literal `rev`), and is being dropped by decision.
- `watch-openspec-releases` built the template this change reuses:
  `dev/openspec-version` (one-line pin) + stdlib-only `dev/check_openspec.py`
  + `.github/workflows/openspec-check.yml` (daily cron, one living issue),
  which in turn followed `check_launchpad.py` / `translations-check.yml`.
- The three validation commands CI runs are `ruff check .`,
  `ruff format --check .` and `ty check .` (the latter sometimes with
  `--extra-search-path` because ty needs site-packages stubs, e.g. Pillow, to
  resolve).
- `dev/` is not a Python package; its scripts are imported around the package
  namespace in tests (`dev/tests/`), and the 99% coverage gate measures only
  `src/scantpaper`, so the checker's own coverage is not part of the gate.

## Goals / Non-Goals

**Goals:**

- One source of truth for both pins, read by CI and the checker, replacing
  every literal in `test.yml` and ending the jammy drift.
- A single command that answers "is a newer ruff/ty out, and does this repo
  still pass the lint and type gates with it?", per tool, locally and in the
  scheduled job.
- A report that says per tool either "safe to upgrade" or "blocked by
  <command>", with the failing output inline, and that surfaces
  config-migration warnings (obsolete settings or rule names) so a pin bump
  that also needs a `pyproject.toml` edit is not mistaken for a pure bump.
- One issue that closes itself once both pins catch up.

**Non-Goals:**

- Automatically bumping the pins or opening a PR. Renovate/Dependabot were
  considered and rejected as disproportionate for two pinned dev tools; the
  bump stays a reviewed commit.
- Validating the *pinned* releases on a schedule. `test.yml` already does
  that on every push, so the scheduled job validates only the candidates.
- Deciding whether a newly-surfaced lint rule belongs in the `ignore`
  blacklist. That stays a maintainer decision per `AGENTS.md`; the check
  only reports the violation.

## Decisions

### One pin file for both tools: `dev/lint-versions`

Two lines in the form `ruff=0.16.7` and `ty=0.0.85`. `test.yml` reads it with
`$(grep '^ruff=' dev/lint-versions | cut -d= -f2)` (and likewise for `ty`),
and the checker reads the same file. Alternatives: two one-line files (more
files, and the two tools are always updated together) or a `requirements.txt`
(fragment adds a packaging file to a project where these tools are not
packaging dependencies). The single file is the smallest thing both
consumers can read unambiguously.

### The checker is a script, not inline workflow YAML

`dev/check_linters.py` does the reading, per-tool comparison and
classification; the workflow only installs candidates and files an issue.
This mirrors `check_openspec.py`, keeps the logic testable with a `file://`
registry fixture and stub validation commands, and lets a maintainer run the
same check locally without GitHub. The checker never installs anything; the
workflow provides the candidate binaries on `PATH`.

### One invocation reports every pinned tool

The checker reads the pin file and loops over every tool it names, fetching
`https://pypi.org/pypi/<tool>/json` for the `latest` version. The `--json`
and `--markdown` reports are a single document covering all tools, satisfying
the spec's machine-readable single-report requirement. `--tool` filters to
one tool for local debugging.

### Per-tool validation through a configurable command list

Defaults, matching CI: ruff runs `ruff check .` then `ruff format --check .`;
ty runs `ty check .`. `--validate-cmd` is repeatable and overrides the
default list for the selected tool (or all tools when `--tool` is omitted),
so a new gate is added in one place and tests can stub commands. Each
command runs with `subprocess.run` in the repository root, capturing stdout
and stderr; the first failure per tool is recorded with its output and that
tool is classified `update-blocked`. Alternatives: hard-coding the commands
(duplicates the CI definition) or letting the workflow run validation and
pass output back (splits classification across YAML and Python).

### `select = ["ALL"]` means a new release can fail in two distinct ways

Because the project enables every ruff rule and suppresses noise in a
blacklist, a candidate fails either because **code now violates a rule** or
because **the config itself is obsolete** (a removed setting, a renamed or
removed rule name in `ignore`). The checker therefore captures stderr as
well as the exit code: exit 0 with `warning:` output is still `safe`, but
the warnings are reported inline so the bump is known to carry a
`pyproject.toml` change; exit non-zero records the failing command's output.
This keeps the human decision (fix code vs. extend the blacklist) in view
without guessing.

### Candidate installation is the workflow's job, in an isolated venv

The scheduled job creates a throwaway virtual environment, installs
`.[test]` plus `ruff==<latest>` and `ty==<latest>` into it, and runs the
checker with that venv's `bin` first on `PATH`. Installing `.[test]` makes
ty's type-check reproducible (the same packages CI's `latest` job resolves,
so `--extra-search-path` is unnecessary) and mirrors the CI validation
environment. Nothing from the pinned install is reused. Like
`check_openspec.py`, validation is read-only with respect to the repository.

### Three states per tool, and only one issue

Per tool: `current`, `update-safe`, `update-blocked`. The workflow upserts
one issue labelled `lint-update`, with a title that names each tool's state
(for example "ruff 0.17.0 safe to upgrade; ty 0.0.90 blocked"), updates it
in place, and closes it only when every tool is `current`. One issue is
enough because the tools' states are reported together and an edited issue
cannot leave a stale recommendation behind.

### Silence is not evidence: every run leaves a summary

A run that finds nothing files no issue, which is otherwise
indistinguishable from a run that never happened. The checker's human
summary (per-tool versions and state) is included in the JSON report, and
the workflow appends it to `$GITHUB_STEP_SUMMARY`, so a run page always
states the conclusion. Alternatives: commenting on a tracking issue every
run (noise on a daily cron) or filing an issue when current (defeats the
self-closing rule).

### Exit codes follow the OpenSpec check

`0` whenever the state was determined, including when an update was found,
safe or blocked; `2` when the pin file, a registry, or a candidate version
cannot be read. Filing an issue is the workflow's job, so "found something"
must not fail the job, while "could not tell" must not read like "current".

### Daily cron, matching the existing checks

`0 7 * * *` plus `workflow_dispatch`, copied from `openspec-check.yml`. ty
releases often; the living-issue pattern absorbs the churn (one issue,
updated in place), and moving to weekly is a one-line cron edit if the
nudges ever feel noisy.

## Risks / Trade-offs

- **A passing candidate can still change behaviour the three commands do not
  cover** (formatting nuance, config semantics) → the issue recommends a
  reviewed commit with the normal suite, never an auto-merge; the green
  scheduled result is not treated as proof.
- **ty is fast-moving (0.0.x), so daily runs often report "safe to
  upgrade"** → the single living issue keeps this to one item; weekly cron
  is a one-line change if it becomes noise.
- **PyPI rate limits or outages make the job red** → exit `2` without filing
  an issue, so a flaky registry cannot masquerade as "update available";
  `workflow_dispatch` allows a manual re-run.
- **A new ruff release that adds many `select = ["ALL"]` rules inflates the
  ignore blacklist work** → the check reports each violation with its rule;
  adopting then falls under the existing AGENTS.md ratchet discipline, so
  the blast radius is visible before the bump.
- **ty candidate resolution differs from CI** (stub availability) → the
  scratch venv installs `.[test]` exactly like the `latest` job, so a
  blocked candidate reflects a real resolution failure, and a false
  "blocked" is preferable to a false "safe".
- **A third scheduled check now exists alongside openspec and translations**
  → all three are stdlib-only, advisory, read-only, and follow the same
  contract, so the maintenance cost is one more YAML file.

## Migration Plan

1. Add `dev/lint-versions` with the current versions (`ruff=0.16.7`,
   `ty=0.0.85`); switch every `test.yml` install step to read it, which
   also fixes the jammy `0.16.5` drift.
2. Land the checker, its tests, and `lint-check.yml` in the same commit, so
   the pins have a single source of truth and a reporter the moment they
   exist.
3. Delete `.pre-commit-config.yaml` and reconcile the docs (the
   `pyproject.toml` comments that call ruff/ty editor-only, `AGENTS.md`,
   `CONTRIBUTING.md`).
4. Rollback: restore the literal pins in `test.yml`. The scheduled workflow
   is independently disable-able and files no issue while the pins match the
   registry; the pre-commit file is recoverable from git.

## Open Questions

- Whether to also surface ruff's `preview`-gated rule set in the report,
  since adopting `preview = true` would change the lint surface. Deferrable:
  the check currently validates the config as written (preview off), which
  is the correct baseline.
