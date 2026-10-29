# Design

## Context

See `proposal.md` — Why. The current state that shapes the approach:

- GTK3's `GtkDialog` applied theme style properties to its action area:
  `button-spacing` (Adwaita 4) and `action-area-border` (Adwaita 0 for a
  plain dialog, 6 for a file chooser). It skipped spacing when the buttons
  were a linked/expanded bar.
- GTK4's `gtkdialog.ui` makes the action area a plain `GtkBox` with spacing
  0. A plain dialog also has no inset; a file chooser keeps a native 6 px
  inset. Message dialogs set the action area homogeneous, producing the
  theme's joined bar.
- The action area is a **sibling** of the content area, so the recent
  `pad_content_area()` fix does not reach it.
- GTK4 removed `Gtk.Dialog.get_action_area()` (absent in 4.24). The action
  area is reachable through the template's fixed structure: content area ->
  next sibling (`dialog-action-box`) -> first child (`dialog-action-area`).
  The structure is the same on GTK 4.6 and 4.24.
- Many tests construct a real `Dialog`, but many others pass `MagicMock`
  dialog instances. Any traversal over widget children must be mock-safe.
- Branch coverage is enforced at 99%, so every new early return needs a
  test.
- `Gtk.Dialog` is deprecated in GTK 4.10+. This change is a targeted bridge
  on top of it, not a migration away from it.

## Goals / Non-Goals

**Goals:**

- One place that owns the action-area inset and inter-button spacing.
- One shared value for each, used by code and tests.
- Every dialog with separate action buttons gets the treatment, including
  bare `Gtk.Dialog` and `Gtk.FileChooserDialog` instances.
- Behaviourally invisible to dialogs that present a joined button bar.
- No phantom space in dialogs that have no action buttons.

**Non-Goals:**

- Redesigning a dialog's content, order or labels.
- Replacing `Gtk.Dialog` or its action area with a custom widget.
- Changing button labels, mnemonics or response handlers (`dialog-buttons`).
- Changing `Gtk.MessageDialog`'s joined bar.
- Spacing the progress-bar Cancel button or the text-layer toolbar, which
  were already unspaced in GTK3.

## Decisions

**D1. Hook the shared work into `Dialog.add_actions()` and call a shared
helper at the bare-dialog and file-chooser sites.** `add_actions()` is the
single seam used by every `Dialog`-based dialog that has action buttons.
The five bare `Gtk.Dialog` sites and the six file-chooser sites bypass it and
call the helper explicitly after adding their buttons.
Rationale: it covers the common path once and keeps the exceptions visible.
Alternative: pad in `Dialog.__init__` — rejected because the Select Date
dialog has no action buttons and would gain phantom space. Alternative:
override `Gtk.Dialog.add_button()` — rejected because it would not cover
`add_buttons()` on bare dialogs or file choosers, nor standard dialogs not
built from our `Dialog` class.

**D2. Use `DIALOG_CONTENT_MARGIN` (12) for all four action-area margins.**
The action area uses the same inset as the content area, so the rightmost
button lines up with the content's right edge and the bottom inset matches
the other edges. GTK4's own print dialog uses 12 px around its action box
(`.dialog-action-box { margin: 12px; }`), so the resulting 24 px gap between
content and buttons is the toolkit's own scale.
Rationale: consistency with the already-shipped content padding.
Alternative: restore GTK3's 2 px plain-dialog / 6 px file-chooser values —
rejected because the content is now inset by 12 and the buttons would look
flush by comparison. Alternative: a second `DIALOG_ACTION_MARGIN` constant —
rejected as unnecessary duplication while the values are the same.

**D3. Add `DIALOG_BUTTON_SPACING = 6` to `const.py`.** The value matches the
existing `DIALOG_ROW_SPACING`, so adjacent controls share one visual rhythm.
GTK3's Adwaita used 4 px; the exact value is aesthetic and can be tuned
without changing the approach.
Rationale: a named button-spacing constant keeps the action area independent
of row spacing if either needs tuning later.
Alternative: reuse `DIALOG_ROW_SPACING` directly — rejected because the
constant's comment describes content rows and the two may diverge.
Alternative: restore 4 px — rejected only for visual consistency with the
app's 6 px scale; it remains a valid value if review prefers it.

**D4. Set spacing and margins on the inner `.dialog-action-area`.** The
outer `dialog-action-box` is used only for navigation. The inner box owns the
buttons, and inset there preserves the file chooser's full-width top border
while still pulling the buttons in from the window edge.
Rationale: one widget receives all the geometry, and the file chooser's
separator stays visually attached to the dialog width.
Alternative: margins on the outer `dialog-action-box` — rejected because it
would inset the file chooser's top border as well. Alternative: a CSS
provider — rejected because GTK4 `GtkBox` spacing is a widget property, not a
CSS property; a `border-spacing` rule has no effect, as verified against
GTK 4.24. Alternative: per-button margins — rejected as more calls for the
same result.

