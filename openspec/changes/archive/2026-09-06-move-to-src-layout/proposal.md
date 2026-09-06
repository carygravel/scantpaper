## Why

`scantpaper/` is not a real Python package today. It is an implicit namespace
package whose own directory is pushed onto `sys.path` at runtime (`app.py`
does `sys.path.insert(0, BASE_DIR)`, `dev/generate_pot.py` does the same), so
every module imports its siblings flat (`from const import ...`,
`from frontend import enums`). This works for the app, but it means:

- ruff `INP001` (implicit namespace package) fires on 35+ files and stays on
  the global ignore list — one more category we cannot ratchet down.
- Tests resolve the flat namespace through pytest's import-mode "basedir"
  insertion, an implicit side-effect of missing `__init__.py` files rather
  than an explicit configuration.
- The outstanding `# This could be removed if we moved to a src-based layout`
  comment in `pyproject.toml` remains unresolved.

Now is the right time: the ruff import convention question (relative vs
package-absolute) has a clear answer given `select = ["ALL"]` already vetoes
parent-relative imports via `TID252`, and the pytest `pythonpath` ini option
(available since pytest 7) gives us an explicit, maintained way to keep tests
running against the source tree.

## What Changes

- Move the source package from `scantpaper/` to `src/scantpaper/` **BREAKING**
  (paths in tooling/docs; not user-facing behaviour).
- Add `scantpaper/__init__.py` and `scantpaper/frontend/__init__.py`, turning
  the implicit namespace package into a regular package.
- Rewrite every first-party import (production and tests) from the flat style
  (`from const import ...`, `from dialog.sane import ...`) to package-absolute
  (`from scantpaper.const import ...`, `from scantpaper.dialog.sane import ...`).
- Rewrite the ~680 string mock targets in tests
  (`patch("savethread.foo")` → `patch("scantpaper.savethread.foo")`).
- Remove the `sys.path.insert()` hacks in `app.py` and `dev/generate_pot.py`.
- Update `pyproject.toml`:
  - `[tool.setuptools.packages.find]` to `where = ["src"]` (removing the
    `# This could be removed if we moved to a src-based layout` comment).
  - Add `[tool.pytest.ini_options] pythonpath = ["src"]` so `pytest` keeps
    running against the source tree with no install step.
- Update `const.get_version()` and `i18n.LOCALEDIR_PKG` so their `__file__`-
  relative path resolution still works under `src/`.
- Update the run workflow: document `python3 -m scantpaper.app` (+
  `PYTHONPATH=src` or an editable install) instead of
  `python3 scantpaper/app.py` **BREAKING** (developer workflow; console
  script `scantpaper` and DEB/CI flows unchanged in effect).
- Update `README.md`, `CONTRIBUTING.md`, `AGENTS.md`, and the `deb.yml`
  help2man invocation that hard-codes `'python3 scantpaper/app.py'`.
- Remove `INP001` from the ruff `ignore` list.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is a pure structural refactor with no user-visible behaviour
change; `skip_specs: true` is set in `.openspec.yaml`, matching the archived
`stop-ignoring-pth` change.

## Impact

- **Source layout**: `scantpaper/` → `src/scantpaper/`; `dev/` scripts are
  updated but stay at repo root.
- **Imports**: every first-party `import`/`from` statement in `scantpaper/`,
  about 300 lines across production and tests, gained the `scantpaper.` prefix.
- **Test mocks**: roughly 682 string `patch(...)` targets updated.
- **Packaging**: setuptools `packages.find` gains `where = ["src"]`;
  `app.ui`/`icons` package-data unaffected.
- **CI/CD**: `.github/workflows/test.yml` unchanged in effect (both `pytest`
  and `pytest-3` jobs resolve the package via `pythonpath`); `deb.yml`
  help2man command updated.
- **Linting**: `INP001` removed from ruff `ignore`; no new ignores added.
- **Docs**: `README.md`, `CONTRIBUTING.md`, `AGENTS.md` import/run-workflow
  wording updated.