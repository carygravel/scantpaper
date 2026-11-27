# Tasks

## 1. Pin, target manifest and local workspace

- [ ] 1.1 Add `dev/mutation-version` containing
      `pytest-gremlins=1.15.0`; verify the file has one `tool=version`
      line and that `pytest-gremlins` does not appear in
      `pyproject.toml`.
- [ ] 1.2 Add `.gremlins_cache/` and `mutation-report/` to `.gitignore`;
      verify `git check-ignore -v` names both paths.
- [ ] 1.3 Add `dev/mutation-targets.toml` with the five initial targets
      (`savethread`, `bboxtree`, `unpaper`, `tesseract`, `config`) and
      the worker/timeout settings; verify it loads with `tomllib`, every
      `module` exists, and every path is under `src/scantpaper` with no
      `dev/` or test path.

## 2. Runner and its tests

- [ ] 2.1 Write `dev/tests/test_run_mutations.py` covering manifest
      parsing and rejection of out-of-scope or missing targets, command
      construction (`-o addopts=`, `PYTHONPATH=src`, temporary
      `COVERAGE_FILE`, the gremlin flags and timeouts), outcome
      classification (killed, survived, no-test, error, timeout,
      pardoned), environment recording, and exit codes (findings exit 0;
      invalid manifest, missing tool, failed baseline, unreadable report
      and disabled coverage selection exit non-zero); verify the new tests
      fail before the runner exists.
- [ ] 2.2 Implement `dev/run_mutations.py` to satisfy those tests,
      streaming the tool output while capturing it for report validation;
      verify `pytest dev/tests/test_run_mutations.py` passes.
- [ ] 2.3 Add the optional repeatable `--target` override, the
      `xvfb-run -a` selection when `DISPLAY` is unset, and the detection
      of the coverage-selection-disabled notice; verify the dedicated
      tests cover each path.
- [ ] 2.4 Run the runner from a dedicated mutation environment for
      `src/scantpaper/savethread.py` only; verify it exits 0 and
      `mutation-report/summary.json` reports at least 200 mutants with
      killed, survived, no-test, error and timeout counts.
- [ ] 2.5 Verify the local run is side-effect free: `sha256sum .coverage`
      is unchanged and `git status --short` shows no tracked
      modifications.

## 3. Local documentation

- [ ] 3.1 Update `CONTRIBUTING.md` with the dedicated Python 3.11+
      environment, the install command from `dev/mutation-version`, the
      local runner command, how to read the summary, the target tiers and
      the report-only policy; verify
      `pytest src/scantpaper/tests/test_markdown_line_length.py`.
- [ ] 3.2 Add a short note to `AGENTS.md` that mutation testing is a
      developer-only advisory check, not part of the required gate;
      verify the Markdown line-length test still passes.
- [ ] 3.3 Document pin bumps, the `# gremlin: pardon[...]` triage rule and
      how to add a target to the manifest; verify the documented path and
      syntax match the runner and the manifest.

## 4. Scheduled advisory workflow

- [ ] 4.1 Add `dev/tests/test_mutation_workflow.py` asserting the
      workflow has a weekly `schedule`, `workflow_dispatch`,
      `issues: write`, `actions/upload-artifact`, the runner path,
      `mutation-report`, and the pinned `ubuntu-24.04` / Python 3.12
      environment; verify it fails before the workflow exists.
- [ ] 4.2 Implement `.github/workflows/mutation-check.yml` with the
      pinned environment, the system packages the app tests need, the
      pinned mutation install, the runner invocation, the job summary and
      the artifact upload; verify the workflow test passes and the YAML
      parses with `python3 -c "import yaml; yaml.safe_load(...)"`.
- [ ] 4.3 Add the single-issue step: create the `mutation-testing` label,
      find the open issue, update it from `mutation-report/summary.md`,
      and close it when the run has no unpardoned findings; verify the
      workflow test asserts the `gh issue` create/edit/close flow.
- [ ] 4.4 Verify the artifact upload includes `summary.json`,
      `summary.md` and the HTML report, and that a failed run does not
      leave a clean-looking issue update; verify with the workflow test
      and a manual `workflow_dispatch` after the branch is pushed.

## 5. Integration checks

- [ ] 5.1 Run `pytest` and `python3 dev/check_test_coverage.py`; verify
      the 99% application coverage gate passes and the test-code audit
      does not raise the partial-branch baseline.
- [ ] 5.2 Run `ruff check .`, `ruff format --check .` and `ty check .`;
      verify all three are clean.
- [ ] 5.3 Run `openspec validate --specs --strict --no-interactive` and
      `openspec validate --archived --no-interactive`; verify both pass.
- [ ] 5.4 Verify a normal installation is unaffected: `pytest-gremlins`
      is absent from `pyproject.toml`, and a clean `pip install .[test]`
      environment does not provide the mutation tool.

## Workflow follow-up

- Push a branch, run the workflow with `workflow_dispatch`, and verify the
  artifact and the rolling issue on the first real run.
- Watch the first scheduled run and adjust the initial target set,
  worker count or timeouts if a target is dominated by fan-in or
  environment-specific survivors.
- Add a per-target baseline and ratchet as a separate change once the
  score is stable across runs.
- Consider a second recorded environment (Debian testing) and a targeted
  string/constant mutation sweep in later changes.
- Archive the change after the normal review requirements are satisfied.
