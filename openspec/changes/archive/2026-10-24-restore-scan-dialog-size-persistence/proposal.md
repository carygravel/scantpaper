# Proposal

## Why

Since the GTK4 migration, the scan dialog no longer remembers its size between
sessions: a dialog the user has resized reopens at the default size on the next
start. The regression was introduced by the migration swapping
`Gtk.Window.get_size()` for `Gtk.Widget.get_width()/get_height()` in the save
path. In GTK4 those accessors report 0 once a window is hidden, and the scan
dialog is hidden (not destroyed) when closed — so on quit its size is persisted
as 0, and the next launch treats the setting as unset.

## What Changes

- The scan dialog records its current size at the moment it is closed (window
  close button, the `_Close` button, or Escape), while the size is still
  available, and keeps it for the quit-time save.
- On quit, the recorded size is written back to `scan_window_width` and
  `scan_window_height`. The persisted value is never overwritten with a zero
  width or height, so an "open scan dialog in the background" session that
  never showed the dialog does not erase the saved size.
- The restore path is unchanged: a saved size is passed to the dialog as
  `default_width`/`default_height` on the next launch.
- The stale migration comment in `_can_quit()` claiming GTK4 exposes no window
  size accessors is corrected to describe the hidden-window behaviour.
- Tests cover the close paths recording the size, the quit path persisting the
  recorded size, a zero snapshot not clobbering the saved value, and the
  restore path passing the saved dimensions to the dialog.

## Capabilities

### New Capabilities

- `scan-dialog-size-persistence`: The scan dialog remembers its size across
  sessions — its size is captured on close and restored on the next launch.

### Modified Capabilities

No existing capability's requirements change; no delta specs are needed.

## Impact

- `src/scantpaper/dialog/scan.py` (or the `Dialog` base in
  `src/scantpaper/dialog/__init__.py`): capture the dialog size on close, the
  single funnel all three close paths already share.
- `src/scantpaper/file_menu_mixins.py`: write back the recorded size instead of
  reading `get_width()/get_height()` from a possibly-hidden dialog; keep the
  previous setting when a live read would be zero; correct the `_can_quit()`
  comment.
- `src/scantpaper/config.py`: no change — defaults for
  `scan_window_width`/`scan_window_height` stay `None`.
- Tests: `test_dialog_scan.py`, `test_scan_menu_item_mixins.py`,
  `test_file_menu_mixins.py` (mock-based expectations may need to reflect the
  recorded-size source).
- No new dependencies; no API or CLI changes; no database changes. Restores
  previously existing user-visible behaviour, so `README.md` is not expected to
  change.
