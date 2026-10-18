## Why

The Save dialog's Date/Time entry field is never visible when the user clicks
"Specify", even though the radio button becomes active. This is a regression
from the GTK3→GTK4 migration: the code connects the handler to the `activate`
signal, but in GTK4 `Gtk.CheckButton` emits `activate` only on keyboard
activation (Space/Enter), not on mouse clicks. The intended UI behavior
(clicking "Specify" shows the date entry) is broken, and constructing the
dialog with `select_datetime=True` also leaves the field hidden.

## What Changes

- Connect the "Specify" check button's handler to the `toggled` signal
  instead of `activate` (GTK4 `Gtk.CheckButton` emits `toggled` for both
  mouse clicks and group changes). Clicking "Specify" now reveals the date
  entry, and widget state stays in sync.
- Apply the same GTK4 signal fix to grouped check buttons in
  `dialog/pagecontrols.py` that were migrated to connect `activate` but
  should connect `toggled` for correct mouse-click behavior
  (All, #:, Single sided). The handlers are connected after the initial
  widget state is set up, so the `set_active()` calls made during
  `__init__` cannot run them.
- Update the affected tests: the migration-added tests
  `test_specify_widget_does_not_fire_on_programmatic_change` and
  `test_sided_buttons_do_not_fire_on_programmatic_change` encode the broken
  assumption that programmatic `set_active()` must not run the handler.
  With the correct `toggled`-based wiring, initialization with
  `select_datetime=True` shows the entry and `select_datetime` mirrors the
  widget state. Tests are rewritten to assert visibility regression
  coverage and the corrected semantics.

## Capabilities

### New Capabilities

_None_

### Modified Capabilities

_None_ — this is a UI behavior fix; no new user-visible requirements and no
changes to exported APIs or data contracts. Behavior is restored to match
the pre-migration intended UI semantics.

## Impact

- `src/scantpaper/dialog/save.py`: fix "Specify" check button signal
  connection.
- `src/scantpaper/dialog/pagecontrols.py`: fix grouped check button signal
  connections (`bscanall`, `bscannum`, `buttons`) to use `toggled`, and
  defer connecting until the initial widget state is in place.
- `src/scantpaper/tests/test_dialog_save.py`: rename and rewrite
  `test_specify_widget_does_not_fire_on_programmatic_change` for the
  corrected semantics; add regression tests for date entry visibility on
  click and on initialization with `select_datetime=True`.
- `src/scantpaper/tests/test_dialog_scan.py`: rename and rewrite
  `test_sided_buttons_do_not_fire_on_programmatic_change` for the corrected
  semantics.
