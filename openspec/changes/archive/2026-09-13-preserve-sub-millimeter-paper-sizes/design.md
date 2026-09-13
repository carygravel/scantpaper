# Design: preserve-sub-millimeter-paper-sizes

## Decision: D1 — Column type change

Switch the Width/Height/Left/Top columns of `PaperList` from `"int"` to
`"double"`, leveraging the existing `"double"` type in `SimpleList`'s
`column_types` (Python `float`, same `Gtk.CellRendererText`). This stops
PyGObject's ListStore from truncating `115.2` to `115` on load, and makes
`SimpleList.do_text_cell_edited` parse edits via `float(new_text)` instead
of `int(new_text)`, accepting fractional input.

## Decision: D2 — Integral display format

Attach a `Gtk.TreeViewColumn.set_cell_data_func` to each of the four
dimension columns that renders the float value with Python's `f"{value:g}"
format. This outputs integral values as `210`, `297` (no trailing `.0`)
and fractional values as `115.2`, matching both display spec requirements
without altering the stored dtype.

## Decision: D3 — No change to config coercion

`_normalise_types` in `config.py` inspects only top-level config keys; it
does not recurse into `Paper` dicts. The stored value is now `115.2`
(float) in the config where it was before `115` (int); `json.dumps`
serialises both correctly and `_normalise_types` compares only the outer
type (`dict`) which has not changed. No coercion code path is affected.

## Decision: D4 — Backward compatibility

Whole-millimetre integers already persisted in config files (e.g. `"x":
210`) load as JSON `int` → Python `int`. When `PaperList.__init__`
appends them to the `"double"` column they are stored as `float` 210.0
in the ListStore, then displayed as `210` via the D2 cell data function.
No value is changed. The round-trip on Apply writes `210.0` (float) back
to the config, which is numerically identical to `210` and causes no
compatibility issue.

## Decision: D5 — Invalid input handling

`SimpleList.do_text_cell_edited` for `float` columns calls
`float(new_text)`. Non-numeric input (`"abc"`) raises `ValueError`,
leaving the cell value unchanged, matching the spec requirement that
invalid input is rejected.
