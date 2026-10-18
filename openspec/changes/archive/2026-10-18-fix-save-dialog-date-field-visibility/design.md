## Context

See `proposal.md - Why`. In GTK4, `Gtk.CheckButton`'s `activate` signal is
only emitted for keyboard activation (Space/Enter) or explicit
`gtk_widget_activate()`. Mouse clicks call `gtk_check_button_set_active()`
directly and emit only `toggled`. During the GTK3→GTK4 migration, some check
button connections were changed from `clicked` (GTK3) to `activate` (GTK4),
but `activate` is not the equivalent for check buttons under GTK4. The
"Specify" radio in the Save dialog and grouped check buttons in Page
Controls are affected.

## Goals / Non-Goals

**Goals:**
- Make clicking "Specify" in the Save dialog reveal the Date/Time entry
  field.
- Correct grouped check button signal connections in
  `dialog/pagecontrols.py` to respond to mouse clicks.
- Preserve correct behavior for keyboard activation (Space/Enter) and for
  programmatic state changes where appropriate.
- Update tests to match the corrected semantics without weakening coverage.

**Non-Goals:**
- Large refactors or changing widget hierarchies/layout.
- Changes to metadata persistence logic or the `meta_datetime` property
  semantics (the fix is purely signal wiring).
- Fixing unrelated GTK4 signal issues beyond the identified ones.

## Decisions

**Decision 1: Use `toggled` instead of `activate` for the Save dialog
"Specify" check button.**

- **Rationale:** In GTK4, mouse clicks on `Gtk.CheckButton` emit `toggled`,
  not `activate`. Connecting to `toggled` fires on mouse clicks, group
  deactivations (so clicking "Now" while "Specify" is active hides the
  entry), and also fires when `set_active()` is called programmatically.
  The handler checks `get_active()`, so it is correct in all cases. This
  also fixes the initial state when constructing with
  `select_datetime=True`.
- **Alternatives considered:**
  - Keep `activate` and also connect to `toggled`: adds redundancy and can
    leave the `select_datetime` property stale in subtle cases.
  - Use `activate` only: fails for mouse clicks (the reported bug).
- **Implementation:** In `src/scantpaper/dialog/save.py`, connect
  `_clicked_specify_date_button` to `"toggled"` instead of `"activate"`.
  The handler method keeps its name (tests call it directly; renaming adds
  churn without benefit).

**Decision 2: Apply the same fix to `dialog/pagecontrols.py`, deferring
the connections until the initial widget state is in place.**

- **Rationale:** Same migration error: `bscanall`, `bscannum`, and
  `buttons` connect to `"activate"` and should connect to `"toggled"`.
  However, unlike the Save dialog, these widgets' handlers feed property
  setters that touch widgets constructed later in `__init__` (e.g. the
  `sided` setter dereferences `combobs`). A `toggled` connection made
  before construction completes runs the handler during the init
  `set_active()` calls — the very crash the migration-era regression test
  documented, which is what pushed the wiring onto the broken `activate`
  signal in the first place. Deferring `connect("toggled", ...)` until
  after the initial `set_active()` calls reproduces GTK3's effective
  behaviour (handlers never ran on programmatic changes during init) while
  fixing mouse clicks, and avoids guards in the property setters.
- **Alternatives considered:**
  - Connect immediately plus `hasattr()` guards in the `sided` and
    `side_to_scan` setters: works, but scatters init-order knowledge into
    setters and keeps property side effects firing during construction.
  - Leave `activate`: unacceptable, mouse clicks do nothing.
- **Implementation:** In `_create_extended_mode()` and the page-number
  section, move the three `connect("toggled", ...)` calls to after the
  initial `set_active()`/`set_active(0)`/`num_pages = 1` sequence, with a
  comment explaining why.

**Decision 3: Update tests to reflect corrected semantics.**

- **Rationale:** The migration-added tests
  `test_specify_widget_does_not_fire_on_programmatic_change` and
  `test_sided_buttons_do_not_fire_on_programmatic_change` assert that
  programmatic `set_active()` must not run the handler. That premise was
  compensating for the wrong signal choice; with `toggled`, a state change
  (user or programmatic) fires the handler and the property mirrors the
  widget. Rewriting them keeps regression coverage for the real hazards:
  entry visibility, and init completing without AttributeError.
- **Alternatives considered:** Preserving the old premise via
  user-vs-programmatic flags — added complexity for no user-visible gain.
- **Implementation:** Rename both tests to
  `*_sync_on_programmatic_change`, assert the property/visibility tracks
  the widget after construction, and add explicit visibility regression
  tests (`Save(select_datetime=True)` shows the entry; toggling "Specify"
  shows/hides it).

## Risks / Trade-offs

- [Risk] Tests asserting the old (broken) behavior fail — expected; they
  are rewritten to assert the corrected contract.
- [Trade-off] Using `toggled` means programmatic `set_active()` after init
  also triggers the handler when state changes — correct and desirable
  (keeps UI and state consistent, and matches how `downsample` and other
  GTK4 check buttons in the codebase already behave).
- [Risk] Deferred connections in `pagecontrols.py` mean a future edit that
  inserts widget construction after the connect calls would re-expose the
  init-order crash — mitigated by the rewritten regression test, which
  constructs the full `Scan` dialog and asserts init completes.
