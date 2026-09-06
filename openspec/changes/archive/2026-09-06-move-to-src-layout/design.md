## Context

The app runs today because `scantpaper/` is an implicit namespace package
whose directory is injected onto `sys.path` at runtime (`app.py:28`,
`dev/generate_pot.py:10`), which makes the flat first-party imports
(`from const import ...`) resolve. Tests inherit the same flat namespace via
pytest's import-mode "basedir" insertion: with `scantpaper/tests/__init__.py`
present but `scantpaper/__init__.py` absent, pytest walks up to `scantpaper/`
as the first `__init__`-less ancestor and puts it on `sys.path`.

This was confirmed empirically: adding `__init__.py` to the package root alone
breaks `pytest` with `ModuleNotFoundError: No module named 'const'` for the
exact same invocation. Any redesign must therefore choose an explicit
mechanism to replace that implicit one (pytest `pythonpath` ini option) rather
than assume tests keep working.

Two facts constrain the import convention decision:

- ruff uses `select = ["ALL"]` and `TID252` (stable, from
  `flake8-tidy-imports`) is active with its default
  `ban-relative-imports = "parents"`. Parent-relative imports
  (`from ..helpers import ...`) are flagged; same-level (`from . import ...`)
  and package-absolute (`from scantpaper.const import ...`) are not.
- Every one of the ~682 string mock targets in tests
  (`mocker.patch("savethread.foo")`) is already a dotted absolute path and
  *cannot* be relative. Choosing package-absolute imports means imports and
  mock targets share one naming scheme.

## Goals / Non-Goals

**Goals:**

- Make `scantpaper` a real, regular package with an explicit `__init__.py`,
  living under `src/`, so `INP001` can be removed from the ruff ignore list
  without adding any new ignore entries.
- Keep `pytest` running against the working source tree with plain `pytest` —
  no install step required — via an explicit, documented mechanism.
- Unify all first-party imports, mock patch strings, and the run workflow on
  the `scantpaper.` dotted namespace.
- Drop the runtime `sys.path.insert` hacks.

**Non-Goals:**

- Changing any user-visible behaviour of the GUI, scanning, OCR, or saving.
- Changing packaged/installed behaviour: the console script `scantpaper`, the
  DEB, and CI install flows keep working as they do today.
- Converting the codebase to relative imports (rejected; see Decisions).

## Decisions

### D1. Package-absolute imports (`from scantpaper.const import ...`), not relative

Under `select = ["ALL"]`, `TID252` with the default `ban-relative-imports =
"parents"` already flags parent-relative imports. In a real package layout the
dominant case (a `dialog/` module importing a root-level module) *requires* a
parent-relative import (`from ..helpers import ...`), which ruff would reject.
Package-absolute imports sidestep the whole issue and need zero new lint
configuration.

Alternatives considered and rejected:

- **Relative imports** (`from ..helpers import ...`): requires adding
  `TID252`/`TID` to the ruff ignore list (backwards on the ratchet); splits
  the naming scheme from the (necessarily absolute) mock patch strings;
  contradicts what `select = ["ALL"]` enforces.
- **Keep flat imports** (`from const import ...`): only works while
  `scantpaper/` is on `sys.path` — precisely the implicit mechanism this
  change removes. Cannot survive a `src/`-as-package layout.

Note: AGENTS.md currently says "uses relative imports... no leading
`scantpaper`". That text describes the *current* flat reality, not a design
target. This change deliberately flips that convention; AGENTS.md is updated
in scope.

### D2. `src/` layout via setuptools `where = ["src"]`

Move `scantpaper/` → `src/scantpaper/`, add top-level `__init__.py`, and
point `[tool.setuptools.packages.find]` at `where = ["src"]`, removing the
stale `# This could be removed if we moved to a src-based layout` comment.
`package-data` (`app.ui`, `icons/**/*`) is unaffected because paths are
resolved relative to each module's `__file__` at runtime
(`app_window.py:149`, `app.py:58`).

### D3. Tests stay source-tree-bound via pytest `pythonpath = ["src"]`

pytest ≥ 7 provides the `pythonpath` ini option. Setting
`pythonpath = ["src"]` in `[tool.pytest.ini_options]` recreates — explicitly
and config-driven — what the missing-`__init__` basedir trick did implicitly:
`src/` lands on `sys.path` for every test run, so `scantpaper` resolves from
the working tree. This preserves plain `pytest` in CI even for the
`latest_w_ppa` job that does not `pip install`.

