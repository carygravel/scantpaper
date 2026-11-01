# Tasks

## 1. Pin as a single source of truth

- [x] 1.1 Add `dev/openspec-version` containing `1.16.0`, and verify that
  `cat dev/openspec-version` prints only the version with a trailing newline
- [x] 1.2 Make the `Install OpenSpec` step in `.github/workflows/test.yml`
  install `"@fission-ai/openspec@$(cat dev/openspec-version)"`, and verify the
  file reads as one argument (quoted) by running the same install command
  locally and checking `openspec --version` reports `1.16.0`

## 2. Version checker

- [x] 2.1 Add `dev/check_openspec.py` that reads the pin, reads the npm
  registry document for `@fission-ai/openspec`, and reports the pinned,
  installed and latest versions as human text, `--json` and `--markdown`, and
  verify with `dev/tests/test_openspec.py` fed a `file://` registry fixture
- [x] 2.2 Classify the state as `current`, `update-safe` or `update-blocked`
  by running each `--validate-cmd` (default: the two CI validation commands)
  and recording the first failure with its output, and verify with tests that
  cover a passing stub, a failing stub, and the default command list
- [x] 2.3 Exit `0` whenever the state was determined and `2` when the pin
  file, registry document, or candidate version cannot be read, and verify
  with tests for a missing pin file, an unreadable registry, and a
  detected-but-blocked update
- [x] 2.4 Verify the new tests pass with
  `python3 -m pytest dev/tests/test_openspec.py`, and that `ruff check`,
  `ruff format --check` and `ty check .` are clean for the new files

## 3. Scheduled workflow

- [x] 3.1 Add `.github/workflows/openspec-check.yml` with a daily cron and
  `workflow_dispatch`, `contents: read` and `issues: write`, installing the
  registry's `latest` before running the checker, and verify the file parses
  with `python3 -c 'import yaml; yaml.safe_load(open(".github/workflows/openspec-check.yml"))'`
- [x] 3.2 Upsert one issue labelled `openspec-update` whose title names the
  state, updating it in place when it already exists, and close it when the
  state is `current`; verify the shell branches with the `gh` commands run in
  a throwaway local repository stub, and confirm the `--json` report fields
  the branches read are the ones the checker emits
- [x] 3.3 Confirm a run files no issue and fails the job when the registry is
  unreachable, so an outage cannot be reported as an available update, by
  running the checker against an unreadable registry URL and checking the
  exit code is `2`

## 4. Documentation

- [x] 4.1 Update the OpenSpec bullet in `AGENTS.md` to describe the scheduled
  check and the one-line bump through `dev/openspec-version`, replacing the
  three manual npm commands, and verify the Markdown lines stay within 80
  characters and the referenced paths exist

## 5. Integration checks

- [x] 5.1 Run `python3 -m pytest`, `ruff check`, `ruff format --check`,
  `ty check .` and `python3 dev/check_test_coverage.py`, and verify all pass
  with coverage at or above the configured threshold and no new unexecuted
  statements
- [x] 5.2 Run `openspec validate watch-openspec-releases --type change`,
  `openspec validate --specs --strict --no-interactive` and
  `openspec validate --archived --no-interactive`, and verify each reports no
  failures

## Workflow follow-up

- After merge, dispatch the workflow manually and confirm it opens exactly one
  `openspec-update` issue that names the versions and the validation result.
- Bump `dev/openspec-version` to the reported release, land it, and confirm the
  next scheduled run closes the issue.
- Archive the change and verify `openspec validate --archived` still passes.
