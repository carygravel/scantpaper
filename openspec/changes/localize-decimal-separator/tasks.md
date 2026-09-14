## 1. Separator helper

- [x] 1.1 Add a cached `decimal_separator()` helper (query → set from env →
      `localeconv` → restore) in `helpers.py`, reused value-only per design.
- [x] 1.2 Unit-test the helper: under a comma locale it returns `","`, under a
      dot locale `"."`, and it leaves the process `LC_NUMERIC` unchanged.

## 2. Locale-aware input parsing

- [x] 2.1 Write failing tests in `test_simplelist.py` that editing an `mm`/
      `double` cell with the locale's separator (e.g. `115,2` under a comma
      locale) stores `115.2`, that a period still works in a comma locale, and
      that invalid input is still rejected.
- [x] 2.2 In `SimpleList.do_text_cell_edited`, normalize the locale decimal
      separator to `"."` before `float()` for `float`-typed columns.

## 3. Locale-aware display

- [x] 3.1 Write a failing test in `test_simplelist.py` that
      `float_g_cell_renderer` renders `115.2` as `115,2` under a comma locale
      and still renders `210.0` as `210`.
- [x] 3.2 Render such a value with the localized separator in
      `float_g_cell_renderer`, keeping whole-number rendering unchanged.

## 4. Verification

- [x] 4.1 Run the full test suite with coverage (`pytest` per
      `pyproject.toml`) under the default locale; confirm no regressions.
- [x] 4.2 Spot-check a `PaperList` render under `LC_ALL=de_DE.UTF-8` showing
      `115,2` and whole sizes as `210`.
- [x] 4.3 Run `ruff format` and `ruff check` on changed files.

## 5. Docs

- [x] 5.1 Update `changelog.md` (unreleased section).
- [x] 5.2 Update README.md if it documents paper-size dimension entry (check
      before editing).