## 1. Pilot & Conventions

- [x] 1.1 Annotate `src/scantpaper/const.py`, `src/scantpaper/i18n.py`,
      `src/scantpaper/pagerange.py`, `src/scantpaper/loop_helpers.py`,
      `src/scantpaper/helpers.py`. Add `from __future__ import annotations`
      to each, move type-only imports into `if TYPE_CHECKING:` blocks, and
      verify `ruff check --select ANN <modules>` reports 0. This is the pilot
      that establishes the house style (PEP 563, no `Any`, unions, `object`
      for polymorphic payloads) that later tasks follow.
- [x] 1.2 Confirm the project-wide checks still pass with the config
      untouched: `ruff check .`, `ruff format --check .`, and `pytest`.

## 2. Leaf Core

- [x] 2.1 Annotate `src/scantpaper/config.py`, `src/scantpaper/tesseract.py`,
      `src/scantpaper/text_layer_control.py`,
      `src/scantpaper/comboboxtext.py`,
      `src/scantpaper/entry_completion.py`, `src/scantpaper/progress.py`,
      `src/scantpaper/print_operation.py`, `src/scantpaper/app.py`,
      `src/scantpaper/postprocess_controls.py`
      (PEP 563 + `TYPE_CHECKING` moves + full annotations).
- [x] 2.2 Annotate `src/scantpaper/scanner/options.py`,
      `src/scantpaper/scanner/profile.py`, `src/scantpaper/frontend/*`
      (untyped SANE objects annotated with their concrete `sane.*` classes;
      no `Any`).
- [x] 2.3 Annotate the `dev/` scripts (`dev/compile_mo.py`,
      `dev/generate_pot.py`).
- [x] 2.4 Run `ruff check .`, `ruff format --check .`, and `pytest` to
      confirm the tree stays green.

## 3. Threads & IO

- [x] 3.1 Annotate `src/scantpaper/basethread.py` and
      `src/scantpaper/importthread.py`.
- [x] 3.2 Annotate `src/scantpaper/savethread.py` and
      `src/scantpaper/docthread.py`.
- [x] 3.3 Annotate `src/scantpaper/unpaper.py`.
- [x] 3.4 Run `ruff check .`, `ruff format --check .`, and `pytest`.

## 4. Core Model

- [x] 4.1 Annotate `src/scantpaper/basedocument.py`.
- [x] 4.2 Annotate `src/scantpaper/page.py`, `src/scantpaper/document.py`.
- [x] 4.3 Annotate `src/scantpaper/bboxtree.py` and
      `src/scantpaper/simplelist.py` (self-referencing
      `SimpleList`/`TiedList`/`TiedRow`; `__iter__` -> Iterator).
- [x] 4.4 Run `ruff check .`, `ruff format --check .`, and `pytest`.

## 5. UI

- [x] 5.1 Annotate `src/scantpaper/imageview.py` (all `@GObject.Property`
      getters/setters keep explicit `type=`).
- [x] 5.2 Annotate `src/scantpaper/canvas.py`.
- [x] 5.3 Annotate `src/scantpaper/app_window.py`.
- [x] 5.4 Run `ruff check .`, `ruff format --check .`, and `pytest`.

## 6. Menu Mixins

- [x] 6.1 Annotate `src/scantpaper/file_menu_mixins.py` and
      `src/scantpaper/edit_menu_mixins.py`.
- [x] 6.2 Annotate `src/scantpaper/tools_menu_mixins.py` and
      `src/scantpaper/scan_menu_item_mixins.py`.
- [x] 6.3 Annotate `src/scantpaper/session_mixins.py`.
- [x] 6.4 Run `ruff check .`, `ruff format --check .`, and `pytest`.

## 7. Dialogs

- [x] 7.1 Annotate `src/scantpaper/dialog/__init__.py`,
      `src/scantpaper/dialog/pagecontrols.py`,
      `src/scantpaper/dialog/preferences.py`,
      `src/scantpaper/dialog/crop.py`, `src/scantpaper/dialog/paperlist.py`.
- [x] 7.2 Annotate `src/scantpaper/dialog/save.py` and
      `src/scantpaper/dialog/sane.py`.
- [x] 7.3 Annotate `src/scantpaper/dialog/scan.py` (largest single module:
      233 violations).
- [x] 7.4 Run `ruff check .`, `ruff format --check .`, and `pytest`.

## 8. Tests

- [x] 8.1 Annotate `src/scantpaper/conftest.py` (fixtures annotated with
      their real types; PEP 563 + `TYPE_CHECKING` for pytest-only imports).
- [x] 8.2 Annotate the SANE dialog test files
      (`test_06*.py`, `test_0608*/`/`test_0609*/`, `test_0610`, `test_06182`,
      `test_06198`, `test_06199`, `test_0810*` etc. — the concentrated
      `ANN001`/`ANN202` clusters) and `src/scantpaper/tests/scan_mocks.py`.
- [x] 8.3 Annotate the remaining `src/scantpaper/tests/*.py` files fixture
      by fixture (`tmp_path: Path`, `pytest.MonkeyPatch`, mock objects).
- [x] 8.4 Confirm per-file: `ruff check --select ANN src/scantpaper/tests`
      reports 0, then `ruff check .`, `ruff format --check .`, `pytest`.

## 9. Config Flip & Enforcement

- [x] 9.1 Remove `ANN001`, `ANN002`, `ANN003`, `ANN201`, `ANN202` from the
      `[tool.ruff.lint]` `ignore` list in `pyproject.toml` and replace the
      stale ANN comment block. Leave `ANN401` enforced (no `Any` is written
      per `CONTRIBUTING.md`).
- [x] 9.2 Update `CONTRIBUTING.md` (Type Annotations) to document the
      adopted conventions: module-wide `from __future__ import annotations`,
      type-only imports in `TYPE_CHECKING` blocks, annotation of GTK signal
      handlers with `gi.repository` types, and the note that
      `@GObject.Property` must keep an explicit `type=` under lazy
      annotations.
- [x] 9.3 Final full verification: `ruff check .` (now including the ANN
      rules), `ruff format --check .`, grep for any stray `typing.Any`, and
      `pytest` with the coverage gate.

## Coverage note (accepted during implementation)

The annotation convention (`if TYPE_CHECKING:` blocks) adds lines that by
design never execute, and because the tests live inside the measured package
(`src/scantpaper/tests/`), `--cov=scantpaper` counts those test-side blocks as
missed lines. This permanently drops the aggregate below the old 99%
threshold, so `--cov-fail-under` is set to `98` and the whole package
(including `src/scantpaper/tests/` and the root `conftest.py`) is measured.
The full suite reports ~98.5% aggregate coverage. Newly-uncovered lines are
only acceptable inside `if TYPE_CHECKING:` blocks (see AGENTS.md and
CONTRIBUTING.md).