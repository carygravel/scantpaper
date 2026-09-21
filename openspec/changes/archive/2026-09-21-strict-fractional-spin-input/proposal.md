## Why

The scan dialog's fractional spin fields now accept the locale's decimal
separator, reject non-locale separators, and trim trailing zeros, but three
other dialogs still build fractional spin buttons the old way: GTK's
`numeric` filter strips the separator while typing (`0,9` becomes `09`), the
commit parser silently truncates or misreads garbage, and nothing rejects a
period in a comma locale. Users editing page resolution (DPI), the blank/dark
thresholds, or the unpaper thresholds run into the exact bug we fixed in the
scan dialog, and the strictness rules are inconsistent across dialogs.

## What Changes

- Extract the fractional spin-button wiring (disable the `numeric` filter,
  value-driven digit trimming, strict commit validation with revert on
  `ValueError`) from the scan dialog into a shared helper, and reuse it in the
  scan dialog so all four call sites share one implementation (DRY).
- Apply the pattern to the remaining fractional spin buttons:
  - X/Y Resolution (DPI) fields in the page Properties dialog — display
    whole values without a decimal part (`300` instead of `300.0`) and
    fractional values with the locale separator (`215,9`).
  - Blank threshold and Dark threshold spin buttons in Preferences.
  - White threshold and Black threshold spin buttons in the unpaper dialog.
- Typed input in these fields: the locale's decimal separator SHALL be
  accepted; any other separator character (e.g. a period in a comma locale)
  and any non-numeric text SHALL be rejected at commit time and the field
  SHALL revert to its previous valid value.
- **BREAKING:** whole DPI values no longer display with a trailing `.0`, and
  a fixed `1`-digit DPI display is replaced by the same trailing-zero
  trimming used by the scan dialog. This only affects how values are shown in
  the Properties dialog, not the stored page metadata.
- No change to the paper-sizes editor cells (they are list-cell edits, not
  spin buttons, and keep their own lenient "period also works" requirement).

## Capabilities

### New Capabilities

- `fractional-number-input`: user-editable fractional numeric spin fields
  across the application's dialogs accept the locale's decimal separator,
  reject non-locale separators and non-numeric text at commit time (reverting
  to the previous value), and display whole values without a trailing decimal
  part.

### Modified Capabilities

None. The scan-dialog behaviour stays as already specified in
`scan-option-values`; this change generalizes that behaviour to the other
fractional spin fields.

## Impact

- `src/scantpaper/helpers.py`: new shared `configure_fractional_spinbutton()`
  helper (numeric off, `FRACTIONAL_DIGITS`-based trimming, strict commit
  revert) and its unit tests.
- `src/scantpaper/dialog/sane.py`: replace the private
  `_configure_fractional_spinbutton()` with the shared helper; behaviour
  unchanged.
- `src/scantpaper/edit_menu_mixins.py`: DPI fields (X/Y Resolution).
- `src/scantpaper/dialog/preferences.py`: Blank threshold, Dark threshold.
- `src/scantpaper/unpaper.py`: White threshold, Black threshold.
- Tests: `test_helpers.py`, `test_0610_dialog_scan_sane.py`
  (regression/no-change), `test_edit_menu_mixins.py`,
  `test_preferences_dialog.py`, unpaper dialog tests.
- No new dependencies; reuses `FRACTIONAL_DIGITS`, `fractional_digits()`,
  `parse_number(strict=True)`.