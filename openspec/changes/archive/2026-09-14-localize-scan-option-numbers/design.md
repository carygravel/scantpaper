## Context

See proposal.md - Why. The paper-size editor already localizes decimal
separators through `helpers.decimal_separator()` (a cached, env-derived
separator that ignores the process's ambient `LC_NUMERIC`, which other code
flips to `"C"`). The scan dialog renders numeric scan-option values with
`str()` and parses free-text entries with the bare `float()`, so comma
locales see dots and cannot type commas.

Verified code paths (file:line):
- `dialog/sane.py:302` — `widget.append_text(str(d_sane(constraint)))` for
  combobox items; for numeric constraints `d_sane(n)` is a no-op gettext
  round-trip, so this is `str(<float>)` → dots.
- `dialog/sane.py:330` — `widget.set_text(str(val))` in `_create_widget_entry`.
- `dialog/sane.py:335` — `value = widget.get_text()`; passed verbatim to
  `set_option`.
- `dialog/scan.py:811` — mirror of the combobox populate
  (`_set_combobox_widget`), `d_sane(str(entry))`.
- `dialog/scan.py:820` — mirror entry default (`_set_entry_widget`),
  `widget.set_text(str(value))`.
- `dialog/scan.py:81` — `_coerce_option_value`: `float(val)` on pre-v3 config
  text; a decimal comma raises `ValueError`.

## Goals / Non-Goals

**Goals:**

- Numeric scan-option values (list items and free-text defaults) display
  with the locale separator at full driver precision, so the text
  round-trips back to the same number; integer-valued options keep no
  decimal part.
- Free-text numeric entries accept the locale separator and send canonical
  numbers (float for TYPE_FIXED) to the backend; period still works.
- Pre-v3 profile floats with a decimal comma are imported instead of
  crashing the apply.
- The paper-size editor keeps byte-identical output (refactor-through-shared-
  helpers only).

**Non-Goals:**

- Changing how values are stored (profiles/config stay canonical numbers).
- String-typed (non-numeric) scan options: display keeps using `d_sane()`
  translation; entry text is passed through untouched.
- Unpaper's comma-joined option strings, `importthread`/`bboxtree`
  subprocess/hOCR parsing, and the user-defined-tool `%r` substitution —
  machine formats that must stay dot.
- The `"%.1f GiB"` size estimate message (cosmetic; out of scope here).
- Repairing the `page.py:226` `LC_NUMERIC="C"` leak (separate cleanup; the
  shared helpers are already robust to it).

## Decisions

### 1. Three shared helpers in `helpers.py`, built on `decimal_separator()`

```python
def format_number(number):
    text = f"{number:g}"
    sep = decimal_separator()
    if sep not in (".", ""):
        text = text.replace(".", sep)
    return text


def format_number_precise(number):
    text = str(number)
    sep = decimal_separator()
    if sep not in (".", ""):
        text = text.replace(".", sep)
    return text


def parse_number(text, number_type=float):
    sep = decimal_separator()
    if sep not in (".", ""):
        text = text.replace(sep, ".", 1)
    return number_type(text)
```

- `format_number` mirrors exactly what `float_g_cell_renderer` already does
  for `mm` cells, so the paper-size editor output cannot change. Its `:g`
  trimming (whole numbers show no decimal part) is the paper editor's
  established display rule.
- `format_number_precise` keeps `str()`'s full precision and only localizes
  the separator. Scan-option values arrive from the driver at full precision
  (e.g. `1.07818603515625`); trimming the visible text would silently change
  what the user re-sends, so scan-option surfaces use this one. Integer
  values still render without a decimal part.
- `parse_number` normalizes a single locale separator to `.` and lets
  `float()`/`int()` validate the rest (a `1,2.3` input still raises).
- **Why separate from `decimal_separator`:** the call sites need the
  parse/format invariant ("type the same thing you see") in one place, and
  both scan-option widgets and the paper-size editor share it.

### 2. Combobox items: localize numerics, keep `d_sane` for strings

In `_create_widget_combobox` (sane.py) and `_set_combobox_widget` (scan.py):

```python
if isinstance(constraint, (int, float)):
    widget.append_text(format_number_precise(constraint))
else:
    widget.append_text(str(d_sane(constraint)))
```

- **Why:** list constraints are alternate values of a numeric option;
  selecting an item still hands the raw constraint value to the backend
  (`sane.py:319`), so only the visible text changes. String items (rare,
  driver-localized labels) keep translating exactly as today.

### 3. Free-text entries: localized display + typed values per option type

In `_create_widget_entry` (sane.py):

- Display: `str(val)` → `format_number_precise(val)` when the option type is
  numeric (TYPE_INT / TYPE_FIXED), else unchanged.
- Activate callback: build the typed value by option type so the backend
  receives a canonical number:

```python
text = widget.get_text()
if opt.type == enums.TYPE_FIXED:
    value = parse_number(text)
elif opt.type == enums.TYPE_INT:
    value = parse_number(text, int)
else:
    value = text
```

In `_set_entry_widget` (scan.py), mirror the localized display for numeric
values.

- **Why parse at the widget boundary:** the string that leaves the dialog must
  already be canonical; the thread/driver is not locale-aware.
- **Today's behaviour:** the entry already forwards the raw string; for
  numeric options python-sane would still want a number, so moving the
  conversion into the dialog makes the locale case work without changing the
  STRING/TYPE_STRING path.

### 4. Pre-v3 profile coercion tolerates a decimal comma

`_coerce_option_value` (scan.py):

```python
if opt.type == enums.TYPE_FIXED:
    if isinstance(val, str):
        return parse_number(val)
    return float(val)
```

- Numeric config values already parsing fine stay unchanged; only string
  values route through the locale-aware parse. The `ValueError` on `115,2`
  disappears.

### 5. Paper-size editor refactors to the shared helpers

`float_g_cell_renderer` and `do_text_cell_edited` call `format_number` /
`parse_number` instead of inlining the separator juggling.

- **Why:** one implementation of "type what you see" for both surfaces; the
  existing `test_simplelist.py` locale tests and the `test_helpers.py`
  separator tests must pass unmodified.

## Risks / Trade-offs

- [Comma-typed text reaching the driver through the entry for non-numeric
  options] -> STRING/TYPE_STRING options pass text unchanged, exactly as
  today; only FIXED/INT parse.
- [`d_sane` translate round-trip changes for numeric combobox items] ->
  numerics were never translated (gettext is a no-op on numbers); only the
  separator changes.
- [SANE constraint values outside the intended display range] -> the scan
  surfaces use `format_number_precise` (full-precision `str()`), so no
  precision is ever trimmed; only the separator is localized.

## Migration Plan

No config/schema/storage changes. Old behavior is restored by using
`str(n)`/`float(s)` as before. Profile values stay canonical numbers under
all locales.

## Open Questions

None.