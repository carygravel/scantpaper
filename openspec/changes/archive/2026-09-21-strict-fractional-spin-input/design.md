## Context

The scan dialog's fractional spin-button wiring lives in the private method
`SaneScanDialog._configure_fractional_spinbutton()`
(`src/scantpaper/dialog/sane.py`) and is called from
`_create_widget_spinbutton()` only for `TYPE_FIXED` options. It:

1. clears GTK's `numeric` filter (so the locale decimal separator survives
   typing),
2. keeps the displayed digits value-driven (`fractional_digits()`, which
   returns 0 for whole values and `FRACTIONAL_DIGITS` otherwise) so trailing
   zeros are trimmed,
3. validates the pre-commit text with `parse_number(strict=True)` on
   `focus-out-event`/`activate` and reverts to the previous valid value on
   `ValueError`.

Three other dialogs still build fractional spin buttons without any of this:
the page Properties dialog X/Y Resolution (DPI) fields
(`edit_menu_mixins.py:67,76`, `set_digits(1)`), the Preferences Blank/Dark
thresholds (`preferences.py:287,299`, 0..1 step 0.01), and the unpaper
White/Black thresholds (`unpaper.py:225,236`, 0..1 step 0.01). Each shows the
same bug: GTK's `numeric` filter strips the typed separator and the commit
parser silently mis-parses or truncates garbage.

Proposal: `openspec/changes/strict-fractional-spin-input/proposal.md`.

## Goals / Non-Goals

**Goals:**

- One shared helper implementing the fractional spin-button pattern, used by
  the scan dialog and the three other dialogs (DRY, single behaviour).
- All four groups of fractional spin fields accept the locale's decimal
  separator, reject non-locale separators and non-numeric text at commit
  time, and display whole values without a trailing decimal part.
- Zero behavioural change in the scan dialog (already specified by
  `scan-option-values`; stays green).

**Non-Goals:**

- No change to the paper-sizes editor dimension cells (list-cell edits with
  their own spec and lenient period handling).
- No change to integer spin buttons anywhere (their `numeric` filtering is
  the desired behaviour).
- No new configuration surface; `FRACTIONAL_DIGITS` stays the single knob.
- No change to how unpaper/preferences read the value back; only the
  spin-button widget behaviour changes.

## Decisions

### 1. Shared helper `configure_fractional_spinbutton(widget, digits=FRACTIONAL_DIGITS)` in `helpers.py`

Move the wiring out of the scan dialog into a module function in
`src/scantpaper/helpers.py`:

- `widget.set_numeric(False)`
- `widget.set_digits(digits)`
- connect a `value-changed` handler that re-runs
  `set_digits(fractional_digits(value))` (0 for whole, `FRACTIONAL_DIGITS`
  otherwise)
- connect `focus-out-event` and `activate` handlers that validate
  `parse_number(widget.get_text())` and, on `ValueError`, call
  `set_value(widget.get_value())` to restore the last valid value
- apply the initial trim `set_digits(fractional_digits(widget.get_value()))`
  so a field configured after `set_value()` displays correctly immediately

- *Why a module helper:* three new call sites would otherwise duplicate the
  same five-step wiring; a single helper keeps the behaviour identical and
  testable in one place. `format_number_precise`, `parse_number` etc. already
  follow this helpers-module pattern.
- *Why a `digits` parameter:* DPI, thresholds and scan fields currently use
  the same `FRACTIONAL_DIGITS` value, but the parameter documents intent and
  keeps the helper general without hard-coding a constant lookup.
- *Alternatives considered:* keep the scan-dialog method and copy it — rejected
  (three copies to keep in sync); extract to a small mixin — rejected (no
  shared state/class hierarchy between these dialogs, a function is enough).

### 2. Scan dialog refactor to the shared helper

`_create_widget_spinbutton()` drops its inline `set_digits(FRACTIONAL_DIGITS)`
and `set_numeric(False)` and the private
`_configure_fractional_spinbutton()` disappears; the shared helper is called
for `TYPE_FIXED` options after the initial `set_value()`. Reordering note:
the helper sets digits/numeric itself, so ordering "set value first, then
configure" is required and is already the case (`set_value` precedes the
current `_configure_fractional_spinbutton` call).

### 3. Apply the helper at the three new call sites

- **Properties dialog DPI** (`edit_menu_mixins.py`): drop `set_digits(1)`,
  call the helper on both spin buttons after `set_value()`. Whole DPI values
  now render as `300` instead of `300.0`; fractional as `215,9`.
- **Preferences thresholds** (`preferences.py`): call the helper on
  `_spinbuttonb` and `_spinbuttond` after their `set_value()`. Fractional
  thresholds render at `FRACTIONAL_DIGITS` from the value instead of a fixed
  2 digits (0.9 shows as `0,9`, 0.33 as `0,33`).
- **Unpaper thresholds** (`unpaper.py`): `_add_spinbutton()` stays generic;
  the two threshold option definitions gain a `"fractional": true` flag and
  `_add_spinbutton()` calls the helper when the flag is set. Ints/pages
  options are untouched.

*Why flags on the unpaper options:* the unpaper option table drives widget
construction generically; a per-option marker keeps that generic builder free
of type sniffing.

### 4. Strictness only at commit time, as in the scan dialog

Rejection reverts the field's text to the last valid adjustment value. The
same caveat as the scan dialog applies: GTK's own commit parser is lenient
and our focus-out/activate handlers run before it, so a rejected value never
reaches the rest of the application. Values are read back via the
adjustment (`get_value()`), which only ever holds valid values even if the
user abandons an invalid edit without leaving the field.

## Risks / Trade-offs

- **Display change for whole DPI values** (`300.0` → `300`) is the intended
  new behaviour and is documented as **BREAKING** in the proposal.
- **Invalid text before revert:** until focus leaves (or Enter is pressed),
  typed garbage is visible in the field; this matches the scan dialog and
  prevents nothing since reads happen from `get_value()`.
- **`digits` rounding:** values are rounded to `FRACTIONAL_DIGITS` (2) for
  display; the float held by the adjustment keeps full driver precision, and
  scanner/DPI values that far exceed 2 decimals are not meaningful here.
- **Existing scan-dialog tests must stay green** with the refactor; the
  behaviour is identical, and any test that asserted private-method details
  will be updated to target the helper instead.