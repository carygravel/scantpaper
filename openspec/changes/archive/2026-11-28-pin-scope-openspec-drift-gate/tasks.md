# Tasks

## 1. Fix the home-relative path (lands first)

- [x] 1.1 Install the pinned CLI (`npm install -g
      "@fission-ai/openspec@$(cat dev/openspec-version)"`) and run `openspec
      update`; verify `git status` reports no change to tracked files and that
      `openspec update --dry-run --json` no longer plans the untracked
      `.opencode` deletions.
- [x] 1.2 In `dev/check_generated_instructions.py`, expand `~` with
      `Path.expanduser()` before the absolute/relative branch in
      `in_repository`, and update its docstring to name the three path forms.
      Verify `pytest dev/tests/test_generated_instructions.py` passes.
- [x] 1.3 Add a test whose stub plans `~/.config/openspec/config.json` and
      whose `HOME` is a temporary directory, asserting exit 0 and a `current`
      report; verify it fails against the unfixed filter and passes after 1.2.
- [x] 1.4 Add a test whose `HOME` is a directory inside the root, asserting a
      `~` path under it is reported as stale; this proves the filter expands
      the path rather than skipping every `~`. Verify it passes with 1.2.

## 2. Pin-scope the gate

- [x] 2.1 Add `--pin-file` (default `dev/openspec-version` under `--root`),
      read the pin, run `<cli> --version`, and compare the stripped strings.
      Verify a unit test covers a matching version and a mismatch.
- [x] 2.2 On a mismatch, report an `unchecked` state, exit 2, and name the
      installed version, the pin and the install command, without claiming
      `current` or `stale`; verify the test asserts the exit code and both
      versions in the human and JSON output.
- [x] 2.3 Treat a missing or empty pin file, and an unreadable `--version`
      output, as `unchecked` with exit 2. Verify each case has a test and that
      a missing CLI still exits 2.
- [x] 2.4 Make the test stubs answer `--version` as well as `update`, so no
      test depends on the real CLI; verify the whole
      `dev/tests/test_generated_instructions.py` suite passes with a
      different CLI on `PATH`.
- [x] 2.5 Update the module docstring, the `_summary` wording and the exit-code
      table so "behind the pinned CLI" is only claimed when the installed CLI
      is the pin. Verify `ruff check .` and `ty check .` report nothing.

## 3. Move the gate out of candidate validation

- [x] 3.1 Remove `python3 dev/check_generated_instructions.py` from
      `DEFAULT_VALIDATE_COMMANDS` and append it to `ADOPT_COMMANDS` after
      `openspec update`. Verify `dev/tests/test_openspec.py` asserts the new
      placement and the issue body order: pin, install, refresh, drift check,
      validation commands.
- [x] 3.2 Keep the gate in every `test.yml` job that installs OpenSpec; verify
      the workflow-drift test in `dev/tests/test_openspec.py` still passes and
      that the workflow step is unchanged.
- [x] 3.3 Add a `dev/tests/test_openspec.py` case where the candidate changes
      the generated files and assert the state is not `update-blocked` for
      that reason. Verify the test fails while the gate is still in the
      candidate list and passes after 3.1.

## 4. Spec and contributor documentation

- [x] 4.1 Verify the delta against the main spec: run `openspec validate
      --changes --strict --no-interactive` and confirm it passes, with no
      warning about a MODIFIED block losing an existing scenario.
- [x] 4.2 Update `AGENTS.md`: the bump procedure installs the pin before
      running the gate, and the gate is verified after `openspec update`
      rather than replayed against a candidate. Verify every command quoted in
      the new text runs as written.
- [x] 4.3 Confirm no user-visible behaviour changed, so `README.md` needs no
      entry; record that in the change's review notes.

## 5. Integration

- [x] 5.1 Run `pytest` with the coverage gate, then `ruff check .`, `ruff
      format --check .`, `ty check .` and `python3 dev/check_test_coverage.py`;
      confirm no diagnostics and no newly uncovered or partially covered
      lines.
- [x] 5.2 Run the five CI commands with the pinned CLI installed and `HOME`
      set to an empty temporary directory; confirm the drift gate is green on
      a clean home.
- [x] 5.3 Run the gate with a different CLI on `PATH`; confirm exit 2, a
      message naming both versions, and no `current` or `stale` claim.

## Workflow follow-up

- Push the commits and confirm `test.yml` is green on `latest`, `resolute` and
  `stonking`.
- After the next OpenSpec release ships, confirm the scheduled check files an
  `openspec-update` issue whose adoption block lists the refresh and the drift
  check in that order.
