# Design

## Context

See `proposal.md` — Why.

- `Scan` (`src/scantpaper/dialog/scan.py`) owns the action area.
  `add_actions` (`dialog/__init__.py:145-167`) creates the Scan button as the
  dialog's OK response and default widget.
- The `cursor` property doubles as a busy flag and as the Scan button's
  sensitivity: the setter (`scan.py:397-408`) calls
  `scan_button.set_sensitive(newval == "default")`.
- Option application sets `cursor = "wait"` at the start of each
  `_set_option_profile` (`scan.py:1296-1297`) and restores `"default"` only in
  `_complete_profile_setting` (`scan.py:1421-1428`). Device opening does the
  same through `_device_opening_started` and `_initialise_options`
  (`sane.py:146-151`, `sane.py:213`).
- `_update_options` re-applies the current options after a reload
  (`scan.py:823-824`), so any option that triggers `INFO_RELOAD_OPTIONS`
  re-enters the wait state.
- GTK delivers `GtkButton::clicked` on release and checks sensitivity at both
  ends: an insensitive button starts no gesture, and
  `gtkbutton.c:click_released_cb` requires the widget to be sensitive at
  release. Disabling the button for the duration of an apply therefore
  discards clicks at either end.
- The focus-level control is a `Gtk.MenuButton` with a `Gtk.Popover`
  (`layer.py:307-346`). Each layer bar owns one. `LayerEditor.set_active`
  hides and shows the bar (`layer.py:815-820`), driven by
  `_update_layer_visibility` (`app_window.py:1002-1006`). `GtkMenuButton`
  clears its `active` state only on the popover's `closed` signal; hiding an
  ancestor unmaps the popover without emitting it.

## Goals / Non-Goals

**Goals:**

- Remember an activation of a primary action that arrives while options are
  being prepared, and run it exactly once when the preparation settles.
- Never leave the Scan control transiently insensitive while search options
  are prepared, so GTK delivers both halves of a click.
- Keep protecting a running scan from a second activation.
- Make the focus-level popover open on the first activation after its control
  bar is shown.

**Non-Goals:**

- Changing light-dismiss semantics for menus and popovers.
- Diagnosing compositor, input-method, or pointer-hardware click loss.
- Making every dialog action queueable; only actions that gate an operation
  the user has already requested.
- New visible strings, preference keys, or configuration changes.

## Decisions

### D1: Separate busy indication from action sensitivity

The `cursor` setter SHALL set the cursor only. The Scan button's sensitivity
SHALL be controlled explicitly by the dialog lifecycle, not derived from
`cursor`:

- insensitive while a scan is actually running;
- insensitive when no device is selected;
- sensitive while options are being applied, reloaded, or the device is
  opening, with a pending activation allowed.

Keeping the button sensitive is what removes the two GTK drop windows: the
press is delivered, and the release still finds a sensitive widget.

Alternatives considered:

- Re-enable the button in a `GLib.idle_add` after disabling it. Rejected: it
  shrinks the window but still loses a release that arrives late, and it does
  not remember the user's intent.
- Install a custom click controller on the insensitive button. Rejected:
  fighting GTK's event delivery, and it would need duplicating for every
  action control.

### D2: One pending activation, settled when the outermost option work ends

Add a busy depth counter and a boolean pending flag to `Scan`:

- Option work increments the counter when an apply or device open starts, and
  decrements it on the corresponding success, error, or cancellation path.
- `_do_scan` keeps emitting `clicked-scan-button`, then:
  - if the counter is above zero, set the pending flag and return;
  - otherwise call `scan()` as today.
- When the counter reaches zero, the pending flag is cleared and `scan()` is
  scheduled through `GLib.idle_add`, so the callback that settled the option
  work unwinds and the dialog repaints before the scan starts.
- Closing the dialog clears the pending flag. An option error clears it and
  relies on the existing error dialog, so nothing fires during a later,
  unrelated operation.

A depth counter is preferred over `setting_profile` or
`setting_current_scan_options`: those lists track profile re-entrancy and may
be emptied before the last reload finishes. The counter reflects outstanding
work directly, and a bool pending flag coalesces repeated clicks into one
scan.

### D3: Busy state without ghosting

While options are prepared, the dialog keeps the wait cursor and the existing
progress text ("Setting option …", "Retrieving options", "Opening device").
Those already tell the user the dialog is busy. The Scan control stays
sensitive and queues instead of being ghosted.

`set_response_sensitive(Gtk.ResponseType.OK, ...)` is reserved for genuine
unavailability (for example no usable device). It is not used as a busy
indicator during device opening or option initialisation.

### D4: Pop the focus-level popover down before hiding its bar

Add a `LayerControls.close_focus_zoom()` helper that pops the focus-level
menu button down if it exists. `LayerEditor.set_active(active=False)` calls
it before `controls.hide()`.

Popping down emits the popover's `closed` signal, which resets the
`GtkMenuButton`'s `active` state. The next activation therefore opens the
popover instead of closing one that is already logically open but invisible.
`_update_layer_visibility` already calls `set_active` for both editors, so
the tab and layer switch paths are both covered without further wiring.

Alternatives considered:

- Set `can_focus(False)` on the button. Rejected: it does not reset the
  popover state when the bar is hidden.
- Create and destroy the popover on each show. Rejected: unnecessary churn
  and it would drop the live slider state.
- Rely on GTK's unmap to close the popover. Rejected: this is exactly the
  behaviour that leaves the state stuck.

### D5: Signal timing is unchanged

`clicked-scan-button` is still emitted when the activation is accepted, even
if the scan itself is deferred. The main window uses that signal to snapshot
postprocessing settings and reset alternate-rotation parity at job start
(`scan_menu_item_mixins.py:265-303`); no consumer starts scan work from it.
This preserves the current ordering and test expectations.

### D6: Tests

Widget-level tests, no display required:

- `test_dialog_scan.py`: activating Scan while the busy counter is positive
  calls `scan()` once after settling; repeated activations coalesce; closing
  clears the pending activation; the cursor setter no longer changes the Scan
  button's sensitivity.
- `test_06198_dialog_scan_sane.py` / `test_0610_dialog_scan_sane.py`: a
  profile apply completes and a queued scan runs afterwards; an error path
  leaves no pending scan.
- `test_layer.py` or `test_text_layer_control.py`: hiding a control bar while
  the focus-level popover is active resets the menu button's `active` state;
  showing the bar again and activating once opens it.

## Risks / Trade-offs

- **Auto-starting a scan may surprise the user** → only queue while option
  preparation is outstanding, coalesce to one activation, clear on close and
  on error, and keep the existing wait cursor plus progress text visible.
- **Nested applies and reloads can settle more than once** → use a depth
  counter and an idempotent settle routine; clear the pending flag before
  calling `scan()`.
- **A queued scan after a device-open error** → the counter is decremented on
  the error path, the pending flag is cleared, and the existing error dialog
  explains why no scan started.
- **Popping the popover down may move focus** → it happens exactly when the
  bar is being hidden, so focus is moving away from the bar anyway.
- **Coverage gate** → add focused unit tests for each new branch; no new
  `noqa` suppressions.

## Migration Plan

No data, settings, or file-format migration. The change is behavioural.
Rolling back is reverting the commit; no stored state depends on the new
pending flag.

## Open Questions

None. Whether to add an explicit "Scanning when ready…" cue can be revisited
separately; this change relies on the existing wait cursor and progress text.
