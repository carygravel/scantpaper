## 1. Shared helpers

- [x] 1.1 Add `format_number(number)`, `format_number_precise(number)` and
      `parse_number(text, number_type=float)` to `helpers.py`, built on
      `decimal_separator()`. Scan-option display uses the precise variant so
      driver values round-trip unchanged; the `:g` variant keeps the paper
      editor's display rule.
- [x] 1.2 Unit tests in `test_helpers.py`: `format_number` shows `115,2` in a
      comma locale and `115.2`/`210`/`150` in a dot locale;
      `format_number_precise` keeps `1.07818603515625` (`1,07818603515625`
      in a comma locale); `parse_number("115,2")` → `115.2` under a comma
      locale, `parse_number("abc")` raises, and `parse_number("1,2.3")`
      raises.

## 2. Paper-size editor reuses the helpers (no behaviour change)

- [x] 2.1 Refactor `float_g_cell_renderer` to call `format_number` and
      `do_text_cell_edited` to call `parse_number` in `simplelist.py`.
- [x] 2.2 Verify the existing `test_simplelist.py` locale and whole-number
      tests pass unchanged (proves output parity).

## 3. Localized combobox items

- [x] 3.1 Add failing tests in `test_0610_dialog_scan_sane.py`: a numeric
      list option shows 215,9 in a comma locale and 215.9 in a dot locale,
      whole-number items show no decimal part, and string items still use
      `d_sane`.
- [x] 3.2 Implement localized item text in `_create_widget_combobox`
      (`dialog/sane.py`) via `format_number_precise` for numerics, keeping
      `str(d_sane(constraint))` for strings.
- [x] 3.3 Mirror in `_set_combobox_widget` (`dialog/scan.py`) and extend the
      same tests to cover it.

## 4. Localized free-text entries

- [x] 4.1 Add failing tests in `test_0610_dialog_scan_sane.py`: a TYPE_FIXED
      entry shows 115,2 in a comma locale; typing 115,2 and activating sends
      `value=115.2` to `set_option`; typing 115.2 still sends 115.2; a
      TYPE_STRING entry keeps text values unchanged.
- [x] 4.2 Implement localized display and typed-value parsing by option type
      in `_create_widget_entry` (`dialog/sane.py`).
- [x] 4.3 Mirror localized display in `_set_entry_widget` (`dialog/scan.py`).

## 5. Robust legacy-profile coercion

- [x] 5.1 Add failing tests: `_coerce_option_value` maps the string "115,2"
      to `115.2` for a FIXED option (under a comma locale) and still maps
      "115.2" in a dot locale.
- [x] 5.2 Implement the string-aware `float` path in `_coerce_option_value`
      (`dialog/scan.py`).

## 6. Verification

- [x] 6.1 Run the full test suite with coverage (`pytest` per
      `pyproject.toml`); confirm no regressions and coverage threshold met.
- [x] 6.2 `ruff format` and `ruff check` on all changed files.
- [x] 6.3 Update `changelog.md` (unreleased section).