**D5. Skip homogeneous action areas.** GTK marks a joined button bar with
`get_homogeneous() == True`; message dialogs are the visible case. This is the
GTK4 equivalent of GTK3's rule that skipped spacing when the button box layout
was `EXPAND`.
Rationale: it protects the joined bar without naming `Gtk.MessageDialog`, so
any other joined action area is covered too.
Alternative: `isinstance(dialog, Gtk.MessageDialog)` — rejected as narrower
and tied to a deprecated class. Alternative: rely on call sites never passing
a message dialog — rejected because a future call is easy to add and hard to
notice.

**D6. No-op when the action area has no children, and call the helper only
after buttons exist.** The helper returns early rather than adding margins to
an empty action area. This keeps button-less dialogs at their natural size.
Rationale: an empty action area with margins would reserve blank space below
the content.
Alternative: set margins in `Dialog.__init__` and hide the empty action box —
rejected as a second behavioural change.

**D7. Reach the action area through a fixed three-step traversal, not a
child loop.** The helper takes the content area, gets its next sibling, then
that box's first child. The chain is cast to `Gtk.Box` for typing.
Rationale: it mirrors the template exactly and cannot hang when tests pass a
`MagicMock` dialog; a `while child:` loop would never terminate against a
mock. It also avoids depending on the CSS class name.
Alternative: recursive search for `.dialog-action-area` — rejected for the
mock-hang risk. Alternative: `get_widget_for_response()` — rejected because
it needs a response ID at every call site and some dialogs use different
response types.

**D8. Apply the same 12 px inset to file choosers, overriding their native
6 px.** One rule for every non-joined action area is easier to reason about
and matches the app's content inset.
Rationale: consistent visual treatment; the native 6 px is a GTK default,
not a contract.
Alternative: set only spacing on file choosers and leave their 6 px inset —
rejected for inconsistency with the 12 px app dialogs; can be revisited if
the narrower file-chooser inset looks better in practice.

## Risks / Trade-offs

- [GTK may change the dialog template or remove the remaining action-area
  access path] -> The helper is covered by a real-widget test and the
  supported GTK floor/ceiling (4.6-4.24) use the same template. Revisit the
  helper when `Gtk.Dialog` is replaced; this change does not increase the
  existing deprecation risk beyond the current dialogs.
- [Overriding the file chooser's native 6 px inset] -> Accepted for
  consistency; it is a single decision and the value can be changed without
  touching the helper structure.
- [The 12 px top margin makes a 24 px content-to-button gap] -> Accepted:
  this matches GTK4's own print dialog scale; if it looks too open, drop the
  top margin only, leaving start/end/bottom at 12.
- [A saved scan-dialog size now carries slightly more content] -> The
  persisted size is respected and the user can resize; no stored value
  changes.
- [Mocked dialogs receive extra setter calls] -> The fixed traversal is
  mock-safe and the setter calls are harmless on mocks; call-site tests that
  assert exact interactions are reviewed.
- [New early returns lower coverage] -> Add real-widget tests for the normal
  path, the empty action area, the homogeneous bar and a file chooser; the
  mock call sites naturally cover the no-content-area path.
- [Message-dialog buttons still look joined] -> Intentional and documented in
  the spec; changing it would require overriding the theme's joined borders,
  not just spacing.

## Testing

- `test_05_dialog.py`: `Dialog.add_actions()` sets the action-area spacing
  and all four margins; the helper works on a bare `Gtk.Dialog`; an empty
  action area keeps zero margins; a message dialog keeps zero spacing and
  stays homogeneous; a `Gtk.FileChooserDialog` gets the same treatment.
- Call-site tests for the bare dialogs and file choosers
  (`test_0621_dialog_scan_edit_save.py`, `test_session_mixins.py`,
  `test_file_menu_mixins.py`, `test_preferences_dialog.py`,
  `test_postprocess_controls.py`) pass with the mock-safe helper.
- Existing `Dialog.add_actions` tests continue to pass; no label or response
  behaviour changes.

## Migration Plan

Single coordinated change; no data or configuration migration. Rollback is
reverting the commit. Land with the full `pytest` suite, `ruff format
--check`, `ruff check` and `ty check .` clean, and coverage at or above the
existing threshold.

## Open Questions

- The exact inter-button spacing (6 px matching the row scale, or 4 px
  matching GTK3's Adwaita) is aesthetic. Confirm at review without changing
  the approach, the spec or the task breakdown.
