# Design

## Context

See `proposal.md` - Why for the motivation. The relevant current state:

- Both the `ImageView._draw_func` (`imageview.py`) and the canvas
  `_draw_selection_rubberband` (`canvas.py`) already add the `rubberband`
  CSS class to their own style context and call
  `Gtk.render_background()`/`Gtk.render_frame()`.
- The GTK4 default theme only styles `rubberband` as a node that is a child
  of selection widgets (`flowbox > rubberband`, `treeview.view >
  rubberband`, `gridview > rubberband`, ...). It ships no `.rubberband`
  *class* rule, so both widgets have painted nothing since the GTK3 to GTK4
  port, on GTK 4.6, 4.14 and 4.24 alike.
- Existing tests assert that the render calls happen with the right
  rectangle, not that any pixel is painted - which is why the breakage
  passed CI.
- The compatibility floor is GTK 4.6 / PyGObject 3.42 (jammy) until
  2027-06. `CssProvider.load_from_data()` exists at the floor;
  `load_from_string()` does not.
- `Gtk.StyleContext` and the `render_*` helpers are deprecated since GTK
  4.10 but present (not removed) on every supported version, and are not
  deprecated at the jammy floor.

## Goals / Non-Goals

**Goals:**

- Make both selection rectangles visibly paint on every supported GTK
  version (4.6, 4.14, 4.24) by shipping the missing `.rubberband` class
  rule.
- Keep the selection themeable: it follows the active theme, and a user's
  `~/.config/gtk-4.0/gtk.css` `.rubberband` rule overrides the shipped
  default (the behaviour the README already documents).
- Add pixel-level regression tests so this cannot regress silently again.
- Stay entirely on the jammy floor (GTK 4.6 / PyGObject 3.42).

**Non-Goals:**

- Dropping jammy or raising the floor (tracked separately in
  `release_procedure.md`).
- Moving the selection off the deprecated `render_*`/`StyleContext` path to
  `GtkSnapshot` before jammy is dropped; that is listed in the release
  procedure's "When jammy is dropped" modernisation list.
- Changing selection geometry, persistence, or the two draw paths
  themselves.

## Decisions

### Ship a `.rubberband` class rule instead of drawing with cairo

Provide the missing style through an application `Gtk.CssProvider` (option
A). Rationale: themability - the selection keeps following the active GTK
theme and the user's stylesheet. The alternative (drawing the rectangle
with raw cairo calls) is faster and sidesteps the deprecated style APIs,
but hardcodes a colour and abandons CSS theming. Performance is a wash
(measured: a few microseconds per frame either way against a frame
dominated by image painting), so themability decides.

### Host the rule beside the thumbnail stylesheet, one provider per app

Add `_attach_selection_css()` next to `_attach_thumbnail_css()` in
`app_window.py`, and call it from `_populate_main_window()` beside the
existing thumbnail call. It builds a `Gtk.CssProvider`, loads the rule with
`load_from_data()`, and attaches it to the display at
`Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION`.

- `load_from_data()` is the floor method; do not use `load_from_string()`
  (GTK 4.12+).
- APPLICATION priority (600) sits below the user stylesheet priority (800),
  so a user's gtk.css rule wins, preserving the README-documented
  customisation.
- A single display-level provider covers the image view and every canvas;
  no per-widget providers are needed.

### Default colours come from the theme

Draft rule: `background-color: alpha(@theme_selected_bg_color, 0.2);
border: 1px solid @theme_selected_bg_color;`. This makes the default
adaptive and keeps the selection readable in light and dark themes. The
rule also sets `background-image: none`, so an `.imageview`
`background-image` (from a theme or a user stylesheet) can never bleed
through the selection overlay. The alternative (a fixed RGB such as the
GTK3-era blue) is deterministic but theme-blind and would clash with dark
themes; it remains the fallback if the theme colour variable does not
resolve on GTK 4.6 (see Open Questions).

### Regression tests read pixels, not call counts

Add tests that render the real widgets to an offscreen cairo surface and
assert the selection region contains pixels painted with the `.rubberband`
style. Reuse the existing offscreen-surface helpers (`_render_view` and
`get_pixel` in `tests/test_imageview.py`, and the canvas draw-path test
pattern in `tests/test_7_canvas.py`). Include one test that overrides the
rule at a higher priority and asserts the rendered colour changes, covering
the themability contract end to end.

Pixel tests are sensitive to CSS providers installed by earlier tests
(providers are display-global and normally outlive a single test).
`test_transparency` in `test_imageview.py` attached a provider for one
assertion and never removed it; the leaked `.imageview` background-image
changed the colour of every later selection render. That test now removes
its provider in a `finally` block, and each selection test holds the rule it
needs for exactly its own duration (see the `_selection_css` fixture), so
the assertions are order-independent.

### Accept the GTK >= 4.10 deprecation warnings until jammy drops

`render_background`/`render_frame`/`get_style_context` stay in use because
they are the only themed way to paint into a DrawingArea's cairo context at
the 4.6 floor; the `GtkSnapshot` replacement is 4.10+, off the floor.
Clearing them is already scheduled in `release_procedure.md`. No code
change is needed for this today; the rule is loaded with non-deprecated
`CssProvider`/`load_from_data`/`add_provider_for_display` calls.

## Risks / Trade-offs

- **Deprecation warnings persist on noble/sid** (GTK 4.10+). →
  Accepted; required for jammy compatibility; removal is planned at the
  jammy drop.
- **`@theme_selected_bg_color` may not resolve on GTK 4.6.** → Verify at
  implementation; fall back to a fixed colour covered by the pixel tests.
- **A user rule might restyle other widgets bearing the class.** → Only
  the ImageView and the Canvas use the `rubberband` class; no other widget
  is affected.
- **Coverage threshold regressions.** → The new tests exercise already-
  covered draw paths with stronger assertions; keep uncovered lines at or
  below the current level.

## Migration Plan

Source-only change, no data migration. On deploy the rule is attached at
window startup; the `oldest` CI job (jammy, GTK 4.6) exercises the
`load_from_data()` path in every run. Rollback is a revert of the change.

## Open Questions

- Does `@theme_selected_bg_color` resolve under GTK 4.6's CSS engine, or
  should the shipped default be a fixed RGBA? This affects the rule's
  default colour only, not the spec, the approach, or the task breakdown.
