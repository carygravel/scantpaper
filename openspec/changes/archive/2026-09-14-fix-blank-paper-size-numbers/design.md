## Context

See proposal.md - Why. The bug: since preserve-sub-millimeter-paper-sizes,
the four dimension columns of the paper-sizes list render blank while name
and units columns show text.

The paper-sizes dimensions are displayed through the `"mm"` column type
(simplelist.py), whose renderer is the data function
`float_g_cell_renderer`. It formats the stored float (`210.0` -> `210`,
`115.2` -> `115.2`) and assigns it with `cell.text = ...`. Empirical
investigation (PyGObject 3.57.1 / GTK 3.24.52) shows this assignment does
not reach the GObject `text` property: `getattr(cell, "text")` returns the
value but `cell.get_property("text")` stays `None`, and GTK paints the
property, so the cell is empty. `cell.set_property("text", value)` and
`cell.props.text = value` both set the real property and the value renders.

The previous `"int"`/`"text"` column types worked because they bind the
renderer attribute directly (`Gtk.TreeViewColumn(title, renderer, text=i)`),
a mechanism GTK itself drives through the property system.

Constraints:
- `scalar_cell_renderer` (simplelist.py) is affected identically and is
  currently unused by production columns.
- The existing test `test_mm_display_without_trailing_decimal` passes while
  the bug is present because it asserts `cell.text` (the Python attribute),
  not `cell.get_property("text")`.

## Goals / Non-Goals

**Goals:**

- The four dimension columns paint their formatted values (`210`, `115.2`).
- Tests assert the GObject property GTK actually paints, so a regression is
  caught.
- Both data-func renderers (`float_g_cell_renderer`, `scalar_cell_renderer`)
  use a mechanism that works.

**Non-Goals:**

- Any change to storage, config, editing, or apply round-trips of paper
  sizes; they are already correct.
- Changing column types or the display format (`f"{value:g}"`).

## Decisions

### 1. Set the GObject property, not the Python attribute

Replace `cell.text = ...` with `cell.set_property("text", ...)` in both
`float_g_cell_renderer` and `scalar_cell_renderer`.

- **Why:** the only channel GTK reads when painting a `Gtk.CellRendererText`
  is the GObject `text` property; the attribute-assignment form
  demonstrably leaves it `None` in the project's PyGObject/GTK versions.
- **Alternative:** `cell.props.text = ...` is equivalent; `set_property` is
  chosen for explicitness and since the renderer is a `CellRendererText`
  where the property is statically known.
- **Why both renderers:** identical latent bug; fixing one and leaving the
  other invites the same empty-cell failure if `scalar` is ever used.

### 2. Pin the test to the paint path

`test_mm_display_without_trailing_decimal` asserts
`cell.get_property("text")` instead of `cell.text`.

- **Why:** the old assertion reads the Python attribute, which the broken
  implementation satisfied, so the test was green while the UI was blank.
- **Trade-off:** a unit test still cannot prove GTK rasterized pixels; the
  property assertion is the closest fast, headless check and is what GTK
  consumes. This satisfies the new spec scenario without an on-screen
  render test.

## Risks / Trade-offs

- [Some other PyGObject assignment pattern also silently no-ops] -> only
  `cell.text =` was implicated in the investigation; the fix uses the
  property API directly, which is the mechanism GTK documents.
- [Test asserts property but GTK still fails to paint in some theme/font] ->
  not observed; the control column rendered correctly in reproduction once
  the property was set, and the change is confined to the display path.

## Migration Plan

No config, schema, or dependency changes. Before/after rendering differs
only in that the previously blank dimension cells now show their values;
reverting is restoring the attribute assignment.

## Open Questions

None.