## Why

The PTH (`flake8-use-pathlib`) rule family is disabled in `pyproject.toml` because the config comment claims "60k lines still use os.path everywhere." That premise is wrong — the actual codebase has only 193 PTH violations across 31 files. Long term the codebase should use pathlib for all filesystem paths; the first step is to stop ignoring PTH, fix the existing violations, and enforce the convention going forward.

## What Changes

- Remove `"PTH"` from the `ignore` list in `[tool.ruff.lint]` in `pyproject.toml`.
- **BREAKING (internal only):** Migrate ~193 call sites of `os.path.*`, builtin `open()`, and `glob.glob()` to pathlib equivalents (`Path` methods). No public API or user-facing behavior changes — this is an internal refactor.
- Update the now-stale config comment that misrepresents the scale of the migration.
- Ensure the test suite still passes and the 99% coverage gate holds.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None.

This is a pure internal refactor to pathlib: no spec-level behavior changes (no public API, config format, or user-facing behavior is altered). Marked `skip_specs: true` in `.openspec.yaml`.

## Impact

- **Code:** All modules touching filesystem paths — principal sites in `scantpaper/` (`app.py`, `config.py`, `helpers.py`, `page.py`, `savethread.py`, `session_mixins.py`, `importthread.py`, `docthread.py`, `file_menu_mixins.py`, `app_window.py`, `i18n.py`, `config.py`) plus `dev/generate_pot.py`.
- **Tests:** ~95 of the 193 violations are in `scantpaper/tests/` (~31 files total affected) — mechanical but the bulk of the file count.
- **Tooling:** Ruff config in `pyproject.toml` (remove `PTH` from ignore); ruff is an editor-time linter only, not a CI gate.
- **Risky surface:** the 15 `glob` sites (PTH207) — `Path.glob`/`Path.rglob` return `Path` objects, not `str`, so downstream string consumers must be checked. `open()` fixtures raise no 3.10/exception-type complications (no `"x"` mode in use).
