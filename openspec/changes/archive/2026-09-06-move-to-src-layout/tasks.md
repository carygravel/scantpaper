## 1. Layout Move

- [x] 1.1 `git mv scantpaper src/scantpaper` (moving app.py, app.ui, dialog/,
      frontend/, scanner/, tests/, icons/, modules)
- [x] 1.2 Add `src/scantpaper/__init__.py` and
      `src/scantpaper/frontend/__init__.py`
- [x] 1.3 Update `[tool.setuptools.packages.find]` to
      `{ where = ["src"], include = ["scantpaper*"], exclude = ["scantpaper.tests"] }`
      and remove the `# This could be removed if we moved to a src-based
      layout` comment
- [x] 1.4 Add `pythonpath = ["src"]` to `[tool.pytest.ini_options]` in
      `pyproject.toml`
- [x] 1.5 Confirm `pytest` still collects and runs against the source tree
      with the move alone (tests are expected to fail on imports until step
      2; verify the failure mode is only `ModuleNotFoundError` for
      first-party modules, not collection errors)

## 2. Import Rewrite

- [x] 2.1 Rewrite imports in leaf modules first: `const`, `i18n`, `helpers`,
      `pagerange`, `loop_helpers` to `scantpaper.` prefix
- [x] 2.2 Rewrite imports in aggregator modules (`config`, `basethread`,
      `page`, `savethread`, `docthread`, `importthread`, `comboboxtext`,
      `simplelist`, `canvas`, `imageview`, `bboxtree`, `unpaper`,
      `tesseract`, `text_layer_control`, `progress`, `print_operation`,
      `postprocess_controls`, `entry_completion`)
- [x] 2.3 Rewrite imports in mixins and windows (`app`, `app_window`,
      `basedocument`, `document`, `session_mixins`, `file_menu_mixins`,
      `edit_menu_mixins`, `tools_menu_mixins`, `scan_menu_item_mixins`,
      `scanner/*`, `frontend/*`, `dialog/*`)
- [x] 2.4 Rewrite first-party imports in all test files under
      `src/scantpaper/tests/` to the `scantpaper.` prefix
- [x] 2.5 Rewrite the string mock targets in tests
      (`patch("dialog.sane.X")` → `patch("scantpaper.dialog.sane.X")`,
      etc.) across test files
- [x] 2.6 Verify no non-`scantpaper.` first-party import remains:
      `grep -rE "^\s*(from|import) (const|i18n|helpers|app|canvas|frontend|scanner|dialog|tests)\b"` returns nothing

## 3. Path Computations and sys.path Hacks

- [x] 3.1 Fix `const.get_version()` to resolve the repo-root `pyproject.toml`
      from `src/scantpaper/` under source, keeping the
      `importlib.metadata` fallback when packaged
- [x] 3.2 Fix `i18n.LOCALEDIR_PKG` so it resolves the package locale dir
      correctly under `src/scantpaper/`
- [x] 3.3 Remove the `sys.path.insert(0, BASE_DIR)` from `app.py`, keeping the
      pyinstaller `sys.frozen`/`_MEIPASS` icon-path branch
- [x] 3.4 Remove the `sys.path.insert` from `dev/generate_pot.py`; switch it
      to `from scantpaper.const import ...`; update `dev/compile_mo.py` for
      the new layout
- [x] 3.5 Audit and fix filesystem-path assertions in tests
      (e.g. `test_app.py:258` pyinstaller `sys.path[0]` assertions)

## 4. Tooling and Documentation

- [x] 4.1 Update the `deb.yml` help2man command from
      `'python3 scantpaper/app.py'` to the new module invocation
- [x] 4.2 Update `README.md` run instructions (all `python3 scantpaper/app.py`
      references) to `python3 -m scantpaper.app` / editable install
- [x] 4.3 Update `CONTRIBUTING.md` and `AGENTS.md` import and run-workflow
      wording (`scantpaper.` absolute imports; module invocation)
- [x] 4.4 Remove `INP001` from the ruff `ignore` list; add `dev/*` to
      `[tool.ruff.lint.per-file-ignores]` for `dev/` scripts, documented as
      "scripts folder, not a package"

## 5. Verification

- [x] 5.1 `ruff check .` passes with no new ignore entries and `INP001`
      removed from the list
- [x] 5.2 `ruff format --check .` passes
- [x] 5.3 Full `pytest` passes from the repo root against the source tree
      (no install), meeting the `--cov-fail-under=99` gate
- [x] 5.4 Confirm `coverage.json`/htmlcov measures `src/scantpaper/` (not a
      site-packages copy)
- [x] 5.5 `python3 -m build` (wheel/sdist) succeeds; `pip install dist/*.whl`
      into a fresh venv and smoke-run the console script `scantpaper`
- [x] 5.6 Confirm `python3 -m scantpaper.app` runs against the source tree
      with `PYTHONPATH=src`, and the `latest_w_ppa`-style uninstalled
      `pytest` path (no `pip install .`) still works