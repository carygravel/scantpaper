# Tasks

## 1. Pin as a single source of truth

- [x] 1.1 Add `dev/lint-versions` containing `ruff=0.16.7` and `ty=0.0.85`,
  and verify that `grep '^ruff=' dev/lint-versions | cut -d= -f2` and the
  ty equivalent print exactly those versions
- [x] 1.2 Change the five `test.yml` install steps (`latest`, `stonking`,
  `resolute`, `noble`, `jammy`) to install via
  `$(grep '^ruff=' dev/lint-versions | cut -d= -f2)` and the ty equivalent,
  and verify the jammy job no longer pins `0.16.5` and that no bare
  `ruff==` or `ty==` literal remains in the workflow after the change

## 2. Version checker

- [x] 2.1 Add `dev/check_linters.py` that reads `dev/lint-versions`, fetches
  the latest version for each pinned tool from PyPI
  (`https://pypi.org/pypi/<tool>/json`), and reports the pinned, installed
  and latest versions per tool as human text, `--json` (with a summary
  string) and `--markdown`; verify with `dev/tests/test_linters.py` fed a
  `file://` registry fixture
- [x] 2.2 Classify each tool as `current`, `update-safe` or `update-blocked`
  by running its `--validate-cmd` list (defaults: ruff runs `ruff check .`
  then `ruff format --check .`, ty runs `ty check .`), recording each tool's
  first failure with its output, with independent per-tool state; verify
  with tests covering a passing stub, a failing stub, and both default
  command lists
- [x] 2.3 Surface config-migration warnings: capture stderr per command, keep
  exit-code-zero-with-warnings as `safe`, and include the warning lines in
  the report; verify with a test whose validation stub exits 0 while
  printing a `warning:` line
- [x] 2.4 Exit `0` whenever a state was determined (including a
  detected-but-blocked update) and `2` when the pin file, a registry, or a
  candidate version cannot be read; verify with tests for a missing pin
  file, an unreadable registry, and a detected-but-blocked update
- [x] 2.5 Support `--tool` filtering and a `--registry-url` override, and
  verify these options select one tool and read a fixture document
- [x] 2.6 Verify the new tests pass with
  `python3 -m pytest dev/tests/test_linters.py`, and that `ruff check`,
  `ruff format --check` and `ty check .` are clean for the new files

## 3. Scheduled workflow

- [x] 3.1 Add `.github/workflows/lint-check.yml` with a daily cron and
  `workflow_dispatch`, `contents: read` and `issues: write`, and verify the
  file parses with
  `python3 -c 'import yaml; yaml.safe_load(open(".github/workflows/lint-check.yml"))'`
- [x] 3.2 In the workflow, create a throwaway venv, install `.[test]` plus
  the latest ruff and ty into it, run `dev/check_linters.py --json` with the
  venv's `bin` first on `PATH`, and verify locally that the same commands
  install the latest releases and produce a `report.json` with per-tool
  entries
- [x] 3.3 Append the checker's human summary to `$GITHUB_STEP_SUMMARY` every
  run, and verify the checker's tests assert the `summary` field names the
  state for a current pin and for a blocked candidate
- [x] 3.4 Upsert one issue labelled `lint-update` whose title names each
  tool's state, updating it in place when it already exists and closing it
  when every tool is `current`; verify the shell branches with the `gh`
  commands in a throwaway local repository stub, and confirm the `--json`
  report fields the branches read are the ones the checker emits
- [x] 3.5 Confirm a run files no issue and fails the job when a registry is
  unreachable, so an outage cannot be reported as an available update, by
  running the checker against an unreadable registry URL and checking the
  exit code is `2`

## 4. Remove pre-commit and reconcile docs

- [x] 4.1 Delete `.pre-commit-config.yaml` and verify no remaining file
  references pre-commit
- [x] 4.2 Update the `pyproject.toml` comments that describe ruff/ty as
  editor-time only, since CI now runs both in five jobs, and verify the
  surrounding text stays consistent with `[tool.ruff]` and `[tool.ty]`
- [x] 4.3 Update `AGENTS.md` to describe the pin in `dev/lint-versions` and
  the scheduled linter check, mirroring the OpenSpec bullet, and verify the
  Markdown lines stay within 80 characters and the referenced paths exist
- [x] 4.4 Update `CONTRIBUTING.md` to point contributors at the pin file and
  the checker for the ruff/ty version discipline, and verify the same
  line-length and path checks

## 5. Integration checks

- [x] 5.1 Run `python3 -m pytest`, `ruff check`, `ruff format --check`,
  `ty check .` and `python3 dev/check_test_coverage.py`, and verify all pass
  with coverage at or above the threshold and no new unexecuted statements
- [x] 5.2 Run `openspec validate watch-linter-releases --type change
  --strict --no-interactive`, `openspec validate --specs --strict
  --no-interactive` and `openspec validate --archived --no-interactive`,
  and verify each reports no failures

## Workflow follow-up

- After merge, dispatch `lint-check.yml` manually and confirm it opens
  exactly one `lint-update` issue naming the per-tool versions and states.
- Bump `dev/lint-versions` to the reported releases, land it, and confirm
  the next scheduled run closes the issue.
- Archive the change and verify `openspec validate --archived` still passes.
