## Why

In locales that use a comma as the decimal separator (e.g. `de_DE.UTF-8`), the
paper-sizes editor displays fractional dimensions with a period (`115.2`) and
rejects comma input: `do_text_cell_edited` parses cells with `float()`, which
is locale-independent and refuses `115,2`, and `float_g_cell_renderer`
formats with `f"{value:g}"`, which never localizes. Users in such locales
cannot enter sub-millimetre dimensions with their own keyboard conventions,
and what they see does not match what they type.

The locale state is also fragile: `Page.get_resolution` force-sets
`LC_NUMERIC` to `"C"` without restoring it, so the entire process silently
loses the user's locale after the first save. The fix therefore must not
depend on the ambient `LC_NUMERIC` at parse/render time.

## What Changes

- The paper-sizes editor SHALL accept the locale's decimal separator when a
  user edits a dimension cell; `115,2` in `de_DE.UTF-8` stores `115.2`. A
  period is still accepted for compatibility, and truly invalid input is
  still rejected.
- The paper-sizes editor SHALL display dimension values with the locale's
  decimal separator (`115,2` in `de_DE`), while whole-millimetre values keep
  rendering without a trailing decimal part (`210`).
- The decimal separator is determined deterministically from the user's
  configured locale (not the ambient `LC_NUMERIC`, which code elsewhere
  flips to `"C"`).
- No change to how values are stored (config stays canonical JSON numbers) or
  to `int`-typed cells.

## Capabilities

### New Capabilities

<!-- None. -->

### Modified Capabilities

- `paper-size-editor`: the fractional dimension requirements gain localization
  behaviour — comma/decimal-separator input is accepted, and fractional values
  are displayed with the locale's decimal separator.

## Impact

- `src/scantpaper/simplelist.py`: `do_text_cell_edited` float parsing
  (`double`/`mm` columns) tolerates the locale's decimal separator;
  `float_g_cell_renderer` formats using the locale's decimal separator.
  `scalar_cell_renderer` is unaffected (pass-through text).
- `src/scantpaper/helpers.py` (or `const.py`): a small helper captures the
  user's configured decimal separator without disturbing in-process locale
  state.
- `src/scantpaper/dialog/paperlist.py`: no direct change (inherits the
  behaviour from `SimpleList`).
- Tests in `test_simplelist.py` and `test_dialog_paperlist.py`.
- No config schema, storage, or dependency changes; `LC_NUMERIC` toggling in
  `page.py` is out of scope (the fix must be robust to it, not repair it).