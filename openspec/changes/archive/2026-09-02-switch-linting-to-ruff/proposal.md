## Why

Pylint is no longer a real quality gate: it is installed in only one of the
three CI jobs via the Debian `python3-pytest-pylint` package, has no pytest
configuration to enforce it, and CI on `main` stays green regardless of the
`pylint.txt` warning counts. Ruff already lints the whole codebase every day
via zed, is dramatically faster, and its config is already maintained in
`pyproject.toml`. This change makes ruff the single linting gate and removes
pylint entirely, so the "pylint-clean / score" bookkeeping in docs and
`MEMORY.md` matches reality.

## What Changes

- Add a `ruff check` step to all three CI jobs in `.github/workflows/test.yml`
  (the two pip-based jobs and the PPA job). Ruff is installed via `pip` in CI.
- **Replace black with `ruff format`** as the formatter: drop black from the
  pre-commit hook (delete `.pre-commit-config.yaml`), replace `black --check`
  steps in CI with `ruff format --check`, and run a one-time `ruff format` over
  the tree (46 files differ from black output — mostly cosmetic
  parenthesization, all mechanical). **BREAKING** for formatter: ruff format
  output differs slightly from black's on this codebase.
- Drop `python3-pytest-pylint` from CI build dependencies in
  `.github/workflows/test.yml` and `.github/workflows/deb.yml`, and drop `black`
  from the `test` extras in `pyproject.toml` (now replaced by `ruff format`).
- Delete `.pylintrc` and the `pylint.txt` / `pylint.txt.new` report files.
- Remove the `# pylint: disable=wrong-import-position,import-error` clause from
  `dev/generate_pot.py:18`, keeping the `# noqa: E402` comment for ruff.
- Replace pylint-referencing quality-gate language in `AGENTS.md`,
  `CONTRIBUTING.md`, and `openspec/config.yaml` with ruff references.
- Reconcile the ruff rule set: decide, per currently-ignored rule category,
  whether it stays in the `ignore` list or becomes a required fix. Remove rules
  from `ignore` only where the codebase is already clean.
- **ruff is NOT added to `pyproject.toml`** — it is not packaged in Debian (only
  pulled in by zed), so it must not become a build dependency. It is installed
  via `pip` in the CI jobs that already use pip. This applies to both `ruff
  check` and `ruff format`; `black` (and `python3-pytest-pylint`) are removed
  from the pyproject/Deploy dependencies for the same reason ruff stays out.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is a pure tooling / CI / documentation change with no change to
user-visible behavior, so it opts out of specs (`skip_specs: true`).

## Impact

- **CI/CD**: `.github/workflows/test.yml` (add `ruff check` + `ruff format
  --check`, drop pytest-pylint and black), `.github/workflows/deb.yml` (drop
  `python3-pytest-pylint` build-dep).
- **Tooling**: `.pylintrc` deleted and `.pre-commit-config.yaml` deleted (its
  black hook is superseded by `ruff format`); ruff config already in
  `pyproject.toml` becomes the authoritative gate for both lint and format.
- **Source**: `dev/generate_pot.py` (remove one pylint-disable clause); a
  one-time `ruff format` pass over `scantpaper/` and `scantpaper/tests/`.
- **Docs**: `AGENTS.md`, `CONTRIBUTING.md`, `openspec/config.yaml`, `MEMORY.md`
  (pylint→ruff language; black→ruff-format references).
- **Deleted files**: `.pylintrc`, `.pre-commit-config.yaml`, `pylint.txt`,
  `pylint.txt.new`.
- **Dependencies**: removes `python3-pytest-pylint` from Debian/CI deps and
  `black` from the `test` extras; does not add ruff to `pyproject.toml` (Debian
  packaging constraint).