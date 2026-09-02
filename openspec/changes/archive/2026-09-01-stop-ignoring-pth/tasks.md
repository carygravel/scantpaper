## 1. Baseline

- [x] 1.1 Record baseline `ruff check --select PTH --statistics` (expect 193 errors) and full `ruff check .` output, save to a scratch note for diff comparison
- [x] 1.2 Record baseline `pylint` warning count (via `pytest --pylint` or `pylint scantpaper`) so it can be verified not to increase
- [x] 1.3 Confirm working tree is clean with `git status` before any `--fix` runs, so the automated diff is reviewable in isolation

## 2. Safe autofix pass (124 violations)

- [x] 2.1 Run `ruff check --select PTH --preview --fix` (safe-only autofix) and verify 124 PTH errors disappear with `ruff check --select PTH --statistics`
- [x] 2.2 Run `ruff check .` and confirm no new non-PTH violations were introduced by the autofix
- [x] 2.3 Run `black --check .` to confirm the autofix output is black-clean (re-run `black` on any files it flags)
- [x] 2.4 Run `pytest` and confirm the full suite passes with the 99% coverage gate (`--cov-fail-under=99`)
- [x] 2.5 Review the git diff of the safe pass for correctness (skim-level; these are semantically neutral, watch for import churn only)

## 3. Unsafe autofix pass (40 violations)

- [x] 3.1 Dry-run first with `ruff check --select PTH --preview --fix --unsafe-fixes --diff` and confirm only the expected ~40 unsafe hunks (PTH120/PTH100/PTH109/PTH116/PTH111 + 1 PTH123) appear
- [x] 3.2 Apply with `ruff check --select PTH --preview --fix --unsafe-fixes`, then verify PTH count is down to the 29 manual sites via `--statistics`
- [x] 3.3 Review every unsafe hunk in `git diff` — especially PTH100 (`abspath`→`Path.resolve()`: symlink/normalization semantics) and PTH120 (`dirname`→`parent`: `""` vs `"."` edge) — and correct any semantic drift manually
- [x] 3.4 Verify the `noqa: SIM115` comment on the cross-scope lockfile handle in `session_mixins.py` still targets the right rule after the `open()`/`Path.open()` conversion
- [x] 3.5 Run `black --check .`, `pytest` (coverage >=99%), and `pylint` baseline comparison; all must pass/flat

## 4. Manual: PTH118 `os.path.join` (14 sites)

- [x] 4.1 Convert the 3 `os.path.join` sites in `scantpaper/session_mixins.py` (`Path(a) / b`) and verify `pytest scantpaper/tests/test_session_mixins.py` passes if present, else via full suite
- [x] 4.2 Convert `scantpaper/app.py`, `scantpaper/app_window.py`, `scantpaper/i18n.py` `os.path.join` sites and verify the relevant tests pass (e.g. `test_app.py`, `test_app_window.py`)
- [x] 4.3 Convert the remaining 7 in `tests/` (`test_8_config.py` ×3, `test_app.py` ×1, `test_text_layer_control.py` ×3) and verify those test files pass
- [x] 4.4 Confirm `ruff check --select PTH118` reports zero errors after this group

## 5. Manual: PTH207 `glob` (15 sites)

- [x] 5.1 Convert `glob.glob` to `Path.glob`/`Path.rglob` in `dev/generate_pot.py` (×2) — verify `intltool-extract`/`subprocess` consumers accept `Path` or convert to `str` at the boundary, and the file still runs
- [x] 5.2 Convert the `/*`-slurp recursion in `scantpaper/helpers.py` and `scantpaper/file_menu_mixins.py` (×2) — check `recursive_slurp` and concat of two glob results handle `Path` objects
- [x] 5.3 Convert `scantpaper/importthread.py` (×2) — verify `x-*` extraction cleanup and `_correlate_pdf_images` sorting/index-matching still work with `Path` items
- [x] 5.4 Convert `scantpaper/app_window.py`, `scantpaper/docthread.py`, `scantpaper/session_mixins.py` glob sites — check `recursive_slurp(glob.glob("/etc/*-release"))`, tessdata dirs, and the `scantpaper-????????.sdb` crash-session scan
- [x] 5.5 Convert glob sites in `tests/` (`test_0601_dialog_scan.py`, `test_1111_save_pdf.py` ×4) and verify those tests pass
- [x] 5.6 Confirm `ruff check --select PTH207` reports zero errors and run `pytest` for this group

## 6. Enable PTH and final gate

- [x] 6.1 Remove `"PTH"` from the `ignore` list in `pyproject.toml` and replace the stale "60k lines" comment with an accurate note reflecting the completed migration (PTH now enforced)
- [x] 6.2 Run `ruff check .` and confirm zero PTH violations and no new violations in other rule families
- [x] 6.3 Run `black --check .` and confirm clean
- [x] 6.4 Run `pytest` and confirm the full suite passes with coverage >=99%
- [x] 6.5 Run pylint baseline comparison and confirm warning count did not increase
- [x] 6.6 Final review: `git diff` / `git status` sanity check, then suggest a commit message per `CONTRIBUTING.md` (starts with a gitmoji)