## Why

The layer-edit control bar and the canvas it edits can disagree about which
layer is active. On startup the `editmode` action's state defaults to `text`
(so the View menu ticks "Edit text layer") while both control bars are hidden
by `app_window.py`'s unconditional `set_active(active=False)` pair. Nothing
reconciles the two, so a user who opens a session or config lands with a ticked
menu item but no visible editor, and must toggle to annotations and back to
make it appear. The same split of responsibilities leaves the annotation layer
unreachable in the split view modes: `_pack_viewer_tools` always packs the text
canvas and detaches the annotation canvas, yet `editmode` can still select
annotations, showing a control bar over a canvas that is not on screen.

## What Changes

- Define a single logical **active layer** (text or annotation) that both the
  tabbed view and the split views represent, instead of leaving `editmode`, the
  notebook page, and bar visibility as three independent states. On launch the
  persisted layer (default text) is applied, so the View menu is correct from
  the first paint.
- In tabbed mode selecting the text or annotation page updates the active layer;
  the Image page keeps the selection but hides its bar, since it shows the bare
  scan. The window still opens on the Image page so the scan is visible. In
  split modes `editmode` selects the active layer.
- Show the active layer's control bar only while its canvas is on screen,
  fixing the startup mismatch (the bar no longer appears over the image page or
  a canvas that is not shown).
- Pack the **active layer's** canvas beside the image in split modes, so the
  annotation layer is editable in split view for the first time, and hide its
  bar rather than offering an unreachable editor.
- Keep the tabbed page and `editmode` in sync when switching between tabbed and
  split modes: leaving split lands on the matching tab; entering split keeps the
  current active layer (default text).
- Persist `editmode` alongside `viewer_tools`, so a restart or a restored
  session reopens the layout and active layer the user left.

## Capabilities

### New Capabilities

- `active-layer-selection`: the single logical active-layer state, how the
  tabbed and split views represent it, how it stays consistent across view
  switches, how it drives control-bar and canvas visibility, and how it is
  persisted.

### Modified Capabilities

- `view-layout`: the split pane packs the active layer's canvas (not always the
  text canvas), and re-packs when the active layer changes.

## Impact

- `src/scantpaper/app_window.py`: `_pack_viewer_tools`, `_change_view_cb`,
  `_edit_mode_callback` (moved/rewired), startup initialisation, settings.
- `src/scantpaper/session_mixins.py`: `_add_text_view_layers` /
  `_edit_mode_callback` wiring.
- `src/scantpaper/config.py`: persist `editmode`.
- `src/scantpaper/app.ui`: View-menu edit-mode items gain tab/active-layer
  semantics (no new strings expected; labels unchanged).
- Tests: `test_app_window.py` layout/pack tests, `test_session_mixins.py`
  edit-mode test, config round-trip tests.
