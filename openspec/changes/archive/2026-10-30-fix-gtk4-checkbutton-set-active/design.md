# Design

## Context

See `proposal.md` - Why, and
`specs/scan-dialog-initialization/spec.md` for the required behaviour.

GTK4's `Gtk.CheckButton` is no longer a `Gtk.ToggleButton`; it derives
directly from `Gtk.Widget` and declares `set_active(setting)`. The GTK3-era
keyword `set_active(is_active=...)` therefore raises `TypeError`. The same
keyword is still valid for `Gtk.Switch` and `Gtk.ToggleButton`, so the
mistake is invisible at a glance and the shared setter's
`Gtk.CheckButton | Gtk.Switch` type does not expose it.

The affected branches are all in scan-dialog construction or the
Preferences apply path:

| Site | Trigger |
|------|---------|
| `scan_menu_item_mixins.py:336` | saved alternate rotation is on |
| `scan_menu_item_mixins.py:357` | the clean-up tool is missing |
| `scan_menu_item_mixins.py:359` | saved image clean-up is on |
| `scan_menu_item_mixins.py:401` | the user-defined-tool list is empty |
| `scan_menu_item_mixins.py:404` | saved user-defined tool is on |
| `edit_menu_mixins.py:445` | Preferences applied with no tools |
| `dialog/scan.py:1470` | the shared setter receives a `Gtk.CheckButton` |

The default settings avoid every row in the table, and the tests either mock
the module's `Gtk` or use `Mock(spec=Gtk.CheckButton)`, which accepts any
keyword. Some tests also assert the broken `is_active=` shape, so the suite
is green today.

## Goals / Non-Goals

**Goals:**

- Open the scan dialog successfully for every valid saved postprocessing
  state named by the spec.
- Apply Preferences with an empty tool list without disturbing the scan
  dialog.
- Add regression tests that use real `Gtk.CheckButton` widgets, so the
  parameter-name change cannot return unnoticed.

**Non-Goals:**

- Changing defaults, saved settings, or dialog layout.
- Auditing unrelated GTK3-era keyword calls that still work, such as
  `set_sensitive(sensitive=...)` and `set_visible(visible=...)`.
- Introducing a widget wrapper or a compatibility shim.
- Adding a project-wide lint rule for PyGObject call signatures.

## Decisions

### Call `set_active()` positionally

Replace `set_active(is_active=False)` with `set_active(False)`, and
`set_active(is_active=value)` with `set_active(value)`. A positional boolean
is accepted by both `Gtk.CheckButton` and `Gtk.Switch`, so the shared setter
needs no type switch.

Alternatives considered:

- **`set_property("active", value)`**: works for all three widget types and
  survives parameter renames, but it is less idiomatic and reads as a
  workaround rather than normal GTK code.
- **`set_active(setting=value)`**: correct for `Gtk.CheckButton` but wrong
  for `Gtk.Switch`, which keeps `is_active`. It would just move the trap to
  the other branch of the union.
- **A `set_check_active(widget, value)` helper**: hides a one-line call and
  adds indirection for a problem positional arguments already solve.

Ruff's FBT003 whitelists `set_*` calls by default, and the codebase already
uses positional `set_active(True)` throughout, so no lint suppression is
needed.

### Keep `_set_switch_widget` unchanged

`dialog/scan.py:848` calls `set_active(is_active=value)` on a value typed
`Gtk.Switch`, where the keyword is valid. Leaving it alone keeps the diff
focused; the shared `_set_checkbutton_active` is the only setter that needs
to handle both widget types positionally.

### Test with real widgets, not only mocks

Add one real-widget regression case per branch in the table. Each case
constructs the real control with the relevant setting and would fail with
the `TypeError` before the fix. Keep the existing mock-based behavioural
assertions, but change their expected call shape to the positional form.

Alternatives considered:

- **Rely on the type checker**: `gi.repository` has no stubs, so `ty` cannot
  see the parameter names and reports nothing.
- **Rely on a lint rule**: ruff has no rule for PyGObject signatures, and
  FBT003 deliberately ignores `set_*`.
- **Only update the mock assertions**: this would make the tests pass
  without proving that a real `Gtk.CheckButton` accepts the call, which is
  exactly how the bug survived.

### Give the behaviour its own capability

The triggers span alternate rotation, image clean-up and the user-defined
tool. A new `scan-dialog-initialization` capability owns "the dialog is
built from saved settings" once, instead of duplicating a crash-fix
requirement in three feature specs.

## Risks / Trade-offs

- **Real-widget tests need a display** -> the suite already runs under Xvfb,
  and other layout tests present real dialogs there.
- **Updating mock assertions could hide a future regression** -> the new
  real-widget cases are the guard; the mock assertions only describe the
  intended call.
- **`_set_checkbutton_active` may receive either widget type** -> positional
  `set_active(value)` is valid for both, which the design verifies with one
  real case each.
- **Ruff's allowlist could change** -> if FBT003 ever stops ignoring
  `set_*`, the project would need a maintainer-approved suppression; today
  no suppression is required.
- **Another GTK3-era keyword could be wrong elsewhere** -> this change
  fixes the confirmed `set_active` sites only; a broader audit is separate
  work.

## Migration Plan

None. There is no settings, data or file-format change. Rolling back means
reverting the calls and tests.

## Open Questions

None.
