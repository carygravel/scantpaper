## 1. Helpers and constants

- [x] 1.1 Add `FRACTIONAL_DIGITS = 2` to `src/scantpaper/const.py` with a
  docstring stating it is the single knob for fractional-precision display.
- [x] 1.2 Add a `grouping_separator()` helper to `src/scantpaper/helpers.py`
  that mirrors `decimal_separator()` (reads from the environment with the
  temporary `LC_NUMERIC` flip, `lru_cache`d, using
  `localeconv()["thousands_sep"]`), and clear its cache in the
  `comma_locale`/`dot_locale` fixtures alongside `decimal_separator`.
- [x] 1.3 Add unit tests for `grouping_separator()` under the
  `comma_locale` (expects the locale's grouping separator) and `dot_locale`
  fixtures.
- [x] 1.4 Rework `parse_number()` in `src/scantpaper/helpers.py` with a
  `strict` keyword (default `True`): strict mode accepts digits, one locale
  decimal separator, and the locale grouping separator only between
  right-aligned groups of exactly three digits; anything else raises
  `ValueError`. Lenient mode keeps the current replace+parse behaviour.
- [x] 1.5 Add unit tests proving strict parsing: comma accepted in a comma
  locale, period rejected in a comma locale, a valid grouped number like
  "1.234" parses to 1234, a malformed grouping like "115.2" in a comma
  locale is rejected, and lenient mode still accepts both separators.
- [x] 1.6 Add an integer-step helper (`spin_step(constraint)` = 1 when
  `constraint[2] <= 0` else `max(1, int(constraint[2]))`) in
  `src/scantpaper/helpers.py` with unit tests.

## 2. Fractional spin-button widgets

- [x] 2.1 Spike the fractional-value display mechanism. Conclusion: PyGObject
  cannot use the `input`/`output` signals (input out-value un-writable,
  output `set_text` re-entrancy empties the field), so value-driven
  `set_digits()` trimming (`set_digits(fractional_digits(value))` on
  `value-changed`) is the working pattern; strictness is enforced at
  commit time by validating the pre-commit text in `focus-out`/`activate`
  handlers and reverting via `set_value(get_value())` on `ValueError`.
- [x] 2.2 In `_create_widget_spinbutton()` (`src/scantpaper/dialog/sane.py`),
  call `set_digits(FRACTIONAL_DIGITS)` for `TYPE_FIXED` options, compute the
  step with the `spin_step()` helper, and connect `_configure_fractional_spinbutton()`
  (trim digits on `value-changed`; strict pre-commit validation with revert
  on `focus-out-event`/`activate`).
- [x] 2.3 In `_set_spinbutton_widget()` (`src/scantpaper/dialog/scan.py`),
  replace the `constraint[2]` step with the same `spin_step()` helper so
  reloads keep whole-unit steps and do not disturb the digits/validation
  setup.
- [x] 2.4 Add functional tests for spin-button options (a tuple-constrained
  `TYPE_FIXED` option): typing a fractional value with the locale separator
  commits the canonical value and re-shows it correctly; non-locale
  separators are rejected and the previous value is restored; display
  trims trailing zeros (174 shows as "174"); arrow clicks step by whole
  units while preserving the fractional part; `TYPE_INT` spin buttons keep
  integer-only behaviour.

## 3. Strict parsing at the remaining user-typing sites

- [x] 3.1 In `dialog/sane.py::activate_entry_cb`, wrap the `parse_number`
  call in `try/except ValueError` and ignore invalid edits, so strict
  parsing never raises out of a user-typed free-text entry.
- [x] 3.2 In `simplelist.py::do_text_cell_edited`, use strict parsing for
  float cells and swallow `ValueError` (keep the previous value) instead of
  propagating, matching the PaperList dimension cells.
- [x] 3.3 Keep `_coerce_option_value()` (`dialog/scan.py`) on the lenient
  `strict=False` path so pre-v3 profile strings (e.g. written with a comma)
  still import; add a regression test that a comma-written legacy value
  loads under both locales.
- [x] 3.4 Update tests that assert the old lax behaviour (an ASCII period
  accepted in a comma locale) to expect rejection, including any entry and
  paper-list cell cases.

## 4. Integration and quality gates

- [x] 4.1 Verify the full suite passes (`pytest`), coverage does not regress
  beyond the standing exceptions, `ruff format`, `ruff check`, and
  `ty check .` are clean.
- [x] 4.2 Update README.md with the user-visible changes: scan-area size
  fields accept fractional values with the locale's decimal separator and
  keep whole-unit arrow steps; only locale separators are accepted when
  typing numbers.
- [x] 4.3 Regenerate the translation template
  (`PYTHONPATH=src python3 dev/generate_pot.py`) if any user-visible string
  changed.