### D4. `__file__`-relative path computations get one extra directory

Under `src/scantpaper/`, these resolve one level shallower than today:

- `const.get_version()` (`const.py:11`): `Path(__file__).parent.parent /
  "pyproject.toml"` currently hits repo-root `pyproject.toml`; under `src/` it
  would hit `src/pyproject.toml` (missing). Fix: walk up to the repo root
  explicitly (e.g. `Path(__file__).resolve().parents[2]`), falling back to
  `importlib.metadata.version(PROG_NAME)` when packaged.
- `i18n.LOCALEDIR_PKG` (`i18n.py:7`): `__file__.parent / ".." / "locale"`
  changes meaning under `src/`. Fix to resolve the same physical path the
  package currently ships, preserving the "package locale dir first, then
  system dirs" behaviour.

### D5. Run workflow: module invocation instead of script execution

Running a file directly (`python3 scantpaper/app.py`) sets `__package__` to
empty, making any (dot-)import relative to the package illegal. With a real
package, the documented dev command becomes module invocation:
`PYTHONPATH=src python3 -m scantpaper.app`, or
`pip install -e . && scantpaper`. `app.py`'s `sys.path.insert(0, BASE_DIR)`
is deleted; the pyinstaller `sys.frozen`/`_MEIPASS` branch is kept (it still
provides the icon search path).

### D6. `dev/` scripts adopt the package namespace

`dev/generate_pot.py:10` drops its `sys.path.insert` and switches to
`from scantpaper.const import ...`; `dev/compile_mo.py` is updated
accordingly. `dev/` remains non-package (its `INP001` hits are excluded via
the `dev/*` path in ruff `per-file-ignores`, matching the "scripts folder,
not a package" intent).

## Risks / Trade-offs

- **Massive mechanical churn hiding as "just imports."** ~300 import lines + ~682
  mock targets + path computations. → Sequence the change (layout first,
  imports next, config after) and keep every intermediate commit green; grep
  counts (`from scantpaper.`) and test coverage gates make regressions loud.
- **Coverage measures the wrong copy.** `--cov=scantpaper` could silently
  measure the editable-installed copy instead of `src/scantpaper/` if the
  `pythonpath` injection is ever misconfigured. → `pythonpath = ["src"]` set
  once so both import and coverage resolve identically; verify in CI that
  `coverage.json` paths point at `src/scantpaper/`.
- **`latest_w_ppa` CI job (no `pip install`).** It relies on the current
  implicit basedir insertion; after the change it needs `pythonpath = ["src"]`
  to keep working uninstalled. → Covered by D3; add a CI assertion that the
  job runs without an install and imports from the source tree.
- **help2man hard-codes `python3 scantpaper/app.py`** in `deb.yml`. → Update
  to the module invocation used by the packaged console script; verify the man
  page still renders (`help2man --version-string`).
- **Run-workflow doc churn.** README cites script execution 6+ times.
  → Single pass updating README/CONTRIBUTING/AGENTS/deb.yml together (all in
  scope), so no stale instructions survive.
- **`selftest`/`timeout` before package rename confusion.** Coverage-gated
  tests asserting on exact filesystem paths (e.g. `test_app.py:258` pyinstaller
  `sys.path[0]` assertions) may need path updates. → Audit path assertions in
  tests as part of the layout move.

## Migration Plan

1. **Layout**: `git mv scantpaper src/scantpaper`; add
   `src/scantpaper/__init__.py`, `src/scantpaper/frontend/__init__.py`;
   minimal `pyproject.toml` (`where = ["src"]`, `pythonpath = ["src"]`).
2. **Imports**: rewrite each first-party import to the `scantpaper.` prefix in
   dependency order (const/i18n/helpers first, then aggregators, then
   dialogs/tests); update mock patch strings. `ruff check .` stays green
   throughout (`INP001` removed only at the end).
3. **Paths & hacks**: fix `const.get_version()`, `i18n.LOCALEDIR_PKG`,
   `app.py` sys.path removal, `dev/` scripts.
4. **Tooling & docs**: `deb.yml` help2man, README/CONTRIBUTING/AGENTS,
   remove `INP001` from ruff ignore (add `dev/*` per-file-ignore only).
5. **Verify**: `pytest` (root, uninstalled), `pytest-3` path, wheel build +
   `pip install .` smoke, console script, ruff `check`/`format`.

Rollback: reverting the layout commit restores the flat namespace; no
migration of user data or config involved.