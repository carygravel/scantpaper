# Design

## Context

The GTK4 migration (commit `e4e067a2`) replaced the `button-press-event` /
`button-release-event` widget signals - which deliver every mouse button -
with a `Gtk.GestureClick`, one per widget in `Canvas.__init__`
(`canvas.py`, ~line 543) and `ImageView.__init__` (`imageview.py`, ~line
733). The two handler bodies kept their GTK3 `Gdk.BUTTON_MIDDLE` branches
unchanged. `GtkGestureClick`'s `button` property defaults to 1, so it only
reports primary-button presses; middle presses are silently dropped and the
MMB branches are unreachable. See `proposal.md - Why`.

Handlers already decide per-button behaviour, so no handler logic has to
change: `SelectorDragger.button_pressed` routes button 1 to `Selector` and
`Gdk.BUTTON_MIDDLE` to `Dragger`; `Canvas._button_pressed` starts a pan on
middle and a draw on 1; every tool returns `False` for
`Gdk.BUTTON_SECONDARY`. The app already adds a *separate*
`Gtk.GestureClick(button=Gdk.BUTTON_SECONDARY)` for context menus
(`_add_secondary_click_controller`, `app_window.py:779`) - evidence the
default-gesture limitation was known for the right button but never fixed
for the middle button.

## Goals / Non-Goals

**Goals:**
- Make the single click gesture of both widgets deliver every button to
  the existing handlers, restoring MMB panning exactly as in GTK3.
- Add a unit-level regression test that fails if the gesture ever stops
  receiving non-primary buttons (the current tests mock the gesture and
  cannot detect this).

**Non-Goals:**
- No change to the tool architecture (`Tool` / `Dragger` / `Selector` /
  `SelectorDragger`), the `image_control_tool` setting, or the
  `_add_secondary_click_controller` context-menu gesture.
- No new UI, config, or undo/redo interaction.
- Not changing the existing quirk that the pure `Selector` tool draws a
  selection on any non-secondary press (it predates and is unrelated to
  this bug).

## Decisions

### 1. Configure the existing gesture with `button=0` (listen to any button)

Change the construction in both files to
`click = Gtk.GestureClick(button=0)` rather than `Gtk.GestureClick()`.

- Rationale: `button=0` restores the GTK3 contract where every button
  reaches the handler and the per-button dispatch in the tools decides
  what happens. It is a two-site, one-keyword change; no handler or tool
  edits, no new controllers.
- Alternatives considered:
  - *A dedicated second `Gtk.GestureClick(button=Gdk.BUTTON_MIDDLE)` per
    widget.* More explicit about intent, but duplicates wiring, splits
    the single-dispatch model (the ImageView routes through one
    `SelectorDragger.button_pressed`), and would need release/edge
    handling duplicated too. Rejected as heavier and divergent.
  - *Relying on the unset default.* The default is version-dependent (it
    "happened to be" 1 on GTK 4.24.1 where the bug reproduces) and is
    exactly the source of the regression. Rejected.
- Verified empirically: with injected X11 button events (libXtst under
  xvfb) on GTK 4.24.1, a stock `ImageView`/`Canvas` never receives a
  middle press and never pans, while `button=0` delivers button 2, the
  combined tool switches to `Dragger`, and both widgets pan; LMB
  selection and RMB context-menu behaviour are unaffected.

### 2. Regression test asserts the controller listens to any button

The existing unit tests call `_button_pressed(_gesture(...), ...)` with a
mock gesture, so they exercise the dispatch but never the delivery. Add a
test per widget that scans `observe_controllers()` for its
`Gtk.GestureClick` and asserts `get_property("button") == 0`.

- Rationale: this is the minimal reliable CI guard that a later
  refactor cannot silently re-break MMB. Synthesising real GTK4 button
  events in-process is not viable (`Gtk.test_widget_click` is not
  exposed through introspection here), and an XTest-based harness is too
  heavy for the unit suite.
- The existing dispatch tests (e.g. `test_selector_dragger_tool`
  asserting MMB routes `SelectorDragger` to `Dragger`) remain as the
  behavioral layer above the delivery guard.

## Risks / Trade-offs

[With `button=0`, secondary presses now also reach the tool handlers]
→ each tool's `button_pressed` already guards `Gdk.BUTTON_SECONDARY` and
returns `False`; the separate popup gesture still receives the event, so
context menus are unchanged. Verified in the injection harness.

[Back/forward (side) buttons are delivered too]
→ handlers act only on buttons 1 and 2; other buttons fall through as
no-ops, matching the GTK3 signal behaviour.

[Setting `button=0` depends on GTK honoring 0 as "any button"]
→ documented GTK behaviour ("0 to listen for any button"); if a future
GTK changed this, the delivery test (Decision 2) would fail loudly
rather than regressing silently.

[X11 middle-click primary-selection paste on some desktops]
→ applies only to widgets with clipboard handling (entries, text
views); `ImageView` and `Canvas` are plain `Gtk.DrawingArea`s, so no
conflict. Noted, not mitigated.

## Migration Plan

No deployment or data steps: this is a two-line source fix. Rollback is
reverting the two gesture constructions. The new delivery test removes
itself on revert because it asserts the `button=0` configuration.

## Open Questions

None. Any unknowns (which buttons each tool should act on) are already
decided by existing, unchanged dispatch code and are deliberately out of
scope per the Non-Goals.
