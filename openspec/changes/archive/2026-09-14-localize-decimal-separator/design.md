## Context

See proposal.md - Why. The paper-sizes editor shows and parses fractional
dimensions with a hard-coded period. Python's `float()` and
`f"{value:g}"` ignore the `LC_NUMERIC` locale, so in a decimal-comma locale
(`de_DE.UTF-8`) users see `115.2` and cannot type `115,2` (it is rejected as
invalid input).

Constraint that shapes this design: `Page.get_resolution` (page.py:226)
force-sets `LC_NUMERIC` to `"C"` and never restores it, so once any save has
run the whole process is in `"C"`. Any locale-aware behaviour that reads the
ambient `LC_NUMERIC` at dialog time would silently switch back to period
display mid-session. The design therefore captures the user's configured
separator deterministically and never depends on ambient locale state.

Empirically verified (Python, CPython under `LC_ALL=de_DE.UTF-8`):
- `float("115,2")` raises `ValueError` even with `LC_NUMERIC=de_DE`.
- `f"{115.2:g}"` → `"115.2"` regardless of locale.
- The configured separator can be read even after a flip to `"C"` via
  query → `setlocale(LC_NUMERIC, "")` → `localeconv()` → restore.
- Stored values are canonical floats; only the text boundary localizes.

## Goals / Non-Goals

**Goals:**

- A user in a decimal-comma locale can enter `115,2` and sees `115,2`;
  a period still works and is still accepted everywhere.
- Whole-millimetre values keep rendering as `210`, `297` (no trailing `.0`).
- The locale is read robustly even after some other code has forced the
  process into `LC_NUMERIC=C`.
- Truly invalid input stays rejected.

**Non-Goals:**

- Repairing the `LC_NUMERIC` flip in `page.py` (separate concern; this
  change must merely be robust to it).
- Changing the stored config format (values stay canonical JSON numbers).
- Localizing `int`-typed columns (no decimal separator involved).
- Extending to other decimal-separator-sensitive dialogs beyond the
  paper-sizes editor's `mm`/`double` columns.

## Decisions

### 1. Capture the configured separator once, cached, via setlocale round-trip

A small helper (module-level function in `helpers.py`, cached on first call)
reads the separator without leaving the process locale changed:

```python
def decimal_separator():
    previous = locale.setlocale(locale.LC_NUMERIC, None)   # query only
    locale.setlocale(locale.LC_NUMERIC, "")                # set from environment
    sep = locale.localeconv()["decimal_point"]
    locale.setlocale(locale.LC_NUMERIC, previous)          # restore
    return sep
```

- **Why:** `setlocale(LC_NUMERIC, "")` resets to the user's configured
  locale regardless of any earlier code flipping it to `"C"`, and the
  query-then-restore leaves the process state untouched. Caching avoids
  repeated process-global setlocale churn on every draw/edit.
- **Alternative rejected:** reading `locale.localeconv()` directly at render
  time — returns the *ambient* separator, so breakage once `page.py` has
  flipped the process to `"C"`.
- **Note:** setlocale is process-global; the brief env round-trip could in
  theory race a worker thread also touching locale. The capture is cached on
  first use (main thread, dialog open) and paper-list edits/renders are
  main-thread only, so no practical contention.

### 2. Parse the locale separator on input, then canonical `float()`

In `SimpleList.do_text_cell_edited`, for `float`-typed columns (`double`,
`mm`), normalize the locale's separator to a period before `float()`:

```python
sep = decimal_separator()
if sep not in (".", ""):
    new_text = new_text.replace(sep, ".", 1)
new_text = float(new_text)
```

- **Why:** deterministic, locale-independent after normalization; the same
  `float()` path handles whole numbers and rejects the rest. A value with two
  separators (`1,2,3`) normalizes to `1.2.3` and is rejected, so input stays
  strict. `int` columns are untouched.
- **Alternative rejected:** `locale.atof` — depends on ambient `LC_NUMERIC`,
  which the process does not keep stable.

### 3. Display with the localized separator

`float_g_cell_renderer` keeps `f"{value:g}"` (which already yields `210`
for `210.0` and `115.2` for `115.2`) and then substitutes the separator:

```python
text = f"{value:g}"
sep = decimal_separator()
if sep not in (".", ""):
    text = text.replace(".", sep)
cell.set_property("text", text)
```

- **Why:** reuses the tested `:g` whole/fractional logic and only changes
  the separator glyph. Dot-locale users see exactly today's output.
- **Trade-off accepted:** `:g` may render an exponent (`1e+30`) whose `.`
  would also be replaced; paper dimensions never reach exponent range, and
  this is a display-only cosmetic corner.

### 4. Scope: only `mm`/`double` float columns

Parsing lives in the shared `do_text_cell_edited`, but `mm` is the only
production float column type (`double` appears only in tests), so the
change stays effectively within the paper-sizes editor.

## Risks / Trade-offs

- [Ambient locale contention from worker threads] -> capture is cached and
  main-thread-only; the round-trip is a single setlocale pair.
- [Exponent notation corrupted by separator substitution] -> out of range
  for millimetre dimensions; cosmetic-only if it ever occurred.
- [A locale with a non-period, non-comma separator, e.g. Arabic thousands
  separator `٫`] -> handled generically since the helper returns whatever
  `localeconv` reports; replaces on input and back on display.
- [Some locale uses an empty decimal point] -> guarded (`sep not in (".", "")`).

## Migration Plan

No config, schema, or dependency changes. Display changes only for
fractional values in decimal-comma locales (visual, expected); input becomes
more permissive. Reverting is restoring `float(new_text)` and
`f"{value:g}"`.

## Open Questions

None.