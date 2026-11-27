# Tasks

## 1. Clear the backlog

- [x] 1.1 Split `restore-bilevel-g4-after-pdfa`:
      `specs/pdf-image-compression/spec.md` keeps the lossless-in/lossless-out
      guarantee and its explicit request, and a new requirement carries the
      Group 4 restoration for page XObjects and inlined images. Verify
      `openspec validate restore-bilevel-g4-after-pdfa --strict` passes and
      that the scenario set is unchanged.
- [x] 1.2 Split `honor-cancel-through-pdf-save`:
      `specs/background-job-cancellation/spec.md` keeps queued/running work
      and progress teardown, and a new requirement carries stopping a PDF save
      in any phase including after page assembly. Verify strict validation
      passes and the scenario set is unchanged.
- [x] 1.3 Split `fix-manual-word-inside-ocr-para-lost-on-save`:
      `specs/save-searchable-text-layer/spec.md` keeps the structural
      guarantee and container levels, and a new requirement carries a word
      added inside a paragraph's box but outside its lines. Verify strict
      validation passes and the scenario set is unchanged.
- [x] 1.4 Archive the five changes in the design's order
      (`watch-openspec-releases`, `preserve-ligature-text-mapping`,
      `fix-manual-word-inside-ocr-para-lost-on-save`,
      `restore-bilevel-g4-after-pdfa`, `honor-cancel-through-pdf-save`).
      Verify `openspec validate --specs --strict --no-interactive`,
      `openspec validate --archived --no-interactive` and
      `openspec validate --changes --strict --no-interactive` all pass, and
      that `openspec/specs/openspec-cli-version/spec.md` now exists.

## 2. Validate every active change

- [x] 2.1 Add `openspec validate --changes --strict --no-interactive` to
      `dev/check_openspec.py`'s `DEFAULT_VALIDATE_COMMANDS` and add the
      matching step to each `.github/workflows/test.yml` job that installs
      OpenSpec, immediately after the `--archived` step. Verify
      `dev/tests/test_openspec.py` passes: its workflow-drift test asserts
      every recorded command appears in the workflow.
- [x] 2.2 Confirm the new step fails on a malformed active change and passes
      on the cleaned-up tree. Verify by temporarily introducing a
      requirement over the length limit in a scratch change under
      `openspec/changes/`, running the step, and deleting the scratch
      change afterwards.

## 3. Gate on unarchived completed changes

- [x] 3.1 Write `dev/check_change_archive.py`: run `openspec list --json`,
      select changes whose `status` is `complete`, exit non-zero naming every
      one of them, and support a machine-readable mode for CI logs. Take the
      CLI command as an option so tests can substitute a stub. Verify with
      `dev/tests/test_change_archive.py` covering a completed change, several
      completed changes, an in-progress change, and a change with no tasks.
- [x] 3.2 Add the gate as a step in each `.github/workflows/test.yml` job that
      installs OpenSpec, after gate A, and record the command alongside
      `DEFAULT_VALIDATE_COMMANDS` so the scheduled CLI-version check replays
      it. Verify by extending `dev/tests/test_openspec.py` to assert the step
      appears in the workflow, and by running it against the cleaned-up tree.
- [x] 3.3 Update `AGENTS.md`: describe both gates, state that a change is
      archived in the commit that ticks its last task, and record the
      permitted alternative of leaving the last task unticked while a change
      is held for review. Verify every command quoted in the new text runs as
      written.

## 4. Integration

- [x] 4.1 Run `pytest` from the repository root and confirm all tests pass
      with the coverage gate. Run `ruff check .`, `ruff format --check .`,
      `ty check .` and `python3 dev/check_test_coverage.py`; confirm no
      diagnostics and no new unexecuted statements in the new developer
      script's tests.
- [x] 4.2 Run the three OpenSpec commands exactly as CI invokes them and
      confirm no active change is left complete.

## Workflow follow-up

- Archive this change after review, in the commit that ticks task 4.2.
- Verify the archived result with `openspec validate --archived
  --no-interactive`.
