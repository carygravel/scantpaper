## Why

The scan dialog's size/area fields (`tl-x`, `tl-y`, `br-x`, `br-y`,
`page-height`, `page-width`) are `Gtk.SpinButton`s built with
`Gtk.SpinButton.new_with_range()`, which initializes the widget with
`digits = 0`. As a result users cannot type any decimal separator (`.` or
`,`) into these fields and the `+`/`-` arrows step only by whole units —
even though the scanner driver exposes fractional millimetre values (e.g.
`br-y` with constraint `(0.0, 431.8, 0.0)`). A user on `de_DE.UTF-8`
reports they still cannot enter `115,2`. The earlier locale work only wired
fractional/locale handling into the free-text-`Entry`, `ComboBoxText`, and
paper-list paths; the tuple-constrained (spin button) path was missed.

While here, we tighten the current decimal-separator behaviour: today
typing an ASCII period is accepted even in comma locales, which is lax.
We now accept only the separators (decimal and grouping) that the active
locale defines.

## What Changes

- Scan-area spin buttons (`TYPE_FIXED` options with a tuple constraint)
  accept fractional typed input using the locale's decimal separator and
  preserve sub-millimetre precision while the widget is active.
- Fractional spin buttons format their text without trailing zeros
  (174.0 displays as "174", 115.2 as "115,2" in a comma locale).
- Number parsing becomes **strict** about separators: only the decimal
  and grouping separators of the active locale are accepted. **BREAKING**
  — an ASCII period is no longer accepted when the locale's decimal
  separator is a comma.
- Arrow-step behaviour is unchanged: `+`/`-` continue to step in whole
  units; sub-integer values are entered by typing.
- Fractional precision is fixed at 2 decimal places for now (a constant in
  `const.py`), pending a decision on where/how to expose it as a setting.
- Keystroke sanitization: characters outside the locale's accepted set are
  rejected while editing spin button text.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `scan-option-values`: the requirement that "a period still works" in
  comma locales is tightened to accept **only** the locale-defined decimal
  and grouping separators; and the fractional/locale-display guarantees
  are extended from free-text entries to ranged (spin-button) scan options
  such as the scan-area dimensions.

## Impact

- `src/scantpaper/dialog/sane.py`: `_create_widget_spinbutton()` sets
  fractional digits, steps stay integer, and connects `input`/`output`
  handlers for strict, locale-aware parsing and zero-trimmed formatting.
- `src/scantpaper/helpers.py`: `parse_number()` and friends become strict
  about the locale's decimal and grouping separators (a period typed in a
  comma locale is rejected instead of silently converted).
- `src/scantpaper/dialog/scan.py`: `_set_spinbutton_widget()` (re-)displays
  fractional values correctly.
- `src/scantpaper/const.py`: a new shared constant for the fractional
  precision (2), following the single-source-of-truth convention.
- Tests: new cases for fractional spin-button input under `comma_locale`
  and `dot_locale`, strict-separator rejection, zero-trimmed display, and
  integer arrow steps; existing locale tests updated where they assert the
  now-stricter behaviour.
- No dependency changes; no data-model changes.