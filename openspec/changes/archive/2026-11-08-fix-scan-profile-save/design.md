# Design

## Context

`_save_profile_callback` in `src/scantpaper/dialog/scan.py` builds a bare
`Gtk.Dialog`, adds a name entry and calls `run_dialog`, a helper that runs a
nested main loop until the dialog responds. Saved profiles are emitted as
`added-profile` so the window persists them in the configuration; the profile
selector is populated from `self.profiles`. See `proposal.md` for why this
matters.

The GTK4 port left the dialog title as a positional argument. GTK4's
PyGObject `Gtk.Dialog` wrapper accepts keyword properties only, so the call
raises before the dialog is shown. The callback tests replace `Gtk.Dialog`
with a mock, so CI cannot see the failure.

## Goals / Non-Goals

**Goals:**

- Restore the naming dialog without changing the profile model or storage.
- Make the same regression fail a test even if the constructor is exercised.

**Non-Goals:**

- Reworking the profile manager UI or its buttons; that is
  `label-icon-only-buttons`.
- Changing profile serialisation or configuration keys.

## Decisions

**Use the `title=` property.** Construct the dialog with
`title=_("Name of scan profile")`, matching the Edit dialog, which already
uses keyword arguments. Alternatives: build the dialog from the project's
`Dialog` base class (more churn for no behaviour gain), or add a compatibility
shim around `Gtk.Dialog` (hides the class of bug rather than fixing it).

**Test the real dialog and mock only the modal loop.** Patch
`scantpaper.dialog.scan.run_dialog` to return a response, locate the real
`Gtk.Entry` inside the constructed dialog, set its text, and let `Gtk.Dialog`
be created for real. This exercises the constructor that regressed while
keeping the test synchronous. The suite already runs under Xvfb, so a real
dialog is available. Alternatives: keep mocking `Gtk.Dialog` and assert the
keyword arguments (catches this call but still never proves the dialog can be
built), or drive a real dialog through the event loop (slower and flakier).

**Keep the retry loop.** An empty name keeps the dialog open; Cancel closes it
without saving. This is existing behaviour, and the new capability spec now
states it, so the change does not alter it.

## Risks / Trade-offs

- Other GTK4 constructors could have the same positional-argument mistake. →
  An audit found no other positional `Gtk.Dialog` call in production code; a
  real-dialog regression test protects this one.
- A real dialog needs a display in CI. → pytest-xvfb already provides one;
  keep the test in the normal suite rather than an opt-in job.

## Migration Plan

None. No stored data or configuration keys change; existing profiles load and
apply as before.
