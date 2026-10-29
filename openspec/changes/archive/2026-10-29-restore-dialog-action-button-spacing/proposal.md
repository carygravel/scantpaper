# Proposal

## Why

GTK3's `GtkDialog` took the action-button spacing and action-area border from
the active theme and applied them to the action area. Adwaita used 4 px between
buttons and, for a file chooser, 6 px around them. GTK4's `GtkDialog` replaced
that action area with a plain `GtkBox` whose spacing is 0; a plain dialog also
loses the inset entirely, while a file chooser keeps only a 6 px native inset.
The recent dialog content-padding fix deliberately covered the content area
only.

As a result, separate action buttons now touch each other and the window edge.
This is most visible in the Tools dialogs, the scan dialog and the file
choosers. `Gtk.MessageDialog` is different: GTK presents its buttons as a
joined, homogeneous bar, so it is not part of this regression and should keep
that presentation.

## What Changes

- Give the action area of every dialog with separate action buttons a
  consistent 12 px inset on all sides, matching the dialog content margin, and
  a consistent 6 px gap between adjacent buttons.
- Apply the same treatment through the shared `Dialog` base so every
  `Dialog`-based dialog is covered automatically, and at the bare
  `Gtk.Dialog` and `Gtk.FileChooserDialog` call sites that bypass it.
- Leave `Gtk.MessageDialog` action areas unchanged. Their homogeneous,
  joined-button bar is intentional, and spacing or insetting them would fight
  the theme's borders and rounded outer corners.
- Keep the action-area inset and button spacing as shared constants so code
  and tests read one source of truth.
- Add tests covering a normal dialog, a bare `Gtk.Dialog`, a file chooser and
  the unchanged message-dialog bar, and document the visible change in
  `README.md` and `changelog.md`.
- No change to button labels, mnemonics, response handling or which callbacks
  run.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `dialog-layout`: extend the capability from content padding and row spacing
  to the action area. Action buttons are inset from the dialog edge and
  separated from each other, while a joined message-dialog bar keeps its
  presentation.

## Impact

- `src/scantpaper/const.py`: add the shared action-button spacing value; reuse
  the existing `DIALOG_CONTENT_MARGIN` for the action-area inset.
- `src/scantpaper/dialog/__init__.py`: add the shared action-area helper and
  apply it from `Dialog.add_actions`.
- Bare `Gtk.Dialog` sites: `src/scantpaper/session_mixins.py`,
  `src/scantpaper/file_menu_mixins.py` and `src/scantpaper/dialog/scan.py`.
- File-chooser sites: `src/scantpaper/file_menu_mixins.py`,
  `src/scantpaper/dialog/preferences.py` and
  `src/scantpaper/postprocess_controls.py`.
- Tests: `src/scantpaper/tests/test_05_dialog.py` and the adjacent dialog,
  file-menu and postprocess tests.
- `README.md` and `changelog.md`.
- No new dependency, no persistence or configuration change, and no data
  migration. The change reaches the action area through GTK4's dialog child
  structure on top of the deprecated `Gtk.Dialog`; it is a targeted fix, not a
  redesign of the dialogs.
