## 1. CI gate: make ruff the enforced linter + formatter

- [x] 1.1 In `.github/workflows/test.yml`, in the `latest_w_ppa` job: add `pip install ruff==0.16.5`, add a `ruff check .` step, replace the `black --check .` step with `ruff format --check .`, and drop `python3-pytest-pylint` from the `apt-get install` list; verify by inspecting the edited workflow.
- [x] 1.2 In `.github/workflows/test.yml`, in the `latest` job: add `pip install ruff==0.16.5`, add a `ruff check .` step, and replace the `black --check .` step with `ruff format --check .`; verify by inspecting the edited workflow.
- [x] 1.3 In `.github/workflows/test.yml`, in the `oldest` job: add `pip install ruff==0.16.5`, add a `ruff check .` step, and replace the `black --check .` step with `ruff format --check .`; verify by inspecting the edited workflow.
- [x] 1.4 In `.github/workflows/deb.yml`, remove `python3-pytest-pylint` from the `Build-Depends-Indep` list; verify the line is gone.

## 2. Replace black with ruff format

- [x] 2.1 In `pyproject.toml`, add `[tool.ruff.format] exclude = ["openspec/**"]` and remove `black==26.3.1` from the `test` extras; verify both edits.
- [x] 2.2 Delete `.pre-commit-config.yaml` (its black hook is superseded by `ruff format`); verify the file no longer exists.
- [x] 2.3 Run `venv/bin/ruff format .` and confirm it reports no remaining reformats; this is the one-time migration pass over source + tests. (Note: the format exclude needed `openspec/**`, not `openspec`, to take effect.)

## 3. Remove pylint configuration and reports

- [x] 3.1 Delete `.pylintrc`; verify the file no longer exists.
- [x] 3.2 Delete `pylint.txt` and `pylint.txt.new`; verify both are gone.

## 4. Clean pylint directives from source

- [x] 4.1 In `dev/generate_pot.py`, change the `# pylint: disable=wrong-import-position,import-error  # noqa: E402` comment to keep only `# noqa: E402`; verify `venv/bin/ruff check dev/generate_pot.py` passes.
- [x] 4.2 Strip the ~74 inline `# pylint: disable=...` / `# pylint: enable=...` directives across `scantpaper/` (incl. `conftest.py`, `app.py`, `docthread.py`, `session_mixins.py`, `basedocument.py`, all `scantpaper/tests/`) and `dev/`, preserving each accompanying `# noqa` comment; verify `venv/bin/ruff check .` passes and `venv/bin/ruff format --check .` is clean.
- [x] 4.3 Remove `python3-pytest-pylint` from the Development list in `README.md`; verify the line is gone.

## 5. Update documentation and tooling to reference ruff

- [x] 5.1 In `AGENTS.md`, replace pylint-clean language (lint-suppression approval rule, quality gates) with ruff equivalents; verify no `pylint` reference remains.
- [x] 5.2 In `CONTRIBUTING.md`, replace the pylint linting section and the lint-suppression rule with ruff (and black references with `ruff format`); verify no `pylint` reference remains and the `noqa` approval rule is preserved (reworded for ruff).
- [x] 5.3 In `openspec/config.yaml`, update the quality-gates context line from "pylint-clean" to "ruff-clean"; verify the edit.
- [x] 5.4 In `MEMORY.md`, replace the pylint score line and note the ruff gate change; verify only if edited.
- [x] 5.5 In `GEMINI.md` (and its `CLAUDE.md` symlink), replace pylint/black references with ruff equivalents; verify no `pylint` reference remains.
- [x] 5.6 In `tox.ini`, replace the black-based `lint` env with `ruff check .` + `ruff format --check .` (deps `ruff==0.16.5`); verify the edited env.

## 6. Verification

- [x] 6.1 Run `venv/bin/ruff check .` and confirm it reports `All checks passed!` (ruff 0.16.5).
- [x] 6.2 Run `venv/bin/ruff format --check .` and confirm no files would be reformatted.
- [x] 6.3 Run `pytest` and confirm the pre-existing failure set is unchanged (no new failures, coverage gate met). (A new failure, `test_save_multipage_hocr`, was introduced by `ruff format` stripping a trailing space inside a byte-for-byte hOCR literal; fixed by guarding that literal with `# fmt: off`/`# fmt: on`.)
- [x] 6.4 Confirm no `pylint` references remain in live source/config/docs (excluding `.git`, `openspec/changes/archive/**`, `scantpaper.egg-info/`, `reorder.log`).