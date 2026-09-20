## Context

The scan dialog builds widgets per SANE option type in
`src/scantpaper/dialog/sane.py::_create_widget()`. Options with a tuple
constraint (e.g. the scan-area fields `br-x`, `br-y`,
`tl-x`, `tl-y`, `page-height`, `page-width`) go to
`_create_widget_spinbutton()`, which calls
`Gtk.SpinButton.new_with_range(lo, hi, step)` and never sets
`set_digits()`. GTK initializes spin buttons with `digits = 0`, so:

- typed fractional separators are stripped and arrow buttons step by whole
  units (`step` is derived from `constraint[2]`, which for `br-x`/`br-y`
  is `0.0` and falls back to `1` — see proposal.md "Why");
- literal values displayed by `widget.set_value()` lose their fraction.

`dialog/scan.py::_set_spinbutton_widget()` re-applies range/increments on
reload and would re-introduce a fractional step from `constraint[2]`.

Locale helpers live in `src/scantpaper/helpers.py`:
`format_number()` (locale separator, `:g` so trailing zeros are trimmed),
`format_number_precise()`, and the currently lenient `parse_number()`
(accepts the locale separator *and* an ASCII period). Separator helpers
read the locale from the environment, temporarily flipping `LC_NUMERIC`,
and are `lru_cache`d with `cache_clear()` in the `comma_locale`/`dot_locale`
test fixtures. Today `parse_number` is only used on user-typed text
(dialog/sane.py entry activate, simplelist cell edits) and on legacy
pre-v3 profile strings via `_coerce_option_value()` in dialog/scan.py.

Specs: `openspec/specs/scan-option-values/spec.md` codifies locale display
for combobox/entry options; the tuple-constrained (spin) path is not
covered, and "a period still works" is currently a stated requirement.

## Goals / Non-Goals

**Goals:**

- Ranged FIXED scan options (scan-area size fields and any other tuple
  FIXED option) accept typed fractional values with the locale's decimal
  separator, preserve the sub-unit part, and display without trailing
  zeros.
- Number entry becomes strict: only the locale's decimal and grouping
  separators are accepted; a period typed in a comma locale is rejected
  instead of silently converted.
- Arrow steps remain whole-unit; fractional values are reached by typing.
- Fractional precision is a shared constant (2) so it can later be made
  configurable in one place.

**Non-Goals:**

- No per-driver or runtime-configurable precision yet; the constant is the
  single knob.
- No change to legacy pre-v3 profile value import — `_coerce_option_value()`
  keeps its tolerant conversion so old configs still load.
- No change to combobox rendering beyond what the locale helpers already
  provide; no data-model or dependency changes.

## Decisions

### 1. Fractional spin buttons: value-driven `set_digits()` + commit-time validation

Set `widget.set_digits(FRACTIONAL_DIGITS)` on tuple-constrained `TYPE_FIXED`
options (integer options keep `digits = 0`) and keep the digit count in sync
with the value:

- A `value-changed` handler re-runs `set_digits(fractional_digits(value))`,
  where `fractional_digits()` returns 0 for integral values and 2 otherwise.
  An integral value therefore renders as "174" (no trailing zeros) while a
  fractional value renders as "115,2" — GTK draws the separator from the
  process locale (`nl_langinfo`), not from what was typed. `set_digits`
  only emits `value-changed` when the digit count actually changes, so the
  round trip does not recurse.
- Strictness lives at commit time. GTK's default text parser is locale-aware
  but *lenient* (in de_DE it accepts both a comma and an ASCII period), so
  the pre-commit text is validated by our strict parser instead. The
  `focus-out-event` and `activate` handlers run before GTK's own commit;
  they check `widget.get_text()` and, on `ValueError`, call
  `set_value(widget.get_value())` to restore the last valid value, so a
  rejected non-locale separator never reaches the backend.

- *Why not the `input`/`output` signals (spiked first):* PyGObject cannot
  use them. The `input` signal's out-value (`gdouble*`) crosses the border
  as an unusable object our callback cannot write, so returning `True`
  leaves GTK working with garbage; the `output` handler returning `True`
  after `set_text()` re-enters the commit cycle and produces an empty text.
  The `set_digits`-trimming approach needs neither.
- *Why not `set_digits(2)` unconditionally:* it renders "174,00"; the
  value-driven digit count does not.
- *Alternatives considered and rejected:* key-filtering the internal entry
  (`insert_text` on spin buttons is a silent no-op in PyGObject even when
  realized and focused); overriding the `output` handler (broken, above).

### 2. Strict locale-aware number parser

