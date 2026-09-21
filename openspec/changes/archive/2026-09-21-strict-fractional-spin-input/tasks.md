## 1. Shared helper

- [x] 1.1 Add `configure_fractional_spinbutton(widget, digits=FRACTIONAL_DIGITS)`
  to `src/scantpaper/helpers.py`: disable the `numeric` filter, set the
  digits, wire the value-driven `set_digits(fractional_digits(value))` trim
  on `value-changed`, connect the strict commit-time validator (parse
  `get_text()` with `parse_number(strict=True)`, revert via
  `set_value(get_value())` on `ValueError`) on `focus-out-event` and
  `activate`, then apply the initial digit trim.
- [x] 1.2 Add unit tests for the helper (plain `Gtk.SpinButton`): numeric is
  disabled; whole value shows without decimals and fractional with the
  comma/dot separator; typing a locale-valid fraction commits it; a
  non-locale separator and non-numeric text are rejected and the previous
  value restored.

## 2. Refactor the scan dialog to the shared helper

- [x] 2.1 In `src/scantpaper/dialog/sane.py`, remove the inline
  `set_digits(FRACTIONAL_DIGITS)` / `set_numeric(False)` and the private
  `_configure_fractional_spinbutton()`, calling the shared helper for
  `TYPE_FIXED` options after the initial `set_value()`.
- [x] 2.2 Keep the existing scan-dialog spin tests green
  (`test_0610_dialog_scan_sane.py`); they document the unchanged behaviour.

## 3. Apply the helper to the other fractional spin fields

- [x] 3.1 Page Properties dialog (`edit_menu_mixins.py`): drop
  `set_digits(1)` on the X/Y Resolution spin buttons and call the helper
  after each `set_value()`.
- [x] 3.2 Preferences (`preferences.py`): call the helper on the Blank
  threshold and Dark threshold spin buttons after their `set_value()`.
- [x] 3.3 Unpaper (`unpaper.py`): add a `"fractional": true` flag to the
  White/Black-threshold option definitions and call the helper in
  `_add_spinbutton()` when the flag is set.

## 4. Tests for the new call sites

- [x] 4.1 Properties dialog tests (`test_edit_menu_mixins.py`): DPI fields
  display a whole value as an integer (`300`), accept a locale-typed
  fraction, and reject a non-locale separator / non-numeric text (previous
  value restored).
- [x] 4.2 Preferences tests (`test_preferences_dialog.py` or
  `test_edit_menu_mixins.py`): Blank and Dark thresholds accept the locale
  separator and revert on invalid input.
- [x] 4.3 Unpaper tests (`test_34_unpaper.py`): White/Black thresholds accept
  the locale separator and revert on invalid input; integer spin options
  keep their previous behaviour.

## 5. Integration and quality gates

- [x] 5.1 Update README.md (and changelog.md) with the user-visible changes:
  DPI fields, blank/dark thresholds and unpaper thresholds accept the
  locale's decimal separator, reject non-locale separators at commit time,
  and display whole values without trailing zeros.
- [x] 5.2 Regenerate the translation template
  (`PYTHONPATH=src python3 dev/generate_pot.py`).
- [x] 5.3 Full suite green (`pytest`) with coverage not regressing beyond
  the standing exceptions; `ruff format`, `ruff check`, `ty check .` clean.