# Tasks

## 1. Migrate and track the generated instruction files

- [ ] 1.1 Run `openspec update` with the pinned CLI and confirm it reports the
      24 planned changes the dry run described: `.agents/skills/**` created,
      `.opencode/commands/**` and `.opencode/skills/**` removed. Verify
      `openspec update --dry-run --json` then reports no change to a path
      inside the repository.
- [ ] 1.2 Confirm the migrated workflows are still discoverable as skills and
      that the four CI commands (`validate --specs`, `validate --archived`,
      `validate --changes`, `check_change_archive.py`) pass. Verify by listing
      the available skills and running the four commands.
- [ ] 1.3 Bring `.agents/skills/**` under version control, leaving the
      dependency manifests that `.opencode/.gitignore` covers ignored. Verify
      `git status` shows the generated files as the only addition and that
      `openspec update --dry-run` still reports nothing inside the repository.

## 2. Gate the drift

- [ ] 2.1 Write `dev/check_generated_instructions.py`: run
      `openspec update --dry-run --json`, keep the planned changes whose path
      resolves inside the repository root, and exit non-zero naming each one.
      Filter by path containment only, never by `tool` or `action`, and take
      the CLI command and root as options. Verify with
      `dev/tests/test_generated_instructions.py` covering an in-repository
      change, an outside-repository path, several changes, clean output, and
      an unreadable CLI.
- [ ] 2.2 Add the gate to each `.github/workflows/test.yml` job that installs
      OpenSpec, after the archive gate, and record its command in
      `dev/check_openspec.py`'s `DEFAULT_VALIDATE_COMMANDS`. Verify
      `dev/tests/test_openspec.py` passes: its workflow-drift test asserts
      every recorded command appears in the workflow.
- [ ] 2.3 Prove the gate fires: change a line in one tracked skill file, run
      the gate, and confirm it exits non-zero naming that file; then restore
      the file and confirm the gate passes.

## 3. Adoption instructions

- [ ] 3.1 Add an `ADOPT_COMMANDS` constant to `dev/check_openspec.py` holding
      `openspec update`, and render it in the issue body between the install
      step and the validation commands, so the refresh is named without making
      the candidate validation modify the repository. Verify
      `dev/tests/test_openspec.py` asserts the issue body contains the refresh
      command and the validation commands in that order.
- [ ] 3.2 Update `AGENTS.md`: the bump procedure gains `openspec update`, and
      the OpenSpec section states that the generated instruction files are
      tracked and gated. Verify every command quoted in the new text runs as
      written.

## 4. Integration

- [ ] 4.1 Run `pytest` from the repository root and confirm all tests pass
      with the coverage gate. Run `ruff check .`, `ruff format --check .`,
      `ty check .` and `python3 dev/check_test_coverage.py`; confirm no
      diagnostics and no new unexecuted statements in the new developer
      script's tests.
- [ ] 4.2 Run the five commands exactly as CI invokes them and confirm the
      drift gate reports nothing inside the repository.

## Workflow follow-up

- Archive this change after review, in the commit that ticks task 4.2.
- Verify the archived result with `openspec validate --archived
  --no-interactive`.