Replace the lenient transform in `parse_number()` with a strict one and
add a `strict`-or-lenient choice at the call sites:

- Strict parsing accepts: an optional leading `+`/`-`, decimal digits, the
  locale's decimal separator (at most once), and the locale's grouping
  (thousands) separator, which must sit between groups of exactly three
  digits counted from the right; any other character raises `ValueError`.
  The grouping rule is the standard right-aligned 3-digit rule; exotic
  grouping schemes (e.g. the Indian 3-2) are out of scope for now.
- A new `grouping_separator()` helper mirrors `decimal_separator()`'s
  environment-driven, cache-able pattern (`localeconv()["thousands_sep"]`).
- User-typing sites use strict mode: free-text entry activation
  (`dialog/sane.py::activate_entry_cb`), cell edits
  (`simplelist.py::do_text_cell_edited`), and the spin-button commit-time
  validator from Decision 1. These sites also wrap parsing in
  `try/except ValueError` and ignore the edit (keep the previous value)
  rather than raising.
- `_coerce_option_value()` (legacy pre-v3 profile strings, spec requirement
  "Legacy profile values with a decimal comma are imported") keeps the old
  lenient behaviour via an explicit `strict=False` path.

- *Why:* the maintainer explicitly wants typing to be strict — a period in
  a comma locale previously fell through the lenient `.replace()` and was
  silently accepted. Split points keep the legacy import requirement from
  the scan-option-values spec intact (values written as commas must still
  load).
- *Why grouping matters for strictness:* in `de_DE` the grouping separator
  *is* a period, so a naive "reject anything that is not the decimal
  separator" would both wrongly reject valid grouped numbers and wrongly
  accept `115.2` as grouping; validating grouping placement makes the
  behaviour deterministic (and rejects `115.2`).

### 3. Integer arrow steps, enforced at both rebuild points

Compute the spin-button step with a shared helper that clamps to a whole
unit: `1 if constraint[2] <= 0 else max(1, int(constraint[2]))` (a driver
step below 1 mm, or non-integer, becomes 1; an integer 2 stays 2). Apply it:

- in `_create_widget_spinbutton()` (`dialog/sane.py`) when building, and
- in `_set_spinbutton_widget()` (`dialog/scan.py`), which currently re-reads
  a possibly-fractional `constraint[2]` on every reload and would silently
  undo Decision 1.

The `value-changed` → `set_digits` path of Decision 1 guarantees the
displayed fractional part survives a step (114.8 + 1 = 115.8), which is why
no fractional stepping is needed.

### 4. Single shared precision constant

Add `FRACTIONAL_DIGITS = 2` to `src/scantpaper/const.py` (used by
`sane.py` for `set_digits()` and by `fractional_digits()`). It is
deliberately *not* wired to a setting yet; opening the config door is
deferred until the right option location/name is known (see Open
Questions).

## Risks / Trade-offs

- [Propagating GTK float display of the full driver precision
  (297.179992…) is now rounded to 2 decimals in the widget (value stays
  exact in the adjustment).] → Acceptable per the 2-digit decision; exact
  values still hit the backend on programmatic `set_value` reloads, and the
  backend re-clamps via existing tolerance checks.
- [Spiked: the PyGObject `input`/`output` signals do not marshal
  (input out-value un-writable; output `set_text` re-entrancy empties the
  field).] → Resolved in Decision 1: value-driven `set_digits()` trimming
  plus pre-commit validation. The strict parser still guards the
  entry/paperlist/commit-time boundaries.
- [Making `parse_number` strict could disturb unsearched callers that feed
  it machine-formatted text.] → Audit every call site in the change; only
  user-typing sites go strict, `_coerce_option_value()` stays lenient.
- [Strict grouping may reject values escaping the right-aligned 3-digit
  rule in exotic locales.] → Out of scope; documented; standard rule used.

## Migration Plan

No data migration. Behaviour change is confined to the scan dialog's
numeric widgets; config and profiles load unchanged (legacy path stays
lenient). Rollback is a revert of the change, since no persisted format is
altered.

## Open Questions

- **Where/how to expose the fractional precision as a user setting?**
  Deferred; `FRACTIONAL_DIGITS` is the single knob for now. A future
  change may promote it to a preferences row (likely a "units/precision"
  grouping) without touching the specs here.
- **Exact PyGObject contract of the `Gtk.SpinButton` `input` signal**
  (return-vs-out-struct). Resolved during the implementation spike: the
  signal is unusable through PyGObject (see Decision 1), so the design no
  longer depends on it.