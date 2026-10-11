# Proposal: Fix split view panes collapsing on startup

## Why

When the main window ends a session in a horizontal or vertical split (rather
than tabbed), the next launch does not show a visible split: the image pane is
collapsed to an edge, so an imported image is invisible until the user cycles
through the three view modes to force a re-layout. The split layout is saved
correctly, but it is not rendered correctly on startup.

## What Changes

- Pack the split panes (`_hpanei`/`_vpanei`) with an explicit divider position
  so the image and text-layer panes are both visible immediately on startup,
  instead of relying on GtkPaned's default position computed while the
  children are empty and the window is unrealized.
- Persist the split-pane divider position in the config (in the same spirit as
  the existing `"thumb panel"` setting) and restore it on the next launch, so a
  user's chosen split ratio survives across sessions.
- Add/adjust tests that exercise the split-pane startup path (currently the
  packing tests use `MagicMock`, so they do not catch collapsed-pane behaviour).

No **BREAKING** changes.

## Capabilities

### New Capabilities

- `view-layout`: Describes how the main window arranges the image, text-layer
  and annotation views (tabbed, horizontal split, vertical split) and how the
  split divider position is initialised and persisted across sessions.

### Modified Capabilities

None.

## Impact

- `src/scantpaper/app_window.py` — `_pack_viewer_tools`, and the construction
  of `_hpanei`/`_vpanei` in `_populate_panes` (set a default divider position).
- `src/scantpaper/config.py` — add a default for the split-pane position and
  ensure it round-trips through `write_config`/`read_config`.
- `src/scantpaper/session_mixins.py` — `_pack_viewer_tools` is called from
  `_add_text_view_layers`; no contract change expected.
- `src/scantpaper/tests/test_app_window.py` — extend/add packing tests.
- No new dependencies.

Related but out of scope (candidate follow-up): in split modes the annotation
canvas is currently never packed anywhere, so annotations are only visible in
tabbed mode. This change does not address that.
